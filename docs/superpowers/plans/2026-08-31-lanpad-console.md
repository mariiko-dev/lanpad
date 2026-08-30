# lanpad — консоль на компьютере. План реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Окно на компьютере с живым QR, состоянием связи, управлением службой, настройками и журналом — в лаунчпаде рабочего стола.

**Architecture:** Окно — веб-страница, которую агент раздаёт сам, открытая ярлыком в режиме приложения. Нативного тулкита нет намеренно: он потянул бы системные зависимости, а установка одной командой уже ломалась на недостающих заголовках. Консоль доступна только с петлевого интерфейса, потому что показывает QR, а в QR лежит токен.

**Tech Stack:** Python 3.11+ на стороне агента, Vite + React + TypeScript на стороне страницы, сборка через bun.

**Spec:** [docs/superpowers/specs/2026-08-29-lanpad-design.md](../specs/2026-08-29-lanpad-design.md), раздел «Консоль на компьютере»

## Global Constraints

- **Консоль доступна только с `127.0.0.1` и `::1`.** Проверка подсети, разрешающая всю локальную сеть, для неё не годится: страница показывает QR с токеном
- Токен не попадает в журнал событий никогда — ни в сообщениях, ни в адресах
- Управление службой вызывает `systemctl --user` и доступно только с петлевого интерфейса
- Инструмент сборки — `bun`, `package.json` обычный, CI гоняет на node
- Каталог сборки — ровно `src/lanpad/web`
- Имена файлов сборки содержат **шестнадцатеричный** хеш: агент кэширует только по образцу `-[0-9a-f]{6,}\.[ext]` (`http.py:97`)
- Код, комментарии, докстринги и сообщения коммитов — **на английском**
- Тесты не открывают сетевых сокетов, не вызывают `systemctl`, не пишут за пределы временного каталога
- Каждая задача заканчивается зелёными `pytest`, `ruff`, `bun run test`, `bun run typecheck`, `bun run lint`

## Что уже есть в агенте

Проверено по коду, не по памяти:

- `config.is_private_client(host)` — пускает приватные подсети, петлевой и link-local. Для консоли **недостаточно строг**
- `config.load_or_create_token()`, `config.port()`, `config.data_dir()`
- `qr.lan_addresses()`, `qr.connect_url(host, port, token)`, `qr.render_terminal(text)`, `qr.save_png(text, path)`
- `http.make_handler(session, token, web_root)` — маршруты `/`, `/manifest.webmanifest`, `/art`, `/ws`, `/e`, статика
- `service.unit_text(executable)`, `service.unit_path()`, `service.install()`
- `session.Session` с `add_listener`, `remove_listener`, `current_state`

---

### Task 1: Каркас сборки с двумя страницами

Проект Vite, собирающийся туда, откуда агент раздаёт статику, с двумя точками входа: приложение для телефона и консоль.

**Files:**
- Create: `web/package.json`, `web/vite.config.ts`, `web/tsconfig.json`, `web/index.html`, `web/console.html`, `web/src/main.tsx`, `web/src/console.tsx`
- Create: `web/src/build-name.test.ts`
- Modify: `.gitignore`, `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: ничего
- Produces: `bun run build`, `bun run test`, `bun run lint`, `bun run typecheck`; сборка в `src/lanpad/web` с файлами `index.html` и `console.html`

- [ ] **Step 1: Создать `web/package.json`**

```json
{
  "name": "lanpad-app",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc --noEmit && vite build",
    "typecheck": "tsc --noEmit",
    "lint": "eslint src",
    "test": "vitest run"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  },
  "devDependencies": {
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.3.0",
    "eslint": "^9.0.0",
    "typescript": "^5.6.0",
    "typescript-eslint": "^8.0.0",
    "vite": "^6.0.0",
    "vitest": "^2.1.0"
  }
}
```

- [ ] **Step 2: Создать `web/vite.config.ts`**

Ключевое — `hashCharacters: "hex"`. Без него Rollup даёт хеши в другом алфавите, агент их не распознаёт и выдаёт `no-cache` вместо вечного кэша, то есть обновление никогда не доходит до телефона.

```ts
import { resolve } from "node:path";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  build: {
    // The agent serves from here and only from here.
    outDir: "../src/lanpad/web",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        index: resolve(__dirname, "index.html"),
        console: resolve(__dirname, "console.html"),
      },
      output: {
        // The agent grants year-long caching only to hex-hashed names
        // (http.py `_HASHED_NAME`). Rollup's default alphabet never
        // matches, so upgrades would never reach a paired phone.
        hashCharacters: "hex",
        entryFileNames: "assets/[name]-[hash].js",
        chunkFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]",
      },
    },
  },
  test: { environment: "node" },
});
```

- [ ] **Step 3: Создать `web/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noEmit": true,
    "skipLibCheck": true,
    "types": ["vitest/globals"]
  },
  "include": ["src", "vite.config.ts"]
}
```

- [ ] **Step 4: Создать `web/index.html` и `web/console.html`**

`index.html`:
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover" />
    <meta name="theme-color" content="#000000" />
    <link rel="icon" href="/favicon.png" />
    <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
    <meta name="apple-mobile-web-app-capable" content="yes" />
    <title>lanpad</title>
  </head>
  <body><div id="root"></div><script type="module" src="/src/main.tsx"></script></body>
</html>
```

`console.html`:
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <link rel="icon" href="/favicon.png" />
    <title>lanpad</title>
  </head>
  <body><div id="root"></div><script type="module" src="/src/console.tsx"></script></body>
</html>
```

- [ ] **Step 5: Создать заглушки точек входа**

`web/src/main.tsx`:
```tsx
import { createRoot } from "react-dom/client";

const root = document.getElementById("root");
if (root) {
  createRoot(root).render(<div>lanpad</div>);
}
```

`web/src/console.tsx`:
```tsx
import { createRoot } from "react-dom/client";

const root = document.getElementById("root");
if (root) {
  createRoot(root).render(<div>lanpad console</div>);
}
```

- [ ] **Step 6: Перенести иконки прототипа**

```bash
mkdir -p web/public
git mv src/lanpad/web/icon-192.png src/lanpad/web/icon-512.png \
       src/lanpad/web/icon-maskable-512.png src/lanpad/web/favicon.png \
       src/lanpad/web/apple-touch-icon.png web/public/
```

- [ ] **Step 7: Написать падающий тест на имена сборки**

Создать `web/src/build-name.test.ts`:

```ts
import { existsSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

// Copied verbatim from the agent (http.py `_HASHED_NAME`). A name that
// does not match gets `no-cache`, so an upgrade would never reach a
// paired phone without clearing site data.
const AGENT_HASHED_NAME = /-[0-9a-f]{6,}\.[a-z0-9]+$/;

const built = join(__dirname, "..", "..", "src", "lanpad", "web");

describe("build output", () => {
  it("emits both pages", () => {
    expect(existsSync(join(built, "index.html"))).toBe(true);
    expect(existsSync(join(built, "console.html"))).toBe(true);
  });

  it("emits names the agent will cache forever", () => {
    const files = readdirSync(join(built, "assets")).filter((n) => /\.(js|css)$/.test(n));
    expect(files.length).toBeGreaterThan(0);
    for (const name of files) {
      expect(name).toMatch(AGENT_HASHED_NAME);
    }
  });
});
```

- [ ] **Step 8: Установить, собрать, проверить**

Run:
```bash
cd web && bun install && bun run build && bun run test
```
Expected: сборка проходит, тест зелёный. Приведи в отчёте список файлов в `src/lanpad/web/assets/` — имена обязаны выглядеть как `index-a1b2c3d4.js`

- [ ] **Step 9: Обновить `.gitignore` и CI**

В корневой `.gitignore` добавить:
```gitignore
web/node_modules/
bun.lockb
```

В `.github/workflows/ci.yml` добавить задание:
```yaml
  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: web
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
      - run: npm install
      - run: npm run typecheck
      - run: npm run lint
      - run: npm run test
      - run: npm run build
```

CI намеренно на npm, а не на bun: контрибьюторы придут с node, и ломаться должно там, где сломается у них.

- [ ] **Step 10: Коммит**

```bash
git add web .gitignore .github src/lanpad/web
git commit -m "build: vite scaffold with app and console entry points

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Проверка петлевого интерфейса

Отдельный барьер для консоли: она показывает QR, а в QR лежит токен.

**Files:**
- Modify: `src/lanpad/config.py`
- Modify: `tests/test_config.py`

**Interfaces:**
- Consumes: ничего
- Produces: `is_loopback_client(host: str) -> bool`

- [ ] **Step 1: Написать падающие тесты**

Добавить в `tests/test_config.py`:

```python
@pytest.mark.parametrize("host", ["127.0.0.1", "127.0.1.1", "::1", "[::1]"])
def test_loopback_clients_are_allowed(host):
    assert config.is_loopback_client(host) is True


@pytest.mark.parametrize("host", [
    "192.168.1.50", "10.0.0.7", "172.16.3.9", "fe80::1", "8.8.8.8",
])
def test_everything_beyond_this_machine_is_refused(host):
    """The console shows the QR, and the QR carries the token."""
    assert config.is_loopback_client(host) is False


@pytest.mark.parametrize("host", [None, 123, b"127.0.0.1", "", "   ", "not an address"])
def test_garbage_is_refused(host):
    assert config.is_loopback_client(host) is False


def test_mapped_loopback_is_allowed():
    """A dual-stack socket reports IPv4 loopback in this form."""
    assert config.is_loopback_client("::ffff:127.0.0.1") is True


def test_mapped_lan_address_is_still_refused():
    assert config.is_loopback_client("::ffff:192.168.1.50") is False
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `.venv/bin/pytest tests/test_config.py -q`
Expected: FAIL — `is_loopback_client` не существует

- [ ] **Step 3: Написать реализацию**

Добавить в `src/lanpad/config.py`:

```python
def is_loopback_client(host: str) -> bool:
    """Only this machine.

    Stricter than `is_private_client` on purpose: the console shows the
    pairing QR, and the QR carries the token. A page reachable from the
    whole network would hand the keyboard to anyone on the Wi-Fi.
    """
    if not isinstance(host, str):
        return False
    try:
        address = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return False
    mapped = getattr(address, "ipv4_mapped", None)
    return (mapped or address).is_loopback
```

- [ ] **Step 4: Убедиться, что тесты проходят**

Run: `.venv/bin/pytest -q && .venv/bin/ruff check .`

- [ ] **Step 5: Коммит**

```bash
git add src/lanpad/config.py tests/test_config.py
git commit -m "feat: loopback-only check for the console

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Журнал событий

Кольцевой буфер последних событий, чтобы окно показывало происходящее без похода в `journalctl`.

**Files:**
- Create: `src/lanpad/events.py`
- Create: `tests/test_events.py`

**Interfaces:**
- Consumes: ничего
- Produces:
  - `EventLog(capacity: int = 100)` с методами `add(kind: str, message: str)`, `entries() -> list[dict]`, `clear()`
  - Модульный экземпляр `log`

- [ ] **Step 1: Написать падающие тесты**

Создать `tests/test_events.py`:

```python
import pytest

from lanpad.events import EventLog


def test_entries_come_back_newest_first():
    log = EventLog()
    log.add("info", "первое")
    log.add("info", "второе")
    assert [e["message"] for e in log.entries()] == ["второе", "первое"]


def test_entries_carry_kind_and_time():
    log = EventLog()
    log.add("error", "сломалось")
    entry = log.entries()[0]
    assert entry["kind"] == "error"
    assert isinstance(entry["at"], float)


def test_oldest_entries_are_dropped():
    log = EventLog(capacity=3)
    for i in range(10):
        log.add("info", str(i))
    assert [e["message"] for e in log.entries()] == ["9", "8", "7"]


def test_clear_empties_the_log():
    log = EventLog()
    log.add("info", "что-то")
    log.clear()
    assert log.entries() == []


@pytest.mark.parametrize("secret", ["yTZZry26fEos", "t=yTZZry26fEos"])
def test_a_token_never_reaches_the_log(secret):
    """The console shows this log; a token in it defeats the whole barrier."""
    log = EventLog()
    log.add("info", f"phone connected http://192.168.1.5:8477/?{secret}")
    assert secret not in log.entries()[0]["message"]


def test_redaction_keeps_the_rest_of_the_message():
    log = EventLog()
    log.add("info", "phone connected from 192.168.1.5 with t=abc123")
    message = log.entries()[0]["message"]
    assert "192.168.1.5" in message
    assert "abc123" not in message


def test_entries_are_a_copy():
    """A caller mutating the result must not corrupt the log."""
    log = EventLog()
    log.add("info", "что-то")
    log.entries().clear()
    assert len(log.entries()) == 1
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `.venv/bin/pytest tests/test_events.py -q`
Expected: FAIL — модуля нет

- [ ] **Step 3: Написать `src/lanpad/events.py`**

```python
"""Recent events, for the console to show without touching journalctl."""

import re
import threading
import time
from collections import deque

DEFAULT_CAPACITY = 100

# Anything that looks like the pairing token, in a query string or bare.
_TOKEN = re.compile(r"(?:\bt=)?[A-Za-z0-9_-]{10,}")


def _redact(message: str) -> str:
    """Strip anything token-shaped.

    The console renders this log next to the QR. A token that leaked into
    a log line would defeat the barrier the whole page is built around.
    """
    return _TOKEN.sub("…", message)


class EventLog:
    """A bounded log of what the agent has been doing lately."""

    def __init__(self, capacity: int = DEFAULT_CAPACITY) -> None:
        self._entries: deque[dict] = deque(maxlen=capacity)
        self._lock = threading.Lock()

    def add(self, kind: str, message: str) -> None:
        with self._lock:
            self._entries.append({"kind": kind, "message": _redact(message), "at": time.time()})

    def entries(self) -> list[dict]:
        with self._lock:
            return list(reversed(self._entries))

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


log = EventLog()
```

- [ ] **Step 4: Убедиться, что тесты проходят**

Run: `.venv/bin/pytest -q && .venv/bin/ruff check .`

Обрати внимание: выражение отбраковки намеренно широкое. Оно съест и что-то безобидное — это дешевле, чем утёкший токен. Если какой-то тест из-за этого не сойдётся, скажи мне, а не ослабляй выражение.

- [ ] **Step 5: Коммит**

```bash
git add src/lanpad/events.py tests/test_events.py
git commit -m "feat: bounded event log that redacts anything token-shaped

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: Состояние и QR для консоли

Маршруты, отдающие окну всё, что оно показывает.

**Files:**
- Modify: `src/lanpad/http.py`
- Create: `tests/test_console_routes.py`

**Interfaces:**
- Consumes: `config.is_loopback_client`, `qr.lan_addresses`, `qr.connect_url`, `qr.save_png`, `events.log`, `session.Session`
- Produces:
  - `console_state(session, token, port) -> dict` с ключами `addresses`, `port`, `url`, `connected`, `caps`, `events`
  - Маршруты `GET /console`, `GET /console/state`, `GET /console/qr.png`

- [ ] **Step 1: Написать падающие тесты**

Создать `tests/test_console_routes.py`. Обработчик поднимается на двойниках, сокеты не открываются.

```python
import json

from lanpad import http as h
from lanpad.events import EventLog
from lanpad.platform.base import Backends
from lanpad.platform.fake import FakeAudio, FakeClipboard, FakeInput, FakeMedia
from lanpad.session import Session

TOKEN = "consoletoken123"


def make_session() -> Session:
    backends = Backends(FakeInput(), FakeAudio(), FakeMedia(), FakeClipboard())
    return Session(backends)


def test_state_carries_everything_the_window_shows():
    state = h.console_state(make_session(), TOKEN, 8477)
    assert isinstance(state["addresses"], list)
    assert state["port"] == 8477
    assert state["caps"]["audio"] is True
    assert isinstance(state["events"], list)
    assert isinstance(state["connected"], int)


def test_state_url_contains_the_token():
    """The window shows the pairing link; without the token it is useless."""
    state = h.console_state(make_session(), TOKEN, 8477)
    if state["url"]:
        assert TOKEN in state["url"]


def test_state_is_serialisable():
    json.dumps(h.console_state(make_session(), TOKEN, 8477))


def test_console_refuses_a_client_from_the_network(handler_from_network):
    """The console shows the QR, and the QR carries the token."""
    code = handler_from_network("/console")
    assert code == 403


def test_console_state_refuses_a_client_from_the_network(handler_from_network):
    assert handler_from_network("/console/state") == 403


def test_console_qr_refuses_a_client_from_the_network(handler_from_network):
    assert handler_from_network("/console/qr.png") == 403
```

Фикстуру `handler_from_network` напиши сам по образцу `tests/test_http_handler.py`, который уже есть в проекте: там обработчик собирается через `Handler.__new__` с перехватом `send_response`, `send_header`, `send_error` и заголовками через `email.message.Message`. Клиентский адрес задай `192.168.1.9`, вызывай `do_GET` и возвращай код ответа.

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `.venv/bin/pytest tests/test_console_routes.py -q`
Expected: FAIL — `console_state` не существует

- [ ] **Step 3: Добавить `console_state` в `src/lanpad/http.py`**

```python
def console_state(session: Session, token: str, port: int) -> dict:
    """Everything the desktop window shows.

    The pairing URL is rebuilt on every request rather than cached: the
    machine's address changes when the network does, and a stale QR is
    exactly the failure this window exists to prevent.
    """
    addresses = qr.lan_addresses()
    caps = session.capabilities()
    return {
        "addresses": addresses,
        "port": port,
        "url": qr.connect_url(addresses[0], port, token) if addresses else "",
        "connected": session.listener_count(),
        "caps": {"audio": caps.audio, "media": caps.media, "clipboard": caps.clipboard},
        "events": events.log.entries(),
    }
```

Добавь импорты `from lanpad import events, qr` и, если их ещё нет, `from lanpad.config import is_loopback_client`.

- [ ] **Step 4: Добавить в `Session` два метода**

В `src/lanpad/session.py`:

```python
    def capabilities(self) -> p.Capabilities:
        """What this machine can do, for the console."""
        return self._backends.capabilities()

    def listener_count(self) -> int:
        """How many phones are connected right now."""
        return len(self._listeners)
```

- [ ] **Step 5: Добавить маршруты в `do_GET`**

Перед веткой статики:

```python
            elif path.startswith("/console"):
                self._serve_console(path)
```

И метод в классе `Handler`:

```python
        def _serve_console(self, path: str) -> None:
            # Loopback only: this page shows the QR, and the QR carries
            # the token. The network-wide check used elsewhere would hand
            # the keyboard to anyone on the Wi-Fi.
            if not is_loopback_client(self.client_address[0]):
                self.send_error(403)
                return
            if path == "/console":
                self._serve_static("/console.html")
            elif path == "/console/state":
                self._respond(
                    200, "application/json",
                    json.dumps(console_state(session, token, self.server.server_address[1]),
                               ensure_ascii=False),
                    "no-store",
                )
            elif path == "/console/qr.png":
                self._serve_console_qr()
            else:
                self.send_error(404)

        def _serve_console_qr(self) -> None:
            state = console_state(session, token, self.server.server_address[1])
            if not state["url"]:
                self.send_error(404)
                return
            with tempfile.TemporaryDirectory() as folder:
                target = Path(folder) / "qr.png"
                try:
                    qr.save_png(state["url"], target)
                    body = target.read_bytes()
                except OSError:
                    self.send_error(500)
                    return
            self._respond(200, "image/png", body, "no-store")
```

Добавь импорты `import tempfile` и `from pathlib import Path`, если их нет.

- [ ] **Step 6: Записывать подключения в журнал**

В `_serve_websocket`, сразу после успешного рукопожатия:

```python
            events.log.add("info", f"phone connected from {self.client_address[0]}")
```

и в блоке `finally`, рядом со снятием получателя:

```python
                events.log.add("info", f"phone disconnected from {self.client_address[0]}")
```

- [ ] **Step 7: Убедиться, что всё зелёное**

Run: `.venv/bin/pytest -q && .venv/bin/ruff check .`

- [ ] **Step 8: Коммит**

```bash
git add src/lanpad/http.py src/lanpad/session.py tests/test_console_routes.py
git commit -m "feat: console state, QR and loopback-only routes

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: Управление службой

Единственное место, где веб-страница трогает систему. Поэтому — только с петлевого интерфейса и с явным перечнем допустимых действий.

**Files:**
- Modify: `src/lanpad/service.py`, `src/lanpad/http.py`
- Modify: `tests/test_service.py`, `tests/test_console_routes.py`

**Interfaces:**
- Consumes: `config.is_loopback_client`, `events.log`
- Produces:
  - `service.control(action: str) -> tuple[bool, str]`
  - `service.status() -> dict` с ключами `active`, `enabled`
  - Маршрут `POST /console/service`

- [ ] **Step 1: Написать падающие тесты**

Добавить в `tests/test_service.py`:

```python
def test_only_known_actions_are_accepted(monkeypatch):
    """An action list, not a command builder: this runs systemctl."""
    monkeypatch.setattr(service.shutil, "which", lambda _n: "/usr/bin/systemctl")
    ok, message = service.control("rm -rf /")
    assert ok is False
    assert "rm" not in message


@pytest.mark.parametrize("action", ["start", "stop", "restart", "enable", "disable"])
def test_known_actions_call_systemctl(monkeypatch, action):
    calls = []
    monkeypatch.setattr(service.shutil, "which", lambda _n: "/usr/bin/systemctl")
    monkeypatch.setattr(service.subprocess, "run",
                        lambda command, **kw: calls.append(command)
                        or subprocess.CompletedProcess(command, 0))
    ok, _ = service.control(action)
    assert ok is True
    assert calls[0][:3] == ["systemctl", "--user", action]


def test_control_reports_a_failure(monkeypatch):
    monkeypatch.setattr(service.shutil, "which", lambda _n: "/usr/bin/systemctl")
    monkeypatch.setattr(service.subprocess, "run",
                        lambda command, **kw: subprocess.CompletedProcess(command, 1, stderr="нет"))
    ok, _ = service.control("start")
    assert ok is False


def test_control_without_systemctl_explains_itself(monkeypatch):
    monkeypatch.setattr(service.shutil, "which", lambda _n: None)
    ok, message = service.control("start")
    assert ok is False
    assert "systemctl" in message


def test_control_survives_a_vanished_systemctl(monkeypatch):
    monkeypatch.setattr(service.shutil, "which", lambda _n: "/usr/bin/systemctl")

    def vanished(*args, **kwargs):
        raise FileNotFoundError("исчезла")

    monkeypatch.setattr(service.subprocess, "run", vanished)
    assert service.control("start")[0] is False


def test_status_reports_both_flags(monkeypatch):
    monkeypatch.setattr(service.shutil, "which", lambda _n: "/usr/bin/systemctl")
    monkeypatch.setattr(service.subprocess, "run",
                        lambda command, **kw: subprocess.CompletedProcess(command, 0, stdout="active\n"))
    assert service.status() == {"active": True, "enabled": True}


def test_status_without_systemctl_is_all_false(monkeypatch):
    monkeypatch.setattr(service.shutil, "which", lambda _n: None)
    assert service.status() == {"active": False, "enabled": False}
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `.venv/bin/pytest tests/test_service.py -q`
Expected: FAIL — `control` и `status` не существуют

- [ ] **Step 3: Написать реализацию в `src/lanpad/service.py`**

```python
# An allow-list, not a command builder: this runs systemctl, and the
# request comes from a web page.
ACTIONS = frozenset({"start", "stop", "restart", "enable", "disable"})


def control(action: str) -> tuple[bool, str]:
    """Run one known systemctl action. Returns success and a message."""
    if action not in ACTIONS:
        return False, "unknown action"
    if shutil.which("systemctl") is None:
        return False, "systemctl not found — this machine has no systemd"
    command = ["systemctl", "--user", action, UNIT_NAME]
    try:
        result = subprocess.run(  # noqa: S603
            command, capture_output=True, text=True, timeout=10, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    if result.returncode != 0:
        return False, (result.stderr or "").strip() or f"exit {result.returncode}"
    return True, ""


def _query(argument: str) -> bool:
    try:
        result = subprocess.run(  # noqa: S603
            ["systemctl", "--user", argument, UNIT_NAME],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.stdout.strip() in ("active", "enabled")


def status() -> dict:
    """Whether the service runs now and whether it starts at login."""
    if shutil.which("systemctl") is None:
        return {"active": False, "enabled": False}
    return {"active": _query("is-active"), "enabled": _query("is-enabled")}
```

- [ ] **Step 4: Добавить статус службы в состояние консоли**

В `console_state` добавь ключ:

```python
        "service": service.status(),
```

и импорт `from lanpad import events, qr, service`.

- [ ] **Step 5: Добавить маршрут в `do_POST`**

```python
            if urlparse(self.path).path == "/console/service":
                if not is_loopback_client(self.client_address[0]):
                    self.send_error(403)
                    return
                length = int(self.headers.get("Content-Length", 0) or 0)
                raw = self.rfile.read(min(length, 1024)) if length else b"{}"
                try:
                    action = json.loads(raw).get("action", "")
                except (ValueError, AttributeError):
                    self.send_error(400)
                    return
                ok, message = service.control(str(action))
                events.log.add("info" if ok else "error",
                               f"service {action}" + ("" if ok else f" failed: {message}"))
                self._respond(200, "application/json",
                              json.dumps({"ok": ok, "message": message}), "no-store")
                return
```

Поставь это **до** существующей проверки на `/e`, и убедись, что проверка подсети `_client_allowed` для этой ветки не мешает: консоль строже, а не слабее.

- [ ] **Step 6: Добавить тест, что сеть не пускается**

В `tests/test_console_routes.py`:

```python
def test_service_control_refuses_a_client_from_the_network(handler_post_from_network):
    """A web page from the Wi-Fi must not be able to stop the agent."""
    assert handler_post_from_network("/console/service", b'{"action":"stop"}') == 403
```

Фикстуру напиши по образцу существующих в `tests/test_http_handler.py`, вызывая `do_POST`.

- [ ] **Step 7: Убедиться, что всё зелёное**

Run: `.venv/bin/pytest -q && .venv/bin/ruff check .`

- [ ] **Step 8: Коммит**

```bash
git add src/lanpad/service.py src/lanpad/http.py tests
git commit -m "feat: service control from the console, loopback only

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 6: Страница консоли

**Files:**
- Create: `web/src/console.tsx`, `web/src/console/ConsoleApp.tsx`, `web/src/console/consoleState.ts`, `web/src/styles/console.css`
- Create: `web/src/console/consoleState.test.ts`

**Interfaces:**
- Consumes: маршруты `/console/state`, `/console/qr.png`, `/console/service`
- Produces: типы `ConsoleState`, функция `parseConsoleState`, компонент `ConsoleApp`

- [ ] **Step 1: Написать падающие тесты**

Создать `web/src/console/consoleState.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import { formatWhen, parseConsoleState } from "./consoleState";

const payload = JSON.stringify({
  addresses: ["192.168.1.50"],
  port: 8477,
  url: "http://192.168.1.50:8477/?t=abc",
  connected: 1,
  caps: { audio: true, media: true, clipboard: false },
  service: { active: true, enabled: true },
  events: [{ kind: "info", message: "phone connected", at: 1788000000 }],
});

describe("parseConsoleState", () => {
  it("reads a full payload", () => {
    const state = parseConsoleState(payload);
    expect(state?.port).toBe(8477);
    expect(state?.connected).toBe(1);
    expect(state?.service.active).toBe(true);
    expect(state?.events[0].message).toBe("phone connected");
  });

  it("survives an agent with no network address", () => {
    const state = parseConsoleState(JSON.stringify({
      addresses: [], port: 8477, url: "", connected: 0,
      caps: { audio: false, media: false, clipboard: false },
      service: { active: false, enabled: false }, events: [],
    }));
    expect(state?.url).toBe("");
    expect(state?.addresses).toEqual([]);
  });

  it("rejects nonsense", () => {
    expect(parseConsoleState("not json")).toBeNull();
    expect(parseConsoleState("[]")).toBeNull();
    expect(parseConsoleState("")).toBeNull();
  });
});

describe("formatWhen", () => {
  it("formats a timestamp as a clock time", () => {
    expect(formatWhen(1788000000)).toMatch(/^\d{1,2}:\d{2}/);
  });

  it("refuses nonsense", () => {
    expect(formatWhen(Number.NaN)).toBe("");
  });
});
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `cd web && bun run test src/console`
Expected: FAIL — модуля нет

- [ ] **Step 3: Написать `web/src/console/consoleState.ts`**

```ts
export interface ConsoleEvent {
  kind: string;
  message: string;
  at: number;
}

export interface ConsoleState {
  addresses: string[];
  port: number;
  url: string;
  connected: number;
  caps: { audio: boolean; media: boolean; clipboard: boolean };
  service: { active: boolean; enabled: boolean };
  events: ConsoleEvent[];
}

export function parseConsoleState(raw: string): ConsoleState | null {
  let payload: unknown;
  try {
    payload = JSON.parse(raw);
  } catch {
    return null;
  }
  if (typeof payload !== "object" || payload === null || Array.isArray(payload)) {
    return null;
  }
  const value = payload as Partial<ConsoleState>;
  if (typeof value.port !== "number" || !Array.isArray(value.addresses)) {
    return null;
  }
  return value as ConsoleState;
}

export function formatWhen(at: number): string {
  if (!Number.isFinite(at)) {
    return "";
  }
  return new Date(at * 1000).toLocaleTimeString();
}
```

- [ ] **Step 4: Написать `web/src/console/ConsoleApp.tsx`**

```tsx
import { useCallback, useEffect, useState } from "react";

import { formatWhen, parseConsoleState, type ConsoleState } from "./consoleState";

const POLL_MS = 2000;

export function ConsoleApp() {
  const [state, setState] = useState<ConsoleState | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const response = await fetch("/console/state", { cache: "no-store" });
      setState(parseConsoleState(await response.text()));
    } catch {
      setState(null);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), POLL_MS);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const act = async (action: string): Promise<void> => {
    setBusy(true);
    try {
      await fetch("/console/service", {
        method: "POST",
        body: JSON.stringify({ action }),
      });
    } catch {
      // The next poll shows what actually happened.
    } finally {
      setBusy(false);
      void refresh();
    }
  };

  if (!state) {
    return <main className="console"><p>Connecting to the agent…</p></main>;
  }

  return (
    <main className="console">
      <header>
        <h1>lanpad</h1>
        <span className={`badge${state.connected > 0 ? " on" : ""}`}>
          {state.connected > 0 ? `${state.connected} connected` : "no phone connected"}
        </span>
      </header>

      <section className="pairing">
        {state.url ? (
          <>
            {/* Re-fetched every poll: the address changes with the network,
                and a stale QR is what this window exists to prevent. */}
            <img className="qr" src={`/console/qr.png?at=${Date.now()}`} alt="Pairing QR code" />
            <code>{state.url}</code>
          </>
        ) : (
          <p>No network address. Connect to Wi-Fi and this updates itself.</p>
        )}
      </section>

      <section className="service">
        <div>
          Service: {state.service.active ? "running" : "stopped"},{" "}
          {state.service.enabled ? "starts at login" : "manual"}
        </div>
        <div className="buttons">
          <button type="button" disabled={busy} onClick={() => void act("start")}>Start</button>
          <button type="button" disabled={busy} onClick={() => void act("stop")}>Stop</button>
          <button type="button" disabled={busy} onClick={() => void act("restart")}>Restart</button>
          <button type="button" disabled={busy} onClick={() => void act("enable")}>Enable</button>
          <button type="button" disabled={busy} onClick={() => void act("disable")}>Disable</button>
        </div>
      </section>

      <section className="caps">
        Volume {state.caps.audio ? "yes" : "no"} · Media {state.caps.media ? "yes" : "no"} ·
        Clipboard {state.caps.clipboard ? "yes" : "no"}
      </section>

      <section className="log">
        <h2>Recent events</h2>
        <ul>
          {state.events.map((event, index) => (
            <li key={`${event.at}-${index}`} className={event.kind}>
              <time>{formatWhen(event.at)}</time> {event.message}
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
```

- [ ] **Step 5: Обновить `web/src/console.tsx`**

```tsx
import { createRoot } from "react-dom/client";

import { ConsoleApp } from "./console/ConsoleApp";
import "./styles/console.css";

const root = document.getElementById("root");
if (root) {
  createRoot(root).render(<ConsoleApp />);
}
```

- [ ] **Step 6: Написать `web/src/styles/console.css`**

```css
:root { color-scheme: dark; }

body {
  margin: 0;
  background: #000;
  color: #fff;
  font: 14px/1.5 system-ui, sans-serif;
}

.console { max-width: 560px; margin: 0 auto; padding: 24px; display: grid; gap: 20px; }
.console header { display: flex; align-items: center; gap: 12px; }
.console h1 { font-size: 20px; margin: 0; }
.badge { font-size: 12px; padding: 3px 9px; border-radius: 20px; background: #1c1c1e; color: #8e8e93; }
.badge.on { background: rgb(52 199 89 / 16%); color: #34c759; }

.pairing { display: grid; justify-items: center; gap: 12px; }
.qr { width: 220px; height: 220px; image-rendering: pixelated; background: #fff; padding: 10px; border-radius: 12px; }
.pairing code { font-size: 12px; color: #8e8e93; word-break: break-all; }

.service, .caps, .log { background: #0c0c0d; border: 0.5px solid #1c1c1e; border-radius: 14px; padding: 14px; }
.buttons { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
.buttons button { border: 0; border-radius: 9px; padding: 8px 14px; background: #1c1c1e; color: #fff; }
.buttons button:disabled { opacity: 0.5; }

.log h2 { font-size: 13px; margin: 0 0 8px; color: #8e8e93; font-weight: 600; }
.log ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 5px; max-height: 220px; overflow-y: auto; }
.log li { font-size: 12px; color: #c7c7cc; }
.log li.error { color: #ff453a; }
.log time { color: #636366; margin-right: 6px; }
```

- [ ] **Step 7: Собрать и проверить**

Run: `cd web && bun run build && bun run test && bun run typecheck && bun run lint`

- [ ] **Step 8: Коммит**

```bash
git add web/src src/lanpad/web
git commit -m "feat: console page with live QR, service control and log

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 7: Настройки в консоли

Перевыпуск токена и язык окна. Перевыпуск отвязывает все спаренные телефоны, поэтому спрашивает подтверждение и говорит об этом прямо.

**Files:**
- Modify: `src/lanpad/config.py`, `src/lanpad/http.py`
- Modify: `tests/test_config.py`, `tests/test_console_routes.py`
- Modify: `web/src/console/ConsoleApp.tsx`

**Interfaces:**
- Consumes: `config.token_path`, `config.load_or_create_token`, `events.log`
- Produces: `config.reissue_token(path=None) -> str`, маршрут `POST /console/token`

- [ ] **Step 1: Написать падающие тесты**

Добавить в `tests/test_config.py`:

```python
def test_reissue_replaces_the_token(tmp_path):
    token_file = tmp_path / "token"
    first = config.load_or_create_token(token_file)
    second = config.reissue_token(token_file)
    assert second != first
    assert token_file.read_text().strip() == second


def test_reissued_token_is_private(tmp_path):
    token_file = tmp_path / "token"
    config.load_or_create_token(token_file)
    config.reissue_token(token_file)
    assert token_file.stat().st_mode & 0o077 == 0


def test_reissue_works_without_an_existing_token(tmp_path):
    token_file = tmp_path / "token"
    assert config.reissue_token(token_file)
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `.venv/bin/pytest tests/test_config.py -q`
Expected: FAIL — `reissue_token` не существует

- [ ] **Step 3: Написать реализацию**

Добавить в `src/lanpad/config.py`:

```python
def reissue_token(path: Path | None = None) -> str:
    """Replace the pairing token.

    Every paired phone stops working the moment this runs — their links
    carry the old token. The console says so before offering the button.
    """
    target = path or token_path()
    token = secrets.token_urlsafe(TOKEN_BYTES)
    target.parent.mkdir(parents=True, exist_ok=True)
    _write_private(target, token + "\n")
    return token
```

- [ ] **Step 4: Добавить маршрут**

В `do_POST`, рядом с веткой управления службой:

```python
            if urlparse(self.path).path == "/console/token":
                if not is_loopback_client(self.client_address[0]):
                    self.send_error(403)
                    return
                config.reissue_token()
                events.log.add("info", "pairing token reissued, paired phones must scan again")
                self._respond(200, "application/json", json.dumps({"ok": True}), "no-store")
                return
```

Добавь импорт `from lanpad import config`.

Обрати внимание: работающий агент держит прежний токен в памяти, поэтому новый вступит в силу после перезапуска службы. Окно обязано сказать об этом человеку — иначе он перевыпустит токен, отсканирует новый код и не поймёт, почему ничего не изменилось.

- [ ] **Step 5: Добавить тест, что из сети недоступно**

В `tests/test_console_routes.py`:

```python
def test_token_reissue_refuses_a_client_from_the_network(handler_post_from_network):
    """Anyone on the Wi-Fi could otherwise unpair every phone."""
    assert handler_post_from_network("/console/token", b"{}") == 403
```

- [ ] **Step 6: Добавить в окно**

В `ConsoleApp.tsx`, перед разделом журнала:

```tsx
      <section className="settings">
        <h2>Settings</h2>
        <p className="warning">
          Reissuing the token unpairs every phone. They will need to scan the new
          code, and the change takes effect after the service restarts.
        </p>
        <button
          type="button"
          disabled={busy}
          onClick={() => {
            if (window.confirm("Unpair every phone and issue a new token?")) {
              void fetch("/console/token", { method: "POST" }).finally(() => void refresh());
            }
          }}
        >
          Reissue token
        </button>
      </section>
```

- [ ] **Step 7: Убедиться, что всё зелёное**

Run: `.venv/bin/pytest -q && .venv/bin/ruff check . && cd web && bun run test && bun run typecheck && bun run lint`

- [ ] **Step 8: Коммит**

```bash
git add src/lanpad/config.py src/lanpad/http.py web/src tests
git commit -m "feat: token reissue from the console

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 8: Ярлык в лаунчпаде

**Files:**
- Create: `src/lanpad/desktop.py`
- Modify: `src/lanpad/service.py`, `src/lanpad/__main__.py`
- Create: `tests/test_desktop.py`

**Interfaces:**
- Consumes: `config.port`
- Produces:
  - `desktop.browser_command(port: int) -> list[str] | None`
  - `desktop.entry_text(command: list[str]) -> str`
  - `desktop.entry_path() -> Path`
  - `desktop.install(port: int) -> tuple[bool, str]`

- [ ] **Step 1: Написать падающие тесты**

Создать `tests/test_desktop.py`:

```python
from lanpad import desktop


def test_prefers_a_browser_with_app_mode(monkeypatch):
    """App mode gives a window without an address bar — a real app."""
    monkeypatch.setattr(desktop.shutil, "which",
                        lambda name: "/usr/bin/google-chrome" if name == "google-chrome" else None)
    command = desktop.browser_command(8477)
    assert command is not None
    assert any(part.startswith("--app=http://127.0.0.1:8477/console") for part in command)


def test_falls_back_to_the_next_browser(monkeypatch):
    monkeypatch.setattr(desktop.shutil, "which",
                        lambda name: "/usr/bin/epiphany" if name == "epiphany" else None)
    assert desktop.browser_command(8477) is not None


def test_without_any_browser_there_is_no_command(monkeypatch):
    monkeypatch.setattr(desktop.shutil, "which", lambda _name: None)
    assert desktop.browser_command(8477) is None


def test_entry_is_a_valid_desktop_file():
    text = desktop.entry_text(["/usr/bin/google-chrome", "--app=http://127.0.0.1:8477/console"])
    assert text.startswith("[Desktop Entry]")
    assert "Type=Application" in text
    assert "Exec=/usr/bin/google-chrome" in text
    assert "Icon=lanpad" in text


def test_entry_never_carries_the_token():
    """A .desktop file is world-readable; the console needs no token."""
    text = desktop.entry_text(["/usr/bin/x", "--app=http://127.0.0.1:8477/console"])
    assert "t=" not in text


def test_entry_path_follows_xdg(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    assert desktop.entry_path() == tmp_path / "applications" / "lanpad.desktop"


def test_install_writes_the_entry(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setattr(desktop.shutil, "which",
                        lambda name: "/usr/bin/google-chrome" if name == "google-chrome" else None)
    ok, _ = desktop.install(8477)
    assert ok is True
    assert desktop.entry_path().exists()


def test_install_without_a_browser_explains_itself(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setattr(desktop.shutil, "which", lambda _name: None)
    ok, message = desktop.install(8477)
    assert ok is False
    assert "browser" in message.lower()
    assert not desktop.entry_path().exists()
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `.venv/bin/pytest tests/test_desktop.py -q`
Expected: FAIL — модуля нет

- [ ] **Step 3: Написать `src/lanpad/desktop.py`**

```python
"""The launcher entry that opens the console in a window."""

import os
import shutil
from pathlib import Path

ENTRY_NAME = "lanpad.desktop"

# Browsers that can open a window without an address bar, best first.
APP_MODE_BROWSERS: tuple[tuple[str, str], ...] = (
    ("google-chrome", "--app={url}"),
    ("chromium", "--app={url}"),
    ("chromium-browser", "--app={url}"),
    ("microsoft-edge", "--app={url}"),
    ("epiphany", "--application-mode"),
)


def browser_command(port: int) -> list[str] | None:
    """A command that opens the console as its own window.

    The console is loopback-only, so the address is fixed and needs no
    token — which is just as well, since a .desktop file is readable by
    anyone on the machine.
    """
    url = f"http://127.0.0.1:{port}/console"
    for name, flag in APP_MODE_BROWSERS:
        found = shutil.which(name)
        if found:
            return [found, flag.format(url=url)] if "{url}" in flag else [found, flag, url]
    fallback = shutil.which("xdg-open")
    return [fallback, url] if fallback else None


def entry_text(command: list[str]) -> str:
    return f"""[Desktop Entry]
Type=Application
Name=lanpad
Comment=Pair a phone and control this computer
Exec={" ".join(command)}
Icon=lanpad
Terminal=false
Categories=Utility;RemoteAccess;
StartupWMClass=lanpad
"""


def entry_path() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    return Path(base) / "applications" / ENTRY_NAME


def install(port: int) -> tuple[bool, str]:
    """Write the launcher entry. Returns success and a message."""
    command = browser_command(port)
    if command is None:
        return False, "No browser found — cannot open the console window."
    target = entry_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(entry_text(command))
        target.chmod(0o755)
    except OSError as exc:
        return False, f"Could not write {target}: {exc.strerror or exc}"
    return True, str(target)
```

- [ ] **Step 4: Ставить ярлык вместе со службой**

В `src/lanpad/service.py`, в конце `install()`, перед `return 0`:

```python
    from lanpad import config, desktop

    ok, message = desktop.install(config.port())
    if ok:
        print(f"Launcher entry written: {message}")
    else:
        print(f"Launcher entry skipped: {message}")
```

Неудача с ярлыком не должна проваливать установку службы: агент работает и без окна.

- [ ] **Step 5: Положить значок**

```bash
mkdir -p src/lanpad/icons
cp web/public/icon-512.png src/lanpad/icons/lanpad.png
```

И в `desktop.install`, перед записью ярлыка, скопировать значок в каталог тем:

```python
    icon_source = Path(__file__).parent / "icons" / "lanpad.png"
    icon_target = Path(base_data_dir()) / "icons" / "hicolor" / "512x512" / "apps" / "lanpad.png"
```

Добавь рядом с `entry_path()`:

```python
def base_data_dir() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    return Path(base)


def _install_icon() -> None:
    """Copy the icon into the theme. Cosmetic — never fails the install."""
    source = Path(__file__).parent / "icons" / "lanpad.png"
    target = base_data_dir() / "icons" / "hicolor" / "512x512" / "apps" / "lanpad.png"
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    except OSError:
        pass
```

и вызови `_install_icon()` в начале `install()`. Значок косметика, окно важнее: его неудача не должна проваливать установку ярлыка.

Добавь в `pyproject.toml`, в `package-data`:
```toml
lanpad = ["web/**/*", "icons/*.png"]
```

- [ ] **Step 6: Убедиться, что всё зелёное**

Run: `.venv/bin/pytest -q && .venv/bin/ruff check .`

- [ ] **Step 7: Коммит**

```bash
git add src/lanpad/desktop.py src/lanpad/icons src/lanpad/service.py tests/test_desktop.py pyproject.toml
git commit -m "feat: launcher entry opening the console in its own window

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 9: Сквозная проверка

**Files:**
- Modify: `THIRD-PARTY.md` при необходимости

- [ ] **Step 1: Убедиться, что от прототипа ничего не осталось**

```bash
grep -rn "NoteOverlay\|note-overlay\|/vol\|serviceWorker" src/lanpad/web/ && echo "НАЙДЕНО" || echo "чисто"
ls src/lanpad/web
```

Должны быть `index.html`, `console.html`, `assets/`, иконки. Файлов прототипа (`htm.js`, `react.js`, `app.js`) быть не должно.

- [ ] **Step 2: Поднять агент и проверить маршруты**

```bash
.venv/bin/python -m lanpad --port 8620
```

В другом терминале:
```bash
curl -s -o /dev/null -w "%{http_code} консоль\n" "http://127.0.0.1:8620/console"
curl -s -o /dev/null -w "%{http_code} состояние\n" "http://127.0.0.1:8620/console/state"
curl -s -o /dev/null -w "%{http_code} QR\n" "http://127.0.0.1:8620/console/qr.png"
curl -s "http://127.0.0.1:8620/console/state" | head -c 400
```

Ожидание: три раза `200` и осмысленный JSON. Приложи вывод дословно.

- [ ] **Step 3: Проверить, что из сети консоль недоступна**

Определи адрес машины и обратись по нему, а не по петлевому:

```bash
ADDR=$(.venv/bin/python -c "from lanpad import qr; print(qr.lan_addresses()[0])")
curl -s -o /dev/null -w "%{http_code} консоль из сети (ожидается 403)\n" "http://$ADDR:8620/console"
curl -s -o /dev/null -w "%{http_code} состояние из сети (ожидается 403)\n" "http://$ADDR:8620/console/state"
curl -s -o /dev/null -w "%{http_code} управление из сети (ожидается 403)\n" -X POST -d '{"action":"stop"}' "http://$ADDR:8620/console/service"
```

**Все три обязаны дать 403.** Если хоть один даст что-то другое — останови работу и сообщи мне: это дыра, через которую сосед по Wi-Fi получает и токен, и выключатель агента.

- [ ] **Step 4: Проверить, что токен не течёт в журнал**

```bash
curl -s "http://127.0.0.1:8620/console/state" | grep -o "$(cat ~/.local/share/lanpad/token)" && echo "ТОКЕН В ЖУРНАЛЕ" || echo "в журнале токена нет"
```

Токен обязан встречаться только в поле `url`, которое и есть ссылка для спаривания, и нигде в `events`.

- [ ] **Step 5: Прогнать оба набора**

```bash
.venv/bin/pytest -q
.venv/bin/ruff check .
cd web && bun run test && bun run typecheck && bun run lint
```

- [ ] **Step 6: Коммит**

```bash
git add -A
git commit -m "chore: replace the prototype with the built console and app shell

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Проверка перед сдачей плана

- [ ] `.venv/bin/pytest -q`, `.venv/bin/ruff check .` — зелёные
- [ ] `bun run test`, `bun run typecheck`, `bun run lint` — зелёные
- [ ] Консоль, её состояние, QR и управление службой отвечают `403` при обращении из локальной сети
- [ ] Токен не встречается в журнале событий
- [ ] Имена файлов сборки совпадают с образцом агента `-[0-9a-f]{6,}\.[ext]`
- [ ] Ярлык записывается и не содержит токена
- [ ] Смена порта из окна НЕ реализована намеренно: порт приходит из переменной
      окружения, а её задаёт юнит службы. Для настройки из окна нужен файл
      конфигурации, которого в проекте пока нет — отдельное решение, не эта задача

## Что проверяет пользователь

- [ ] `lanpad --install-service` ставит и службу, и ярлык
- [ ] Приложение `lanpad` появилось в лаунчпаде
- [ ] Окно открывается без адресной строки, показывает QR и состояние
- [ ] QR из окна сканируется телефоном и открывает приложение
- [ ] Смена сети перерисовывает QR сама, без перезапуска
- [ ] Кнопки управления службой работают
