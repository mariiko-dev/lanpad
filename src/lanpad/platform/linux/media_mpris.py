"""Состояние воспроизведения через MPRIS поверх D-Bus.

D-Bus работает асинхронно, а сервер — потоками. Поэтому клиент живёт в
отдельном потоке с собственным циклом событий и толкает изменения наружу
через callback. Опроса нет: подписка на PropertiesChanged даёт обновления
в момент их появления.
"""

import asyncio
import hashlib
import threading
from collections.abc import Callable
from urllib.parse import unquote, urlparse

from lanpad.platform.base import MediaBackend
from lanpad.protocol import MediaState

BUS_PREFIX = "org.mpris.MediaPlayer2"
OBJECT_PATH = "/org/mpris/MediaPlayer2"
PLAYER_INTERFACE = "org.mpris.MediaPlayer2.Player"

_ART_PATHS: dict[str, str] = {}


def art_id_for(url: str) -> str:
    """Короткий стабильный идентификатор для локального файла обложки."""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _artist_of(metadata: dict) -> str:
    artist = metadata.get("xesam:artist", "")
    if isinstance(artist, str):
        return artist
    if isinstance(artist, list):
        return ", ".join(str(a) for a in artist)
    return ""


def _art_of(metadata: dict) -> str | None:
    url = metadata.get("mpris:artUrl")
    if not url or not isinstance(url, str):
        return None
    if url.startswith("file://"):
        art_id = art_id_for(url)
        _ART_PATHS[art_id] = unquote(urlparse(url).path)
        return f"/art?id={art_id}"
    return url


def metadata_to_state(
    metadata: dict,
    playback_status: str,
    position_us: int,
    can_seek: bool,
) -> MediaState:
    """Превратить сырые метаданные MPRIS в состояние для телефона."""
    length_us = metadata.get("mpris:length") or 0
    return MediaState(
        playing=(playback_status == "Playing"),
        title=str(metadata.get("xesam:title") or ""),
        artist=_artist_of(metadata),
        art=_art_of(metadata),
        position=round(position_us / 1_000_000, 2),
        duration=round(int(length_us) / 1_000_000, 2),
        can_seek=can_seek,
    )


class MprisMedia(MediaBackend):
    """Следит за первым найденным плеером и отдаёт его состояние."""

    def __init__(self) -> None:
        self._state: MediaState | None = None
        self._subscribers: list[Callable[[MediaState | None], None]] = []
        self._loop: asyncio.AbstractEventLoop | None = None
        self._player = None
        self._ready = threading.Event()
        self._stopping = False
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="lanpad-mpris")
        self._thread.start()
        self._ready.wait(timeout=5)

    # --- публичный интерфейс ---------------------------------------------

    def state(self) -> MediaState | None:
        return self._state

    def command(self, action: str) -> None:
        method = {"play": "call_play_pause", "next": "call_next", "prev": "call_previous"}
        name = method.get(action)
        if name:
            self._call_on_player(name)

    def seek(self, position: float) -> None:
        self._call_on_player("call_set_position", seconds=position)

    def subscribe(self, callback: Callable[[MediaState | None], None]) -> None:
        self._subscribers.append(callback)

    def art_path_for(self, art_id: str) -> str | None:
        return _ART_PATHS.get(art_id)

    def close(self) -> None:
        self._stopping = True
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)

    # --- внутреннее -------------------------------------------------------

    def _publish(self) -> None:
        for callback in self._subscribers:
            callback(self._state)

    def _call_on_player(self, method_name: str, **kwargs) -> None:
        if self._loop is None or self._player is None:
            return
        asyncio.run_coroutine_threadsafe(
            self._invoke(method_name, **kwargs), self._loop
        )

    async def _invoke(self, method_name: str, **kwargs) -> None:
        player = self._player
        if player is None:
            return
        try:
            if method_name == "call_set_position":
                track_id = (await player.get_metadata()).get("mpris:trackid")
                if track_id is None:
                    return
                await player.call_set_position(
                    track_id.value if hasattr(track_id, "value") else track_id,
                    int(kwargs["seconds"] * 1_000_000),
                )
            else:
                await getattr(player, method_name)()
        except Exception:  # noqa: BLE001 — плеер мог исчезнуть между вызовами
            return

    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._connect())
        except Exception:  # noqa: BLE001 — без D-Bus просто нет медиа
            self._ready.set()
            return
        self._ready.set()
        self._loop.run_forever()

    async def _connect(self) -> None:
        from dbus_next import BusType
        from dbus_next.aio import MessageBus

        bus = await MessageBus(bus_type=BusType.SESSION).connect()
        introspection = await bus.introspect("org.freedesktop.DBus", "/org/freedesktop/DBus")
        proxy = bus.get_proxy_object("org.freedesktop.DBus", "/org/freedesktop/DBus", introspection)
        names = await proxy.get_interface("org.freedesktop.DBus").call_list_names()

        player_name = next((n for n in names if n.startswith(BUS_PREFIX + ".")), None)
        if player_name is None:
            self._state = None
            return

        player_introspection = await bus.introspect(player_name, OBJECT_PATH)
        player_proxy = bus.get_proxy_object(player_name, OBJECT_PATH, player_introspection)
        self._player = player_proxy.get_interface(PLAYER_INTERFACE)
        properties = player_proxy.get_interface("org.freedesktop.DBus.Properties")

        async def refresh() -> None:
            try:
                metadata = {k: v.value for k, v in (await self._player.get_metadata()).items()}
                status = await self._player.get_playback_status()
                position = await self._player.get_position()
                can_seek = await self._player.get_can_seek()
            except Exception:  # noqa: BLE001
                self._state = None
            else:
                self._state = metadata_to_state(metadata, status, position, can_seek)
            self._publish()

        def on_properties_changed(interface, changed, invalidated) -> None:  # noqa: ARG001
            if not self._stopping:
                asyncio.create_task(refresh())  # noqa: RUF006

        properties.on_properties_changed(on_properties_changed)
        await refresh()

    @staticmethod
    def is_available() -> bool:
        try:
            import dbus_next  # noqa: F401
        except ImportError:
            return False
        return True
