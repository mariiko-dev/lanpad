"""Адреса в локальной сети и QR для спаривания с телефоном."""

import socket
from pathlib import Path
from urllib.parse import quote

import qrcode
from qrcode.image.pure import PyPNGImage


def lan_addresses() -> list[str]:
    """Адреса машины в локальной сети, без петлевого интерфейса.

    Первым идёт адрес, выбранный ядром для исходящего маршрута: именно
    он вероятнее всего достижим с телефона. Остальные добавляются
    следом как запасные — сортировка задвинула бы нужный за адрес VPN.
    """
    primary: str | None = None
    probe = None
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("10.255.255.255", 1))
        primary = probe.getsockname()[0]
    except OSError:
        pass
    finally:
        if probe is not None:
            probe.close()

    others: set[str] = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = info[4][0]
            if not address.startswith("127.") and address != primary:
                others.add(address)
    except socket.gaierror:
        pass

    found = sorted(others)
    return [primary, *found] if primary else found


def connect_url(host: str, port: int, token: str) -> str:
    return f"http://{host}:{port}/?t={quote(token, safe='')}"


def render_terminal(text: str) -> str:
    """QR символами полублока — помещается в обычное окно терминала."""
    code = qrcode.QRCode(border=4)
    code.add_data(text)
    code.make(fit=True)
    matrix = code.get_matrix()

    lines = []
    for row in range(0, len(matrix), 2):
        upper = matrix[row]
        lower = matrix[row + 1] if row + 1 < len(matrix) else [False] * len(upper)
        line = "".join(
            "█" if u and lo else "▀" if u else "▄" if lo else " "
            for u, lo in zip(upper, lower, strict=False)
        )
        lines.append(line)
    return "\n".join(lines)


def save_png(text: str, path: Path) -> None:
    image = qrcode.make(text, image_factory=PyPNGImage)
    with open(path, "wb") as handle:
        image.save(handle)
