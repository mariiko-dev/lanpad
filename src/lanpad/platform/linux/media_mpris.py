"""Состояние воспроизведения через MPRIS поверх D-Bus.

D-Bus работает асинхронно, а сервер — потоками. Поэтому клиент живёт в
отдельном потоке с собственным циклом событий и толкает изменения наружу
через callback. Опроса нет: подписка на PropertiesChanged даёт обновления
в момент их появления.
"""

import asyncio
import hashlib
import logging
import threading
from collections import OrderedDict
from collections.abc import Callable
from urllib.parse import unquote, urlparse

from lanpad.platform.base import MediaBackend
from lanpad.protocol import MediaState

BUS_PREFIX = "org.mpris.MediaPlayer2"
OBJECT_PATH = "/org/mpris/MediaPlayer2"
PLAYER_INTERFACE = "org.mpris.MediaPlayer2.Player"

_log = logging.getLogger(__name__)

_ART_PATHS: OrderedDict[str, str] = OrderedDict()
MAX_ART_ENTRIES = 32


def _remember_art(art_id: str, path: str) -> None:
    """Запомнить путь к обложке, вытесняя самые старые.

    Без вытеснения `/art` отдавал бы обложки треков, игравших часы
    назад, хотя обещает отдавать только из текущих метаданных.
    """
    _ART_PATHS[art_id] = path
    _ART_PATHS.move_to_end(art_id)
    while len(_ART_PATHS) > MAX_ART_ENTRIES:
        _ART_PATHS.popitem(last=False)


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


def _seconds(raw: object) -> float:
    """Микросекунды в секунды.

    Плееры кладут сюда что угодно, включая строки и отрицательные числа,
    поэтому неразбираемое значение означает ноль, а не исключение.
    """
    try:
        micros = int(raw)
    except (TypeError, ValueError, OverflowError):
        return 0.0
    return round(max(0, micros) / 1_000_000, 2)


def _art_of(metadata: dict) -> str | None:
    url = metadata.get("mpris:artUrl")
    if not url or not isinstance(url, str):
        return None
    if url.startswith("file://"):
        art_id = art_id_for(url)
        _remember_art(art_id, unquote(urlparse(url).path))
        return f"/art?id={art_id}"
    return url


def metadata_to_state(
    metadata: dict,
    playback_status: str,
    position_us: int,
    can_seek: bool,
) -> MediaState:
    """Превратить сырые метаданные MPRIS в состояние для телефона.

    Спецификацию MPRIS плееры соблюдают нестрого, поэтому ни одно поле
    здесь не считается доверенным: разбор обязан выдавать состояние на
    любом входе, а не падать.
    """
    return MediaState(
        playing=(playback_status == "Playing"),
        title=str(metadata.get("xesam:title") or ""),
        artist=_artist_of(metadata),
        art=_art_of(metadata),
        position=_seconds(position_us),
        duration=_seconds(metadata.get("mpris:length")),
        can_seek=can_seek,
    )


class MprisMedia(MediaBackend):
    """Следит за первым найденным плеером и отдаёт его состояние."""

    def __init__(self) -> None:
        self._state: MediaState | None = None
        self._subscribers: list[Callable[[MediaState | None], None]] = []
        self._loop: asyncio.AbstractEventLoop | None = None
        self._player = None
        self._bus = None
        self._player_name: str | None = None
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
            try:
                callback(self._state)
            except Exception:
                _log.exception("подписчик медиа-состояния бросил исключение")

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
        except Exception:
            return

    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._connect())
        except Exception:
            _log.info("подключиться к MPRIS не удалось, медиа отключено", exc_info=True)
            self._ready.set()
            return
        self._ready.set()
        self._loop.run_forever()

    async def _connect(self) -> None:
        from dbus_next import BusType
        from dbus_next.aio import MessageBus

        self._bus = await MessageBus(bus_type=BusType.SESSION).connect()
        introspection = await self._bus.introspect(
            "org.freedesktop.DBus", "/org/freedesktop/DBus"
        )
        proxy = self._bus.get_proxy_object(
            "org.freedesktop.DBus", "/org/freedesktop/DBus", introspection
        )
        dbus = proxy.get_interface("org.freedesktop.DBus")

        def on_name_owner_changed(name: str, old_owner: str, new_owner: str) -> None:
            if self._stopping or not name.startswith(BUS_PREFIX + "."):
                return
            asyncio.create_task(self._players_changed(name, new_owner))

        dbus.on_name_owner_changed(on_name_owner_changed)

        names = await dbus.call_list_names()
        found = next((n for n in names if n.startswith(BUS_PREFIX + ".")), None)
        if found is None:
            self._state = None
            self._publish()
            return
        await self._attach(found)

    async def _players_changed(self, name: str, new_owner: str) -> None:
        """Плеер появился или ушёл.

        Служба стартует вместе с графической сессией, когда плееров ещё
        нет, поэтому единственный поиск при запуске оставлял бы медиа
        мёртвым до перезапуска агента.
        """
        if new_owner and self._player_name is None:
            await self._attach(name)
            return
        if not new_owner and name == self._player_name:
            self._player = None
            self._player_name = None
            self._state = None
            self._publish()
            await self._attach_any()

    async def _attach_any(self) -> None:
        """Подхватить любой оставшийся на шине плеер."""
        if self._bus is None:
            return
        try:
            introspection = await self._bus.introspect(
                "org.freedesktop.DBus", "/org/freedesktop/DBus"
            )
            proxy = self._bus.get_proxy_object(
                "org.freedesktop.DBus", "/org/freedesktop/DBus", introspection
            )
            names = await proxy.get_interface("org.freedesktop.DBus").call_list_names()
        except Exception:
            _log.debug("не удалось перечислить имена на шине", exc_info=True)
            return
        found = next((n for n in names if n.startswith(BUS_PREFIX + ".")), None)
        if found is not None:
            await self._attach(found)

    async def _attach(self, player_name: str) -> None:
        """Подключиться к плееру и подписаться на его изменения."""
        if self._bus is None:
            return
        try:
            introspection = await self._bus.introspect(player_name, OBJECT_PATH)
            player_proxy = self._bus.get_proxy_object(
                player_name, OBJECT_PATH, introspection
            )
            self._player = player_proxy.get_interface(PLAYER_INTERFACE)
            self._player_name = player_name
            properties = player_proxy.get_interface("org.freedesktop.DBus.Properties")
        except Exception:
            _log.debug("не удалось подключиться к плееру %s", player_name, exc_info=True)
            self._player = None
            self._player_name = None
            return

        def on_properties_changed(interface, changed, invalidated) -> None:
            if not self._stopping:
                asyncio.create_task(self._refresh())

        properties.on_properties_changed(on_properties_changed)

        def on_seeked(position_us: int) -> None:
            # MPRIS keeps Position out of PropertiesChanged — it changes
            # continuously — and announces a jump with this signal instead.
            # Without it a seek never reaches the phone and its progress bar
            # keeps counting from the position before the jump.
            if not self._stopping:
                asyncio.create_task(self._refresh())

        try:
            self._player.on_seeked(on_seeked)
        except AttributeError:
            _log.debug("плеер %s не отдаёт сигнал Seeked", player_name)

        await self._refresh()

    async def _refresh(self) -> None:
        player = self._player
        if player is None:
            self._state = None
            self._publish()
            return
        try:
            metadata = {k: v.value for k, v in (await player.get_metadata()).items()}
            status = await player.get_playback_status()
            position = await player.get_position()
            can_seek = await player.get_can_seek()
            self._state = metadata_to_state(metadata, status, position, can_seek)
        except Exception:
            _log.debug("не удалось прочитать состояние плеера", exc_info=True)
            self._state = None
        self._publish()

    @staticmethod
    def is_available() -> bool:
        try:
            import dbus_next  # noqa: F401
        except ImportError:
            return False
        return True
