"""Точка входа: собрать реализации, поднять сервер, показать QR."""

import argparse
import sys
from pathlib import Path

from lanpad import config, qr
from lanpad.http import make_server
from lanpad.platform.registry import build_backends
from lanpad.session import Session

WEB_ROOT = Path(__file__).parent / "web"


def _print_invitation(token: str, listen_port: int) -> None:
    addresses = qr.lan_addresses()
    if not addresses:
        print("Не удалось определить адрес в локальной сети.")
        print("Проверьте подключение к Wi-Fi и запустите снова.")
        return

    url = qr.connect_url(addresses[0], listen_port, token)
    print()
    print(qr.render_terminal(url))
    print()
    print("Отсканируйте код телефоном, подключённым к той же сети Wi-Fi.")
    print(f"    {url}")
    if len(addresses) > 1:
        print("\nЕсли не открылось, попробуйте другой адрес:")
        for address in addresses[1:]:
            print(f"    {qr.connect_url(address, listen_port, token)}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="lanpad",
        description="Телефон как тачпад и пульт для этого компьютера.",
    )
    parser.add_argument("--port", type=int, default=None, help="порт (по умолчанию 8477)")
    parser.add_argument("--qr", metavar="ФАЙЛ", help="сохранить QR в PNG и выйти")
    parser.add_argument("--install-service", action="store_true",
                        help="установить автозапуск через systemd и выйти")
    args = parser.parse_args()

    token = config.load_or_create_token()
    listen_port = args.port if args.port is not None else config.port()
    if not 1 <= listen_port <= 65535:
        print(f"Порт должен быть от 1 до 65535, получено: {listen_port}", file=sys.stderr)
        return 1

    if args.qr:
        addresses = qr.lan_addresses()
        if not addresses:
            print("Нет адреса в локальной сети.", file=sys.stderr)
            return 1
        try:
            qr.save_png(qr.connect_url(addresses[0], listen_port, token), Path(args.qr))
        except OSError as exc:
            print(f"Не удалось записать {args.qr}: {exc.strerror or exc}", file=sys.stderr)
            return 1
        print(f"QR сохранён: {args.qr}")
        return 0

    if args.install_service:
        from lanpad.service import install

        return install()

    try:
        backends = build_backends()
    except Exception as exc:
        print(f"Не удалось получить доступ к вводу: {exc}", file=sys.stderr)
        return 1

    session = Session(backends)
    try:
        server = make_server(session, token, WEB_ROOT, listen_port)
    except OSError as exc:
        session.close()
        print(f"Не удалось занять порт {listen_port}: {exc.strerror or exc}", file=sys.stderr)
        print("Возможно, агент уже запущен. Проверьте:", file=sys.stderr)
        print("    systemctl --user status lanpad", file=sys.stderr)
        print("Либо укажите другой порт: lanpad --port 8478", file=sys.stderr)
        return 1

    _print_invitation(token, listen_port)
    caps = backends.capabilities()
    print(f"Громкость: {'да' if caps.audio else 'нет'}   "
          f"Медиа: {'да' if caps.media else 'нет'}   "
          f"Буфер обмена: {'да' if caps.clipboard else 'нет'}")
    print("Ctrl+C — остановить.\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nОстановлено.")
    finally:
        server.shutdown()
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
