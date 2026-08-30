# lanpad — приложение. План реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Написать приложение для телефона, которое говорит на протоколе агента: тачпад, клавиатура, медиа-панель с обложкой и перемоткой, фейдеры громкости и позиции, два языка.

**Architecture:** Vite + React + TypeScript, сборка в каталог, который раздаёт агент. Движение пальца не проходит через React: координаты пишутся напрямую в DOM, отправка батчится по кадру. Состояние приходит от агента по тому же сокету, в который уходят события. Цвет интерфейса извлекается из обложки на стороне телефона.

**Tech Stack:** Vite 6, React 19, TypeScript 5, vitest. Сборка через bun, `package.json` совместим с npm.

**Spec:** [docs/superpowers/specs/2026-08-29-lanpad-design.md](../specs/2026-08-29-lanpad-design.md)

## Global Constraints

- Инструмент сборки — `bun` (в песочнице исполнителя нет node, он не запускается). `package.json` при этом обычный: контрибьютор с npm ничего не замечает. CI гоняет на node
- Каталог сборки — ровно `src/lanpad/web`, его раздаёт агент (`__main__.py:12`)
- Имена файлов сборки обязаны содержать **шестнадцатеричный** хеш: агент выдаёт вечное кэширование только по образцу `-[0-9a-f]{6,}\.[ext]` (`http.py:97`). Иначе обновление агента не дойдёт до спаренного телефона никогда
- Иконки `icon-192.png`, `icon-512.png`, `icon-maskable-512.png`, `favicon.png`, `apple-touch-icon.png` лежат в корне сборки, не в `assets/` — их путь зашит в манифест агента (`http.py:84-96`)
- Манифест запрашивается **только с токеном**: `/manifest.webmanifest?t=<токен>`. Без токена агент отдаёт 403, и установка на домашний экран не проходит
- Обложка от плеера принимается только со схемой `http`, `https` или как собственный путь `/art?id=`. Всё остальное отбрасывается
- Service Worker не используется. Файла `sw.js` быть не должно
- **На тачпаде не применяется `backdrop-filter` никогда.** Цвет даётся заливкой
- Движение пальца не вызывает перерисовку React
- Языки интерфейса — русский и английский, автоопределение по `navigator.languages` с переключателем в настройках. Строки живут в одном файле на язык
- Код, комментарии, докстринги и сообщения коммитов — **на английском**
- Тесты — vitest, только на чистую логику. DOM не тестируется
- Каждая задача заканчивается зелёными `bun run lint`, `bun run typecheck`, `bun run test`

## Протокол, с которым работаем

Проверено по коду агента, не по памяти.

**Телефон → агент**, массив событий в одном сообщении, не больше 512 штук:

| Событие | Форма | Предел |
|---|---|---|
| движение | `["m", dx, dy]` | ±4000 |
| колесо | `["w", n]` | ±200 |
| кнопка | `["bd", "l"]` / `["bu", "l"]` | `l`, `r`, `m` |
| клик | `["click", "l"]` | |
| клавиша | `["tap", "escape"]` | |
| удержание | `["kd", "ctrl"]` / `["ku", "ctrl"]` | |
| сочетание | `["combo", ["ctrl", "c"]]` | до 6 клавиш |
| набор | `["type", "text"]` | до 10000 символов |
| вставка | `["paste", "текст"]` / `["tpaste", "..."]` | |
| громкость | `["vol", ±n]`, `["volset", 0..100]`, `["volmute"]` | |
| медиа | `["media", "play"|"next"|"prev"]` | |
| перемотка | `["seek", секунды]` | 0..86400 |

**Агент → телефон**, по изменению:

```json
{
  "type": "state",
  "audio": { "volume": 62, "muted": false },
  "media": { "playing": true, "title": "…", "artist": "…", "art": "…",
             "position": 134.2, "duration": 355.0, "canSeek": true },
  "caps": { "audio": true, "media": true, "clipboard": true }
}
```

`audio` и `media` бывают `null`. `art` бывает `null`, внешней ссылкой или путём `/art?id=…`.

## Структура файлов

```
web/                          проект Vite, в корне репозитория
├── package.json
├── vite.config.ts            сборка в ../src/lanpad/web, хеши hex
├── tsconfig.json
├── index.html
├── public/                   иконки, копируются в корень сборки
└── src/
    ├── main.tsx
    ├── App.tsx               композиция экрана
    ├── protocol.ts           типы состояния и конструкторы событий
    ├── transport.ts          сокет, очередь, батч по кадру, запасной POST
    ├── token.ts              токен из адреса, подключение манифеста
    ├── theme.ts              цвет из обложки, три режима насыщенности
    ├── settings.ts           хранение настроек
    ├── i18n/
    │   ├── index.ts          выбор языка, хук
    │   ├── en.ts
    │   └── ru.ts
    ├── components/
    │   ├── StatusBar.tsx
    │   ├── Trackpad.tsx      движение, клики, прокрутка, полоса у края
    │   ├── Fader.tsx         общий для громкости и позиции
    │   ├── VolumeRow.tsx
    │   ├── MediaCard.tsx
    │   ├── ClickRow.tsx
    │   ├── QuickKeys.tsx
    │   ├── KeyboardSheet.tsx
    │   ├── Onboarding.tsx
    │   └── Settings.tsx
    └── styles/app.css
```

---

### Task 1: Каркас сборки

Проект Vite, собирающийся ровно туда, откуда агент раздаёт статику, с именами файлов, которые агент согласится кэшировать.

**Files:**
- Create: `web/package.json`, `web/vite.config.ts`, `web/tsconfig.json`, `web/index.html`, `web/src/main.tsx`, `web/.gitignore`
- Create: `web/src/build-name.test.ts`
- Modify: `.gitignore`, `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: ничего
- Produces: команды `bun run build`, `bun run test`, `bun run lint`, `bun run typecheck`; каталог сборки `src/lanpad/web`

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

Ключевое здесь — `hashCharacters: "hex"`. Без него Rollup генерирует хеши в другом алфавите, агент их не распознаёт и выдаёт `no-cache` вместо вечного кэша.

```ts
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  build: {
    // The agent serves from here and only this path.
    outDir: "../src/lanpad/web",
    emptyOutDir: true,
    rollupOptions: {
      output: {
        // The agent grants year-long caching only to hex-hashed names
        // (see http.py `_HASHED_NAME`). Rollup's default alphabet is
        // base64url, which would never match, so every upgrade would
        // reach paired phones only after a manual cache purge.
        hashCharacters: "hex",
        entryFileNames: "assets/[name]-[hash].js",
        chunkFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]",
      },
    },
  },
  test: {
    environment: "node",
  },
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
    "noFallthroughCasesInSwitch": true,
    "noEmit": true,
    "skipLibCheck": true,
    "types": ["vitest/globals"]
  },
  "include": ["src", "vite.config.ts"]
}
```

- [ ] **Step 4: Создать `web/index.html`**

Ссылки на манифест здесь нет намеренно: он требует токен, который известен только в рантайме. Подключается в задаче 12.

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
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
    <title>lanpad</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 5: Создать `web/src/main.tsx` заглушкой**

```tsx
import { createRoot } from "react-dom/client";

const root = document.getElementById("root");
if (root) {
  createRoot(root).render(<div>lanpad</div>);
}
```

- [ ] **Step 6: Перенести иконки прототипа в `web/public/`**

```bash
mkdir -p web/public
git mv src/lanpad/web/icon-192.png src/lanpad/web/icon-512.png \
       src/lanpad/web/icon-maskable-512.png src/lanpad/web/favicon.png \
       src/lanpad/web/apple-touch-icon.png web/public/
```

- [ ] **Step 7: Написать падающий тест на имена файлов сборки**

Создать `web/src/build-name.test.ts`. Тест повторяет выражение агента дословно — если оно разойдётся с реальностью, обновления перестанут кэшироваться молча.

```ts
import { readdirSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

// Copied verbatim from the agent (http.py `_HASHED_NAME`). Names that do
// not match get `no-cache`, so an upgrade would never reach a paired
// phone without clearing site data.
const AGENT_HASHED_NAME = /-[0-9a-f]{6,}\.[a-z0-9]+$/;

describe("build output", () => {
  it("emits names the agent will cache forever", () => {
    const assets = join(__dirname, "..", "..", "src", "lanpad", "web", "assets");
    const files = readdirSync(assets).filter((name) => /\.(js|css)$/.test(name));
    expect(files.length).toBeGreaterThan(0);
    for (const name of files) {
      expect(name).toMatch(AGENT_HASHED_NAME);
    }
  });
});
```

- [ ] **Step 8: Установить зависимости и убедиться, что тест падает**

Run:
```bash
cd web && bun install && bun run test
```
Expected: тест падает — каталог сборки ещё содержит файлы прототипа без хешей

- [ ] **Step 9: Собрать и убедиться, что тест проходит**

Run:
```bash
cd web && bun run build && bun run test
```
Expected: сборка проходит, тест зелёный. Выведи список файлов в `src/lanpad/web/assets/` и приложи в отчёт — имена обязаны выглядеть как `index-a1b2c3d4.js`

- [ ] **Step 10: Обновить `.gitignore` в корне**

Добавить:
```gitignore
web/node_modules/
web/dist/
bun.lockb
```

Собранный `src/lanpad/web` **остаётся под контролем версий**: он входит в устанавливаемый пакет.

- [ ] **Step 11: Добавить сборку фронта в CI**

В `.github/workflows/ci.yml` добавить задание рядом с существующим:

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

CI намеренно гоняет npm, а не bun: контрибьюторы придут с node, и ломаться должно там, где сломается у них.

- [ ] **Step 12: Проверить и закоммитить**

Run: `cd web && bun run typecheck && bun run lint && bun run test`

```bash
git add web .gitignore .github src/lanpad/web
git commit -m "build: vite scaffold emitting hex-hashed assets the agent caches

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Типы протокола и словари языков

Чистые модули без React. Типы описывают ровно то, что шлёт агент; словари — ровно то, что видит человек.

**Files:**
- Create: `web/src/protocol.ts`, `web/src/i18n/en.ts`, `web/src/i18n/ru.ts`, `web/src/i18n/index.ts`
- Create: `web/src/protocol.test.ts`, `web/src/i18n/i18n.test.ts`

**Interfaces:**
- Consumes: ничего
- Produces:
  - Типы `AudioState`, `MediaState`, `Capabilities`, `AgentState`, `Event`
  - `parseState(raw: string): AgentState | null`
  - `safeArtUrl(art: string | null): string | null`
  - Тип `Strings`, словари `en`, `ru`, `pickLanguage(preferred: readonly string[]): "en" | "ru"`, `strings(lang)`

- [ ] **Step 1: Написать падающие тесты протокола**

Создать `web/src/protocol.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import { parseState, safeArtUrl } from "./protocol";

const full = JSON.stringify({
  type: "state",
  audio: { volume: 62, muted: false },
  media: {
    playing: true, title: "Bohemian Rhapsody", artist: "Queen",
    art: "/art?id=abc", position: 134.2, duration: 355, canSeek: true,
  },
  caps: { audio: true, media: true, clipboard: true },
});

describe("parseState", () => {
  it("reads a full state message", () => {
    const state = parseState(full);
    expect(state?.audio?.volume).toBe(62);
    expect(state?.media?.title).toBe("Bohemian Rhapsody");
    expect(state?.media?.canSeek).toBe(true);
    expect(state?.caps.clipboard).toBe(true);
  });

  it("accepts null audio and media", () => {
    const state = parseState(JSON.stringify({
      type: "state", audio: null, media: null,
      caps: { audio: false, media: false, clipboard: false },
    }));
    expect(state?.audio).toBeNull();
    expect(state?.media).toBeNull();
  });

  it("rejects anything that is not a state message", () => {
    expect(parseState("not json")).toBeNull();
    expect(parseState(JSON.stringify({ type: "other" }))).toBeNull();
    expect(parseState(JSON.stringify([1, 2, 3]))).toBeNull();
    expect(parseState("")).toBeNull();
  });
});

describe("safeArtUrl", () => {
  it("keeps http and https covers", () => {
    expect(safeArtUrl("https://cdn.example/a.jpg")).toBe("https://cdn.example/a.jpg");
    expect(safeArtUrl("http://cdn.example/a.jpg")).toBe("http://cdn.example/a.jpg");
  });

  it("keeps our own proxied path", () => {
    expect(safeArtUrl("/art?id=abc")).toBe("/art?id=abc");
  });

  it("refuses everything else", () => {
    // A local player controls this string; it must not become a page URL.
    expect(safeArtUrl("javascript:alert(1)")).toBeNull();
    expect(safeArtUrl("data:image/png;base64,AAAA")).toBeNull();
    expect(safeArtUrl("file:///etc/passwd")).toBeNull();
    expect(safeArtUrl("//evil.example/a.jpg")).toBeNull();
    expect(safeArtUrl("/other/path")).toBeNull();
    expect(safeArtUrl(null)).toBeNull();
    expect(safeArtUrl("")).toBeNull();
  });
});
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `cd web && bun run test src/protocol.test.ts`
Expected: FAIL — модуля `./protocol` нет

- [ ] **Step 3: Написать `web/src/protocol.ts`**

```ts
/** Types and helpers for the wire format the agent speaks. */

export interface AudioState {
  volume: number | null;
  muted: boolean;
}

export interface MediaState {
  playing: boolean;
  title: string;
  artist: string;
  art: string | null;
  position: number;
  duration: number;
  canSeek: boolean;
}

export interface Capabilities {
  audio: boolean;
  media: boolean;
  clipboard: boolean;
}

export interface AgentState {
  audio: AudioState | null;
  media: MediaState | null;
  caps: Capabilities;
}

/** One outgoing event. The agent validates these again on its side. */
export type Event =
  | ["m", number, number]
  | ["w", number]
  | ["bd" | "bu", "l" | "r" | "m"]
  | ["click", "l" | "r" | "m"]
  | ["tap", string]
  | ["kd" | "ku", string]
  | ["combo", string[]]
  | ["type", string]
  | ["paste" | "tpaste", string]
  | ["vol", number]
  | ["volset", number]
  | ["volmute"]
  | ["media", "play" | "next" | "prev"]
  | ["seek", number];

/** The agent refuses packets larger than this, so we never build one. */
export const MAX_EVENTS = 512;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function parseState(raw: string): AgentState | null {
  let payload: unknown;
  try {
    payload = JSON.parse(raw);
  } catch {
    return null;
  }
  if (!isRecord(payload) || payload.type !== "state" || !isRecord(payload.caps)) {
    return null;
  }
  return {
    audio: isRecord(payload.audio) ? (payload.audio as unknown as AudioState) : null,
    media: isRecord(payload.media) ? (payload.media as unknown as MediaState) : null,
    caps: payload.caps as unknown as Capabilities,
  };
}

/**
 * A cover URL comes from whatever player is running on the machine, so it
 * is not trusted. Only real image sources and our own proxy path pass.
 */
export function safeArtUrl(art: string | null): string | null {
  if (!art) {
    return null;
  }
  if (art.startsWith("/art?id=")) {
    return art;
  }
  return /^https?:\/\/[^/]/.test(art) ? art : null;
}
```

- [ ] **Step 4: Написать падающие тесты словарей**

Создать `web/src/i18n/i18n.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import { en } from "./en";
import { pickLanguage, strings } from "./index";
import { ru } from "./ru";

describe("pickLanguage", () => {
  it("picks russian for russian speakers", () => {
    expect(pickLanguage(["ru-RU", "en-US"])).toBe("ru");
    expect(pickLanguage(["ru"])).toBe("ru");
  });

  it("falls back to english for everything else", () => {
    expect(pickLanguage(["en-GB"])).toBe("en");
    expect(pickLanguage(["de-DE"])).toBe("en");
    expect(pickLanguage([])).toBe("en");
  });

  it("honours the first understood language, not the first listed", () => {
    expect(pickLanguage(["de-DE", "ru-RU", "en-US"])).toBe("ru");
  });
});

describe("dictionaries", () => {
  it("cover the same keys", () => {
    expect(Object.keys(ru).sort()).toEqual(Object.keys(en).sort());
  });

  it("have no empty strings", () => {
    for (const dict of [en, ru]) {
      for (const [key, value] of Object.entries(dict)) {
        expect(value, key).not.toBe("");
      }
    }
  });

  it("keep russian labels short enough for buttons", () => {
    // Russian runs about a third longer than English; a label that
    // overflows on the narrowest phone is a broken layout, not a detail.
    const buttonKeys = ["click", "rightClick", "paste", "pasteTerminal", "done"] as const;
    for (const key of buttonKeys) {
      expect(ru[key].length, key).toBeLessThanOrEqual(14);
    }
  });

  it("resolves a dictionary by language", () => {
    expect(strings("ru")).toBe(ru);
    expect(strings("en")).toBe(en);
  });
});
```

- [ ] **Step 5: Убедиться, что тесты падают**

Run: `cd web && bun run test src/i18n`
Expected: FAIL — модулей нет

- [ ] **Step 6: Написать `web/src/i18n/en.ts`**

```ts
export const en = {
  connected: "connected",
  connecting: "looking for the computer…",
  trackpadHint: "touch and drag",
  click: "Click",
  rightClick: "Right",
  middleClick: "Middle",
  volume: "Volume",
  mute: "Mute",
  quieter: "Quieter",
  louder: "Louder",
  nothingPlaying: "Nothing playing",
  play: "Play or pause",
  next: "Next track",
  previous: "Previous track",
  keyboard: "Keyboard",
  keyboardHint: "Type here — letters go to the computer. Modifier plus key makes a shortcut.",
  pasteField: "Text to paste, Cyrillic included",
  paste: "Paste",
  pasteTerminal: "To terminal",
  done: "Done",
  settings: "Settings",
  sensitivity: "Sensitivity",
  naturalScrolling: "Natural scrolling",
  haptics: "Vibration feedback",
  showMedia: "Media panel",
  saturation: "Colour",
  saturationCalm: "Calm",
  saturationNormal: "Normal",
  saturationRich: "Rich",
  language: "Language",
  onboardingTitle: "Scan the code on your computer",
  onboardingBody: "This page needs the token from the QR code the agent prints. Open the link from that code and the touchpad appears.",
} as const;

export type Strings = typeof en;
```

- [ ] **Step 7: Написать `web/src/i18n/ru.ts`**

```ts
import type { Strings } from "./en";

export const ru: Strings = {
  connected: "на связи",
  connecting: "ищу компьютер…",
  trackpadHint: "коснись и веди",
  click: "Клик",
  rightClick: "Правый",
  middleClick: "Средний",
  volume: "Громкость",
  mute: "Без звука",
  quieter: "Тише",
  louder: "Громче",
  nothingPlaying: "Ничего не играет",
  play: "Пуск или пауза",
  next: "Следующий трек",
  previous: "Предыдущий трек",
  keyboard: "Клавиатура",
  keyboardHint: "Печатай — буквы идут на компьютер. Модификатор и клавиша дают сочетание.",
  pasteField: "Текст для вставки, кириллицу тоже",
  paste: "Вставить",
  pasteTerminal: "В терминал",
  done: "Готово",
  settings: "Настройки",
  sensitivity: "Чувствительность",
  naturalScrolling: "Естественная прокрутка",
  haptics: "Отклик вибрацией",
  showMedia: "Медиа-панель",
  saturation: "Цвет",
  saturationCalm: "Спокойный",
  saturationNormal: "Обычный",
  saturationRich: "Насыщенный",
  language: "Язык",
  onboardingTitle: "Отсканируй код на компьютере",
  onboardingBody: "Странице нужен токен из QR-кода, который печатает агент. Открой ссылку из этого кода, и появится тачпад.",
};
```

- [ ] **Step 8: Написать `web/src/i18n/index.ts`**

```ts
import { en, type Strings } from "./en";
import { ru } from "./ru";

export type Language = "en" | "ru";

const DICTIONARIES: Record<Language, Strings> = { en, ru };

/**
 * Pick a language from the phone's preference list.
 *
 * The first *understood* entry wins, not the first listed: a phone set to
 * German with Russian second should get Russian, not English.
 */
export function pickLanguage(preferred: readonly string[]): Language {
  for (const tag of preferred) {
    const base = tag.toLowerCase().split("-")[0];
    if (base === "ru") {
      return "ru";
    }
    if (base === "en") {
      return "en";
    }
  }
  return "en";
}

export function strings(language: Language): Strings {
  return DICTIONARIES[language];
}

export type { Strings };
```

- [ ] **Step 9: Убедиться, что тесты проходят**

Run: `cd web && bun run test && bun run typecheck && bun run lint`
Expected: всё зелёное

- [ ] **Step 10: Коммит**

```bash
git add web/src/protocol.ts web/src/protocol.test.ts web/src/i18n
git commit -m "feat: wire format types and language dictionaries

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Транспорт

Соединение с агентом: очередь событий, отправка раз в кадр, приём состояния, запасной путь по HTTP при разрыве.

**Files:**
- Create: `web/src/token.ts`, `web/src/transport.ts`
- Create: `web/src/transport.test.ts`

**Interfaces:**
- Consumes: `protocol.Event`, `protocol.AgentState`, `protocol.parseState`, `protocol.MAX_EVENTS`
- Produces:
  - `readToken(search: string): string`
  - `EventQueue` с методами `push(event)`, `drain(): Event[]`, `size(): number`
  - `useTransport(token)` возвращающий `{ send, connected, state }`

- [ ] **Step 1: Написать падающие тесты**

Создать `web/src/transport.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import { MAX_EVENTS } from "./protocol";
import { readToken } from "./token";
import { EventQueue } from "./transport";

describe("readToken", () => {
  it("reads the token the QR link carries", () => {
    expect(readToken("?t=abc123")).toBe("abc123");
  });

  it("decodes percent escapes", () => {
    expect(readToken("?t=a%2Bb")).toBe("a+b");
  });

  it("returns empty when absent", () => {
    expect(readToken("")).toBe("");
    expect(readToken("?other=1")).toBe("");
  });
});

describe("EventQueue", () => {
  it("hands events over in order", () => {
    const queue = new EventQueue();
    queue.push(["m", 1, 2]);
    queue.push(["click", "l"]);
    expect(queue.drain()).toEqual([["m", 1, 2], ["click", "l"]]);
  });

  it("empties on drain", () => {
    const queue = new EventQueue();
    queue.push(["w", 1]);
    queue.drain();
    expect(queue.drain()).toEqual([]);
  });

  it("drops the oldest events rather than growing without bound", () => {
    // A stalled connection during a long drag must not build a packet the
    // agent will refuse outright — it refuses anything over MAX_EVENTS,
    // which would throw away the recent moves along with the stale ones.
    const queue = new EventQueue();
    for (let i = 0; i < MAX_EVENTS + 50; i += 1) {
      queue.push(["m", i, 0]);
    }
    const drained = queue.drain();
    expect(drained.length).toBe(MAX_EVENTS);
    expect(drained[drained.length - 1]).toEqual(["m", MAX_EVENTS + 49, 0]);
  });

  it("reports its size", () => {
    const queue = new EventQueue();
    expect(queue.size()).toBe(0);
    queue.push(["w", 1]);
    expect(queue.size()).toBe(1);
  });
});
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `cd web && bun run test src/transport.test.ts`
Expected: FAIL — модулей нет

- [ ] **Step 3: Написать `web/src/token.ts`**

```ts
/** The pairing token travels in the URL the QR code encodes. */
export function readToken(search: string): string {
  return new URLSearchParams(search).get("t") ?? "";
}
```

- [ ] **Step 4: Написать `web/src/transport.ts`**

```ts
import { useCallback, useEffect, useRef, useState } from "react";

import { MAX_EVENTS, parseState, type AgentState, type Event } from "./protocol";

const FLUSH_HEARTBEAT_MS = 25_000;
const RECONNECT_DELAY_MS = 1_000;

/**
 * Events waiting for the next frame.
 *
 * When the connection stalls mid-drag the queue would grow without bound,
 * and the agent refuses packets over MAX_EVENTS outright — losing the
 * recent moves along with the stale ones. Dropping the oldest keeps the
 * cursor responsive the moment the link comes back.
 */
export class EventQueue {
  private events: Event[] = [];

  push(event: Event): void {
    this.events.push(event);
    if (this.events.length > MAX_EVENTS) {
      this.events.splice(0, this.events.length - MAX_EVENTS);
    }
  }

  drain(): Event[] {
    const drained = this.events;
    this.events = [];
    return drained;
  }

  size(): number {
    return this.events.length;
  }
}

export interface Transport {
  send: (event: Event) => void;
  connected: boolean;
  state: AgentState | null;
}

export function useTransport(token: string): Transport {
  const [connected, setConnected] = useState(false);
  const [state, setState] = useState<AgentState | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const queueRef = useRef(new EventQueue());

  useEffect(() => {
    if (!token) {
      return undefined;
    }
    const query = `t=${encodeURIComponent(token)}`;
    let stopped = false;
    let frame = 0;

    const postFallback = (payload: string): void => {
      void fetch(`/e?${query}`, { method: "POST", body: payload, keepalive: true })
        .catch(() => undefined);
    };

    const connect = (): void => {
      if (stopped) {
        return;
      }
      const scheme = location.protocol === "https:" ? "wss" : "ws";
      const socket = new WebSocket(`${scheme}://${location.host}/ws?${query}`);
      socketRef.current = socket;
      socket.onopen = () => setConnected(true);
      socket.onmessage = (message) => {
        const next = parseState(String(message.data));
        if (next) {
          setState(next);
        }
      };
      socket.onclose = () => {
        setConnected(false);
        socketRef.current = null;
        if (!stopped) {
          window.setTimeout(connect, RECONNECT_DELAY_MS);
        }
      };
      socket.onerror = () => socket.close();
    };
    connect();

    const heartbeat = window.setInterval(() => {
      const socket = socketRef.current;
      if (socket?.readyState === WebSocket.OPEN) {
        socket.send("[]");
      }
    }, FLUSH_HEARTBEAT_MS);

    const flush = (): void => {
      if (queueRef.current.size() > 0) {
        const payload = JSON.stringify(queueRef.current.drain());
        const socket = socketRef.current;
        if (socket?.readyState === WebSocket.OPEN) {
          socket.send(payload);
        } else {
          postFallback(payload);
        }
      }
      frame = requestAnimationFrame(flush);
    };
    frame = requestAnimationFrame(flush);

    return () => {
      stopped = true;
      window.clearInterval(heartbeat);
      cancelAnimationFrame(frame);
      socketRef.current?.close();
    };
  }, [token]);

  const send = useCallback((event: Event) => {
    queueRef.current.push(event);
  }, []);

  return { send, connected, state };
}
```

- [ ] **Step 5: Убедиться, что тесты проходят**

Run: `cd web && bun run test && bun run typecheck && bun run lint`
Expected: всё зелёное

- [ ] **Step 6: Коммит**

```bash
git add web/src/token.ts web/src/transport.ts web/src/transport.test.ts
git commit -m "feat: batched transport with state channel and HTTP fallback

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: Тачпад

Движение, клики касанием, прокрутка двумя пальцами, перетаскивание двойным касанием. Обработчики вешаются напрямую и в React не заходят.

**Files:**
- Create: `web/src/components/Trackpad.tsx`, `web/src/gestures.ts`
- Create: `web/src/gestures.test.ts`

**Interfaces:**
- Consumes: `protocol.Event`, `settings.Settings`
- Produces:
  - `accelerate(distance: number, factor: number): number`
  - `ScrollAccumulator` с методом `add(delta: number, natural: boolean): number`
  - `isTap(elapsedMs: number, travelled: number): boolean`
  - Компонент `Trackpad`

- [ ] **Step 1: Написать падающие тесты**

Создать `web/src/gestures.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import { ScrollAccumulator, accelerate, isTap } from "./gestures";

describe("accelerate", () => {
  it("moves further for a faster swipe", () => {
    expect(accelerate(20, 1)).toBeGreaterThan(accelerate(2, 1));
  });

  it("scales with the sensitivity setting", () => {
    expect(accelerate(10, 2)).toBeGreaterThan(accelerate(10, 1));
  });

  it("stays bounded so a flick cannot throw the cursor across the desk", () => {
    // The agent refuses moves over 4000, and a refused move is a lost one.
    expect(accelerate(10_000, 2.4)).toBeLessThan(4000);
  });

  it("never inverts direction", () => {
    expect(accelerate(0, 1)).toBeGreaterThanOrEqual(0);
  });
});

describe("ScrollAccumulator", () => {
  it("holds back fractions until a whole notch is due", () => {
    const acc = new ScrollAccumulator();
    expect(acc.add(4, false)).toBe(0);
    expect(acc.add(4, false)).toBe(0);
    expect(acc.add(4, false)).not.toBe(0);
  });

  it("keeps the remainder between calls", () => {
    const acc = new ScrollAccumulator();
    let total = 0;
    for (let i = 0; i < 100; i += 1) {
      total += acc.add(1.2, false);
    }
    expect(Math.abs(total)).toBeGreaterThan(9);
  });

  it("flips direction for natural scrolling", () => {
    const normal = new ScrollAccumulator();
    const natural = new ScrollAccumulator();
    expect(Math.sign(normal.add(40, false))).toBe(-Math.sign(natural.add(40, true)));
  });
});

describe("isTap", () => {
  it("accepts a quick still touch", () => {
    expect(isTap(120, 4)).toBe(true);
  });

  it("refuses a slow touch", () => {
    expect(isTap(900, 2)).toBe(false);
  });

  it("refuses a touch that travelled", () => {
    expect(isTap(120, 40)).toBe(false);
  });
});
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `cd web && bun run test src/gestures.test.ts`
Expected: FAIL — модуля нет

- [ ] **Step 3: Написать `web/src/gestures.ts`**

```ts
const SCROLL_SCALE = 0.09;
const TAP_MAX_MS = 240;
const TAP_MAX_TRAVEL = 12;
const MAX_STEP = 3900; // the agent refuses anything past 4000

/**
 * Pointer acceleration.
 *
 * A slow drag should land on a pixel; a fast one should cross the screen.
 * The result is capped below the agent's own limit, because a refused
 * move is a lost move, not a clamped one.
 */
export function accelerate(distance: number, factor: number): number {
  const boosted = factor * (1 + Math.min(distance * 0.06, 4));
  return Math.min(boosted, MAX_STEP);
}

/** Turns finger travel into whole wheel notches, keeping the remainder. */
export class ScrollAccumulator {
  private remainder = 0;

  add(delta: number, natural: boolean): number {
    this.remainder += delta * SCROLL_SCALE * (natural ? 1 : -1);
    const whole = Math.trunc(this.remainder);
    this.remainder -= whole;
    return whole;
  }
}

export function isTap(elapsedMs: number, travelled: number): boolean {
  return elapsedMs < TAP_MAX_MS && travelled < TAP_MAX_TRAVEL;
}
```

- [ ] **Step 4: Написать `web/src/components/Trackpad.tsx`**

```tsx
import { useEffect, useRef } from "react";

import { ScrollAccumulator, accelerate, isTap } from "../gestures";
import type { Event } from "../protocol";
import type { Settings } from "../settings";

interface Props {
  send: (event: Event) => void;
  settings: Settings;
  hint: string;
}

interface Point {
  x: number;
  y: number;
}

/**
 * The touch surface.
 *
 * Handlers are attached to the DOM node directly and never call setState:
 * a re-render per frame of finger movement is exactly the latency this
 * project exists to avoid.
 */
export function Trackpad({ send, settings, hint }: Props) {
  const padRef = useRef<HTMLDivElement>(null);
  const glowRef = useRef<HTMLDivElement>(null);
  const settingsRef = useRef(settings);
  settingsRef.current = settings;

  useEffect(() => {
    const pad = padRef.current;
    const glow = glowRef.current;
    if (!pad || !glow) {
      return undefined;
    }

    const points = new Map<number, Point>();
    const scroll = new ScrollAccumulator();
    let startedAt = 0;
    let travelled = 0;
    let twoFinger = false;
    let dragArmed = false;
    let dragging = false;
    let lastTapAt = 0;

    const moveGlow = (x: number, y: number, visible: boolean): void => {
      const box = pad.getBoundingClientRect();
      glow.style.transform = `translate(${x - box.left}px, ${y - box.top}px)`;
      glow.style.opacity = visible ? "1" : "0";
    };

    const onStart = (event: TouchEvent): void => {
      event.preventDefault();
      for (const touch of Array.from(event.changedTouches)) {
        points.set(touch.identifier, { x: touch.clientX, y: touch.clientY });
      }
      const lead = event.changedTouches[0];
      if (lead) {
        moveGlow(lead.clientX, lead.clientY, true);
      }
      if (points.size === 1) {
        startedAt = performance.now();
        travelled = 0;
        twoFinger = false;
        dragArmed = performance.now() - lastTapAt < 300;
      }
    };

    const onMove = (event: TouchEvent): void => {
      event.preventDefault();
      const touches = Array.from(event.touches);
      const lead = touches[0];
      if (lead) {
        moveGlow(lead.clientX, lead.clientY, true);
      }

      if (points.size === 1 && touches.length === 1) {
        const touch = touches[0];
        const previous = points.get(touch.identifier);
        if (!previous) {
          return;
        }
        const dx = touch.clientX - previous.x;
        const dy = touch.clientY - previous.y;
        previous.x = touch.clientX;
        previous.y = touch.clientY;
        const distance = Math.hypot(dx, dy);
        travelled += distance;
        if (dragArmed && !dragging) {
          send(["bd", "l"]);
          dragging = true;
        }
        const factor = accelerate(distance, settingsRef.current.sensitivity);
        send(["m", Math.round(dx * factor), Math.round(dy * factor)]);
        return;
      }

      if (touches.length >= 2) {
        twoFinger = true;
        let sum = 0;
        let counted = 0;
        for (const touch of touches) {
          const previous = points.get(touch.identifier);
          if (previous) {
            sum += touch.clientY - previous.y;
            previous.x = touch.clientX;
            previous.y = touch.clientY;
            counted += 1;
          }
        }
        if (counted > 0) {
          travelled += Math.abs(sum);
          const notches = scroll.add(sum / counted, settingsRef.current.naturalScrolling);
          if (notches !== 0) {
            send(["w", notches]);
          }
        }
      }
    };

    const onEnd = (event: TouchEvent): void => {
      event.preventDefault();
      const last = event.changedTouches[0];
      for (const touch of Array.from(event.changedTouches)) {
        points.delete(touch.identifier);
      }
      if (points.size > 0) {
        return;
      }

      const elapsed = performance.now() - startedAt;
      if (dragging) {
        send(["bu", "l"]);
        dragging = false;
      } else if (twoFinger) {
        if (isTap(elapsed, travelled)) {
          send(["click", "r"]);
        }
      } else if (isTap(elapsed, travelled)) {
        send(["click", "l"]);
        lastTapAt = performance.now();
      }
      dragArmed = false;
      twoFinger = false;
      travelled = 0;
      if (last) {
        moveGlow(last.clientX, last.clientY, false);
      }
    };

    pad.addEventListener("touchstart", onStart, { passive: false });
    pad.addEventListener("touchmove", onMove, { passive: false });
    pad.addEventListener("touchend", onEnd, { passive: false });
    pad.addEventListener("touchcancel", onEnd, { passive: false });
    return () => {
      pad.removeEventListener("touchstart", onStart);
      pad.removeEventListener("touchmove", onMove);
      pad.removeEventListener("touchend", onEnd);
      pad.removeEventListener("touchcancel", onEnd);
    };
  }, [send]);

  return (
    <div className="pad" ref={padRef}>
      <div className="pad-glow" ref={glowRef} />
      <span className="pad-hint">{hint}</span>
    </div>
  );
}
```

- [ ] **Step 5: Убедиться, что всё зелёное**

Run: `cd web && bun run test && bun run typecheck && bun run lint`

- [ ] **Step 6: Коммит**

```bash
git add web/src/gestures.ts web/src/gestures.test.ts web/src/components/Trackpad.tsx
git commit -m "feat: trackpad surface driving the DOM without React re-renders

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: Полоса прокрутки у правого края

Ведение одним пальцем вдоль правого края прокручивает страницу — для случая, когда телефон держат одной рукой.

**Files:**
- Modify: `web/src/gestures.ts`, `web/src/components/Trackpad.tsx`
- Modify: `web/src/gestures.test.ts`

**Interfaces:**
- Consumes: `gestures.ScrollAccumulator`
- Produces: `isInScrollStrip(x: number, box: { left: number; width: number }): boolean`, константа `SCROLL_STRIP_MIN_PX`

- [ ] **Step 1: Написать падающие тесты**

Добавить в `web/src/gestures.test.ts`:

```ts
import { SCROLL_STRIP_MIN_PX, isInScrollStrip } from "./gestures";

describe("isInScrollStrip", () => {
  const wide = { left: 0, width: 400 };

  it("claims touches at the right edge", () => {
    expect(isInScrollStrip(395, wide)).toBe(true);
  });

  it("leaves the rest of the pad alone", () => {
    expect(isInScrollStrip(200, wide)).toBe(false);
    expect(isInScrollStrip(0, wide)).toBe(false);
  });

  it("stays wide enough to hit with a thumb on a narrow phone", () => {
    // A tenth of a narrow pad would be a few millimetres — unhittable
    // blind, which is exactly how this strip gets used.
    const narrow = { left: 0, width: 200 };
    const boundary = 200 - SCROLL_STRIP_MIN_PX + 1;
    expect(isInScrollStrip(boundary, narrow)).toBe(true);
  });

  it("respects the element offset", () => {
    expect(isInScrollStrip(495, { left: 100, width: 400 })).toBe(true);
    expect(isInScrollStrip(105, { left: 100, width: 400 })).toBe(false);
  });
});
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `cd web && bun run test src/gestures.test.ts`
Expected: FAIL — `isInScrollStrip` не экспортируется

- [ ] **Step 3: Добавить в `web/src/gestures.ts`**

```ts
export const SCROLL_STRIP_MIN_PX = 28;
const SCROLL_STRIP_SHARE = 0.1;

/**
 * Is this touch in the edge strip that scrolls with one finger?
 *
 * A tenth of the pad is right on a large phone and unhittable on a small
 * one, so the strip never gets narrower than a thumb.
 */
export function isInScrollStrip(x: number, box: { left: number; width: number }): boolean {
  const stripWidth = Math.max(box.width * SCROLL_STRIP_SHARE, SCROLL_STRIP_MIN_PX);
  return x >= box.left + box.width - stripWidth;
}
```

- [ ] **Step 4: Подключить в `Trackpad.tsx`**

В `useEffect`, рядом с остальным состоянием жеста, добавить:

```ts
    let scrollingByEdge = false;
```

В `onStart`, внутри ветки `if (points.size === 1)`, первой строкой:

```ts
        const lead0 = event.changedTouches[0];
        // A touch belongs to whatever it started on. Without this the
        // strip would hand the gesture back to the cursor on the first
        // slanted movement, and scrolling would jerk.
        scrollingByEdge = lead0 ? isInScrollStrip(lead0.clientX, pad.getBoundingClientRect()) : false;
```

В `onMove`, в начале ветки одного пальца (сразу после получения `previous`), заменить остаток ветки на:

```ts
        const dx = touch.clientX - previous.x;
        const dy = touch.clientY - previous.y;
        previous.x = touch.clientX;
        previous.y = touch.clientY;
        travelled += Math.hypot(dx, dy);

        if (scrollingByEdge) {
          const notches = scroll.add(dy, settingsRef.current.naturalScrolling);
          if (notches !== 0) {
            send(["w", notches]);
          }
          return;
        }

        if (dragArmed && !dragging) {
          send(["bd", "l"]);
          dragging = true;
        }
        const factor = accelerate(Math.hypot(dx, dy), settingsRef.current.sensitivity);
        send(["m", Math.round(dx * factor), Math.round(dy * factor)]);
        return;
```

В `onEnd`, перед проверкой на клик, добавить:

```ts
      if (scrollingByEdge) {
        // A grab at the edge must not turn into a click somewhere.
        scrollingByEdge = false;
        dragArmed = false;
        travelled = 0;
        if (last) {
          moveGlow(last.clientX, last.clientY, false);
        }
        return;
      }
```

И импортировать `isInScrollStrip` из `../gestures`.

- [ ] **Step 5: Пометить полосу в разметке**

В возвращаемом JSX, перед `pad-hint`:

```tsx
      <div className="pad-strip" aria-hidden="true" />
```

Невидимая функция бесполезна: край помечается ненавязчиво и подсвечивается при касании.

- [ ] **Step 6: Убедиться, что всё зелёное**

Run: `cd web && bun run test && bun run typecheck && bun run lint`

- [ ] **Step 7: Коммит**

```bash
git add web/src/gestures.ts web/src/gestures.test.ts web/src/components/Trackpad.tsx
git commit -m "feat: one-finger scroll strip along the right edge

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 6: Фейдер

Общий компонент для громкости и позиции. Здесь вся соль: пока палец на экране, ручка слушается только пальца.

**Files:**
- Create: `web/src/fader.ts`, `web/src/components/Fader.tsx`
- Create: `web/src/fader.test.ts`

**Interfaces:**
- Consumes: ничего
- Produces:
  - `valueFromPosition(clientX, box, min, max): number`
  - `FaderLock` с `grab()`, `release(now)`, `accepts(now): boolean`
  - `SEND_INTERVAL_MS`, `LOCK_AFTER_RELEASE_MS`
  - Компонент `Fader`

- [ ] **Step 1: Написать падающие тесты**

Создать `web/src/fader.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import { FaderLock, LOCK_AFTER_RELEASE_MS, valueFromPosition } from "./fader";

const box = { left: 100, width: 200 };

describe("valueFromPosition", () => {
  it("maps the ends of the track", () => {
    expect(valueFromPosition(100, box, 0, 100)).toBe(0);
    expect(valueFromPosition(300, box, 0, 100)).toBe(100);
  });

  it("maps the middle", () => {
    expect(valueFromPosition(200, box, 0, 100)).toBe(50);
  });

  it("clamps outside the track", () => {
    expect(valueFromPosition(0, box, 0, 100)).toBe(0);
    expect(valueFromPosition(9999, box, 0, 100)).toBe(100);
  });

  it("works for an arbitrary range, like track position", () => {
    expect(valueFromPosition(200, box, 0, 355)).toBeCloseTo(177.5, 1);
  });

  it("survives a zero-width track", () => {
    expect(valueFromPosition(50, { left: 0, width: 0 }, 0, 100)).toBe(0);
  });
});

describe("FaderLock", () => {
  it("ignores incoming state while the finger is down", () => {
    const lock = new FaderLock();
    lock.grab();
    expect(lock.accepts(1000)).toBe(false);
  });

  it("keeps ignoring briefly after release", () => {
    // A packet sent before our change can still be in flight; applying it
    // would snap the knob back under the user's finger.
    const lock = new FaderLock();
    lock.grab();
    lock.release(1000);
    expect(lock.accepts(1000 + LOCK_AFTER_RELEASE_MS - 50)).toBe(false);
  });

  it("accepts state once the grace period passes", () => {
    const lock = new FaderLock();
    lock.grab();
    lock.release(1000);
    expect(lock.accepts(1000 + LOCK_AFTER_RELEASE_MS + 1)).toBe(true);
  });

  it("accepts state when it was never touched", () => {
    expect(new FaderLock().accepts(0)).toBe(true);
  });
});
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `cd web && bun run test src/fader.test.ts`
Expected: FAIL — модуля нет

- [ ] **Step 3: Написать `web/src/fader.ts`**

```ts
export const SEND_INTERVAL_MS = 60;
export const LOCK_AFTER_RELEASE_MS = 400;

/** Where along the track the finger is, in the fader's own units. */
export function valueFromPosition(
  clientX: number,
  box: { left: number; width: number },
  min: number,
  max: number,
): number {
  if (box.width <= 0) {
    return min;
  }
  const share = Math.min(Math.max((clientX - box.left) / box.width, 0), 1);
  return min + share * (max - min);
}

/**
 * Decides whether incoming state may move the knob.
 *
 * While a finger is on the fader the knob obeys the finger alone, and for
 * a moment after release too: a packet sent before our change can still
 * arrive, and applying it would snap the knob backwards.
 */
export class FaderLock {
  private held = false;
  private releasedAt = -Infinity;

  grab(): void {
    this.held = true;
  }

  release(now: number): void {
    this.held = false;
    this.releasedAt = now;
  }

  accepts(now: number): boolean {
    return !this.held && now - this.releasedAt > LOCK_AFTER_RELEASE_MS;
  }
}
```

- [ ] **Step 4: Написать `web/src/components/Fader.tsx`**

```tsx
import { useEffect, useRef, useState } from "react";

import { FaderLock, SEND_INTERVAL_MS, valueFromPosition } from "../fader";

interface Props {
  value: number | null;
  min: number;
  max: number;
  disabled?: boolean;
  label: string;
  onChange: (value: number) => void;
  format?: (value: number) => string;
}

/**
 * A draggable fader.
 *
 * Used for both volume and track position; the only difference is the
 * range and what the caller does with the value.
 */
export function Fader({ value, min, max, disabled, label, onChange, format }: Props) {
  const trackRef = useRef<HTMLDivElement>(null);
  const lockRef = useRef(new FaderLock());
  const lastSentAt = useRef(0);
  const [local, setLocal] = useState<number | null>(value);

  useEffect(() => {
    if (lockRef.current.accepts(performance.now())) {
      setLocal(value);
    }
  }, [value]);

  const apply = (clientX: number, force: boolean): void => {
    const track = trackRef.current;
    if (!track) {
      return;
    }
    const next = valueFromPosition(clientX, track.getBoundingClientRect(), min, max);
    setLocal(next);
    const now = performance.now();
    if (force || now - lastSentAt.current >= SEND_INTERVAL_MS) {
      lastSentAt.current = now;
      onChange(next);
    }
  };

  const onPointerDown = (event: React.PointerEvent<HTMLDivElement>): void => {
    if (disabled) {
      return;
    }
    event.currentTarget.setPointerCapture(event.pointerId);
    lockRef.current.grab();
    apply(event.clientX, true);
  };

  const onPointerMove = (event: React.PointerEvent<HTMLDivElement>): void => {
    if (disabled || !event.currentTarget.hasPointerCapture(event.pointerId)) {
      return;
    }
    apply(event.clientX, false);
  };

  const onPointerUp = (event: React.PointerEvent<HTMLDivElement>): void => {
    if (disabled) {
      return;
    }
    // The last position must always go out, throttle or not.
    apply(event.clientX, true);
    lockRef.current.release(performance.now());
  };

  const shown = local ?? min;
  const share = max > min ? ((shown - min) / (max - min)) * 100 : 0;

  return (
    <div
      className={`fader${disabled ? " disabled" : ""}`}
      role="slider"
      aria-label={label}
      aria-valuenow={Math.round(shown)}
      aria-valuemin={min}
      aria-valuemax={max}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
    >
      <div className="fader-track" ref={trackRef}>
        <div className="fader-fill" style={{ width: `${share}%` }} />
        <div className="fader-knob" style={{ left: `${share}%` }} />
      </div>
      {format ? <span className="fader-value">{format(shown)}</span> : null}
    </div>
  );
}
```

- [ ] **Step 5: Убедиться, что всё зелёное**

Run: `cd web && bun run test && bun run typecheck && bun run lint`

- [ ] **Step 6: Коммит**

```bash
git add web/src/fader.ts web/src/fader.test.ts web/src/components/Fader.tsx
git commit -m "feat: fader that obeys the finger while it is down

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 7: Настройки и хранение

**Files:**
- Create: `web/src/settings.ts`, `web/src/settings.test.ts`

**Interfaces:**
- Consumes: `i18n.Language`, `i18n.pickLanguage`
- Produces:
  - Тип `Settings` с полями `sensitivity`, `naturalScrolling`, `haptics`, `showMedia`, `saturation`, `language`
  - `DEFAULT_SETTINGS`
  - `loadSettings(storage, languages): Settings`
  - `saveSettings(storage, settings): void`

- [ ] **Step 1: Написать падающие тесты**

Создать `web/src/settings.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import { DEFAULT_SETTINGS, loadSettings, saveSettings, type Settings } from "./settings";

function memoryStorage(seed?: string): Storage {
  const map = new Map<string, string>();
  if (seed !== undefined) {
    map.set("lanpad", seed);
  }
  return {
    getItem: (key: string) => map.get(key) ?? null,
    setItem: (key: string, value: string) => void map.set(key, value),
    removeItem: (key: string) => void map.delete(key),
    clear: () => map.clear(),
    key: () => null,
    length: 0,
  } as unknown as Storage;
}

describe("loadSettings", () => {
  it("takes the language from the phone on first run", () => {
    expect(loadSettings(memoryStorage(), ["ru-RU"]).language).toBe("ru");
    expect(loadSettings(memoryStorage(), ["de-DE"]).language).toBe("en");
  });

  it("prefers a stored choice over the phone language", () => {
    const stored = JSON.stringify({ ...DEFAULT_SETTINGS, language: "en" });
    expect(loadSettings(memoryStorage(stored), ["ru-RU"]).language).toBe("en");
  });

  it("survives corrupted storage", () => {
    expect(loadSettings(memoryStorage("{{{"), ["en"])).toEqual(
      { ...DEFAULT_SETTINGS, language: "en" },
    );
  });

  it("fills in fields a newer version added", () => {
    const partial = JSON.stringify({ sensitivity: 2 });
    const loaded = loadSettings(memoryStorage(partial), ["en"]);
    expect(loaded.sensitivity).toBe(2);
    expect(loaded.haptics).toBe(DEFAULT_SETTINGS.haptics);
  });

  it("refuses an out-of-range sensitivity", () => {
    const absurd = JSON.stringify({ sensitivity: 9999 });
    expect(loadSettings(memoryStorage(absurd), ["en"]).sensitivity)
      .toBe(DEFAULT_SETTINGS.sensitivity);
  });

  it("survives storage that throws", () => {
    const hostile = {
      getItem: () => {
        throw new Error("private mode");
      },
    } as unknown as Storage;
    expect(loadSettings(hostile, ["en"]).language).toBe("en");
  });
});

describe("saveSettings", () => {
  it("round-trips", () => {
    const storage = memoryStorage();
    const settings: Settings = { ...DEFAULT_SETTINGS, sensitivity: 1.8, language: "ru" };
    saveSettings(storage, settings);
    expect(loadSettings(storage, ["en"])).toEqual(settings);
  });

  it("does not throw when storage refuses to write", () => {
    const hostile = {
      getItem: () => null,
      setItem: () => {
        throw new Error("quota");
      },
    } as unknown as Storage;
    expect(() => saveSettings(hostile, DEFAULT_SETTINGS)).not.toThrow();
  });
});
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `cd web && bun run test src/settings.test.ts`
Expected: FAIL — модуля нет

- [ ] **Step 3: Написать `web/src/settings.ts`**

```ts
import { pickLanguage, type Language } from "./i18n";

export type Saturation = "calm" | "normal" | "rich";

export interface Settings {
  sensitivity: number;
  naturalScrolling: boolean;
  haptics: boolean;
  showMedia: boolean;
  saturation: Saturation;
  language: Language;
}

const KEY = "lanpad";
const MIN_SENSITIVITY = 0.5;
const MAX_SENSITIVITY = 2.4;

export const DEFAULT_SETTINGS: Settings = {
  sensitivity: 1.1,
  naturalScrolling: false,
  haptics: true,
  showMedia: true,
  saturation: "normal",
  language: "en",
};

function isSaturation(value: unknown): value is Saturation {
  return value === "calm" || value === "normal" || value === "rich";
}

/**
 * Read settings, falling back field by field.
 *
 * Storage can be absent, corrupted, or throw outright in private mode, and
 * a phone that cannot remember a preference should still work.
 */
export function loadSettings(storage: Storage, languages: readonly string[]): Settings {
  const fallback: Settings = { ...DEFAULT_SETTINGS, language: pickLanguage(languages) };
  let stored: unknown;
  try {
    const raw = storage.getItem(KEY);
    stored = raw === null ? null : JSON.parse(raw);
  } catch {
    return fallback;
  }
  if (typeof stored !== "object" || stored === null) {
    return fallback;
  }
  const partial = stored as Partial<Settings>;
  const sensitivity = typeof partial.sensitivity === "number"
    && partial.sensitivity >= MIN_SENSITIVITY
    && partial.sensitivity <= MAX_SENSITIVITY
    ? partial.sensitivity
    : fallback.sensitivity;
  return {
    sensitivity,
    naturalScrolling: typeof partial.naturalScrolling === "boolean"
      ? partial.naturalScrolling
      : fallback.naturalScrolling,
    haptics: typeof partial.haptics === "boolean" ? partial.haptics : fallback.haptics,
    showMedia: typeof partial.showMedia === "boolean" ? partial.showMedia : fallback.showMedia,
    saturation: isSaturation(partial.saturation) ? partial.saturation : fallback.saturation,
    language: partial.language === "ru" || partial.language === "en"
      ? partial.language
      : fallback.language,
  };
}

export function saveSettings(storage: Storage, settings: Settings): void {
  try {
    storage.setItem(KEY, JSON.stringify(settings));
  } catch {
    // A phone that cannot remember preferences still works with them.
  }
}
```

- [ ] **Step 4: Убедиться, что всё зелёное**

Run: `cd web && bun run test && bun run typecheck && bun run lint`

- [ ] **Step 5: Коммит**

```bash
git add web/src/settings.ts web/src/settings.test.ts
git commit -m "feat: settings that survive absent or hostile storage

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 8: Цвет из обложки

Доминирующий оттенок обложки, поднятый до читаемого на чёрном фоне.

**Files:**
- Create: `web/src/theme.ts`, `web/src/theme.test.ts`

**Interfaces:**
- Consumes: `settings.Saturation`
- Produces:
  - `dominantColor(pixels: Uint8ClampedArray): [number, number, number]`
  - `readableAccent(rgb): string`
  - `themeVariables(accent: string, saturation: Saturation): Record<string, string>`
  - `DEFAULT_ACCENT`

- [ ] **Step 1: Написать падающие тесты**

Создать `web/src/theme.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import { DEFAULT_ACCENT, dominantColor, readableAccent, themeVariables } from "./theme";

function pixels(...rgba: number[]): Uint8ClampedArray {
  return new Uint8ClampedArray(rgba);
}

describe("dominantColor", () => {
  it("averages the pixels it is given", () => {
    const [r, g, b] = dominantColor(pixels(200, 0, 0, 255, 0, 0, 0, 255));
    expect(r).toBeGreaterThan(g);
    expect(r).toBeGreaterThan(b);
  });

  it("ignores transparent pixels", () => {
    // A cover padded with transparency would otherwise read as black.
    const [r] = dominantColor(pixels(255, 0, 0, 255, 0, 0, 0, 0));
    expect(r).toBeGreaterThan(200);
  });

  it("returns black for an empty or fully transparent input", () => {
    expect(dominantColor(pixels())).toEqual([0, 0, 0]);
    expect(dominantColor(pixels(255, 255, 255, 0))).toEqual([0, 0, 0]);
  });
});

describe("readableAccent", () => {
  it("lifts a dark cover to something visible on black", () => {
    // A maroon fill on a black track is invisible; the fader would look
    // empty at every volume.
    const lifted = readableAccent([40, 0, 10]);
    expect(lifted).toMatch(/^hsl\(/);
    const lightness = Number(lifted.match(/([\d.]+)%\)$/)?.[1]);
    expect(lightness).toBeGreaterThanOrEqual(45);
  });

  it("lifts a washed-out cover to something with colour", () => {
    const lifted = readableAccent([130, 128, 129]);
    const saturation = Number(lifted.match(/,\s*([\d.]+)%/)?.[1]);
    expect(saturation).toBeGreaterThanOrEqual(35);
  });

  it("leaves an already vivid cover close to itself", () => {
    const vivid = readableAccent([196, 77, 255]);
    const lightness = Number(vivid.match(/([\d.]+)%\)$/)?.[1]);
    expect(lightness).toBeLessThan(80);
  });

  it("never returns a colour that would vanish", () => {
    for (const rgb of [[0, 0, 0], [255, 255, 255], [1, 1, 1]] as const) {
      const lightness = Number(readableAccent(rgb).match(/([\d.]+)%\)$/)?.[1]);
      expect(lightness).toBeGreaterThanOrEqual(45);
      expect(lightness).toBeLessThanOrEqual(75);
    }
  });
});

describe("themeVariables", () => {
  it("gives the calm mode no glow", () => {
    expect(themeVariables(DEFAULT_ACCENT, "calm")["--glow-opacity"]).toBe("0");
  });

  it("gives the normal mode a glow but plain panels", () => {
    const normal = themeVariables(DEFAULT_ACCENT, "normal");
    expect(Number(normal["--glow-opacity"])).toBeGreaterThan(0);
    expect(normal["--panel-tint"]).toBe("0");
  });

  it("tints panels only in the rich mode", () => {
    expect(Number(themeVariables(DEFAULT_ACCENT, "rich")["--panel-tint"])).toBeGreaterThan(0);
  });

  it("always carries the accent", () => {
    for (const mode of ["calm", "normal", "rich"] as const) {
      expect(themeVariables("hsl(280, 80%, 60%)", mode)["--accent"]).toBe("hsl(280, 80%, 60%)");
    }
  });
});
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `cd web && bun run test src/theme.test.ts`
Expected: FAIL — модуля нет

- [ ] **Step 3: Написать `web/src/theme.ts`**

```ts
import type { Saturation } from "./settings";

export const DEFAULT_ACCENT = "hsl(265, 70%, 62%)";

const MIN_LIGHTNESS = 45;
const MAX_LIGHTNESS = 75;
const MIN_SATURATION = 35;

/** Average the visible pixels of a downscaled cover. */
export function dominantColor(pixels: Uint8ClampedArray): [number, number, number] {
  let r = 0;
  let g = 0;
  let b = 0;
  let counted = 0;
  for (let i = 0; i + 3 < pixels.length; i += 4) {
    const alpha = pixels[i + 3];
    if (alpha === 0) {
      continue;
    }
    r += pixels[i];
    g += pixels[i + 1];
    b += pixels[i + 2];
    counted += 1;
  }
  if (counted === 0) {
    return [0, 0, 0];
  }
  return [Math.round(r / counted), Math.round(g / counted), Math.round(b / counted)];
}

function toHsl([r, g, b]: readonly [number, number, number]): [number, number, number] {
  const rn = r / 255;
  const gn = g / 255;
  const bn = b / 255;
  const max = Math.max(rn, gn, bn);
  const min = Math.min(rn, gn, bn);
  const lightness = (max + min) / 2;
  const delta = max - min;
  if (delta === 0) {
    return [0, 0, lightness * 100];
  }
  const saturation = delta / (1 - Math.abs(2 * lightness - 1));
  let hue: number;
  if (max === rn) {
    hue = ((gn - bn) / delta) % 6;
  } else if (max === gn) {
    hue = (bn - rn) / delta + 2;
  } else {
    hue = (rn - gn) / delta + 4;
  }
  return [((hue * 60) + 360) % 360, saturation * 100, lightness * 100];
}

/**
 * Push a cover's colour into a range that stays visible on black.
 *
 * A dark or washed-out cover would otherwise paint a fader that looks
 * empty at every value, which reads as broken rather than subtle.
 */
export function readableAccent(rgb: readonly [number, number, number]): string {
  const [hue, saturation, lightness] = toHsl(rgb);
  const s = Math.max(saturation, MIN_SATURATION);
  const l = Math.min(Math.max(lightness, MIN_LIGHTNESS), MAX_LIGHTNESS);
  return `hsl(${Math.round(hue)}, ${Math.round(s)}%, ${Math.round(l)}%)`;
}

/**
 * CSS variables for one saturation mode.
 *
 * The glow is a static layer and the panel tint is a flat fill: neither
 * repaints while a finger moves, which is what keeps the pad responsive.
 */
export function themeVariables(
  accent: string,
  saturation: Saturation,
): Record<string, string> {
  const glow = { calm: "0", normal: "0.5", rich: "0.34" }[saturation];
  const tint = { calm: "0", normal: "0", rich: "0.14" }[saturation];
  return {
    "--accent": accent,
    "--glow-opacity": glow,
    "--panel-tint": tint,
  };
}
```

- [ ] **Step 4: Убедиться, что всё зелёное**

Run: `cd web && bun run test && bun run typecheck && bun run lint`

- [ ] **Step 5: Коммит**

```bash
git add web/src/theme.ts web/src/theme.test.ts
git commit -m "feat: accent colour lifted from cover art to stay readable

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 9: Медиа-карточка

Обложка, трек, исполнитель, фейдер позиции, три кнопки. Позиция досчитывается между обновлениями.

**Files:**
- Create: `web/src/position.ts`, `web/src/components/MediaCard.tsx`
- Create: `web/src/position.test.ts`

**Interfaces:**
- Consumes: `protocol.MediaState`, `protocol.safeArtUrl`, `components/Fader`, `theme.dominantColor`, `theme.readableAccent`
- Produces:
  - `interpolatePosition(base, playing, elapsedMs, duration): number`
  - `formatTime(seconds: number): string`
  - Компонент `MediaCard`

- [ ] **Step 1: Написать падающие тесты**

Создать `web/src/position.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import { formatTime, interpolatePosition } from "./position";

describe("interpolatePosition", () => {
  it("advances while playing", () => {
    // The agent sends position rarely; the phone fills the gap itself
    // rather than asking every second.
    expect(interpolatePosition(100, true, 2000, 355)).toBeCloseTo(102, 3);
  });

  it("stands still while paused", () => {
    expect(interpolatePosition(100, false, 5000, 355)).toBe(100);
  });

  it("never runs past the end of the track", () => {
    expect(interpolatePosition(350, true, 60_000, 355)).toBe(355);
  });

  it("never goes negative", () => {
    expect(interpolatePosition(0, true, 0, 355)).toBe(0);
  });

  it("tolerates an unknown duration", () => {
    expect(interpolatePosition(10, true, 1000, 0)).toBeCloseTo(11, 3);
  });
});

describe("formatTime", () => {
  it("formats minutes and seconds", () => {
    expect(formatTime(134)).toBe("2:14");
    expect(formatTime(5)).toBe("0:05");
    expect(formatTime(0)).toBe("0:00");
  });

  it("formats past an hour", () => {
    expect(formatTime(3725)).toBe("1:02:05");
  });

  it("refuses to show nonsense", () => {
    expect(formatTime(-5)).toBe("0:00");
    expect(formatTime(Number.NaN)).toBe("0:00");
    expect(formatTime(Number.POSITIVE_INFINITY)).toBe("0:00");
  });
});
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `cd web && bun run test src/position.test.ts`
Expected: FAIL — модуля нет

- [ ] **Step 3: Написать `web/src/position.ts`**

```ts
/**
 * Track position between updates.
 *
 * The agent pushes position rarely on purpose — a packet a second for a
 * number the phone can compute itself would be pure latency.
 */
export function interpolatePosition(
  base: number,
  playing: boolean,
  elapsedMs: number,
  duration: number,
): number {
  const advanced = playing ? base + elapsedMs / 1000 : base;
  const capped = duration > 0 ? Math.min(advanced, duration) : advanced;
  return Math.max(capped, 0);
}

export function formatTime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) {
    return "0:00";
  }
  const whole = Math.floor(seconds);
  const s = whole % 60;
  const m = Math.floor(whole / 60) % 60;
  const h = Math.floor(whole / 3600);
  const pad = (value: number): string => String(value).padStart(2, "0");
  return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`;
}
```

- [ ] **Step 4: Написать `web/src/components/MediaCard.tsx`**

```tsx
import { useEffect, useRef, useState } from "react";

import type { Strings } from "../i18n";
import { formatTime, interpolatePosition } from "../position";
import { safeArtUrl, type Event, type MediaState } from "../protocol";
import { DEFAULT_ACCENT, dominantColor, readableAccent } from "../theme";
import { Fader } from "./Fader";

interface Props {
  media: MediaState;
  send: (event: Event) => void;
  strings: Strings;
  onAccent: (accent: string) => void;
}

const TICK_MS = 500;

export function MediaCard({ media, send, strings, onAccent }: Props) {
  const [now, setNow] = useState(() => performance.now());
  const receivedAt = useRef(performance.now());
  const art = safeArtUrl(media.art);

  useEffect(() => {
    receivedAt.current = performance.now();
    setNow(performance.now());
  }, [media.position, media.playing]);

  useEffect(() => {
    if (!media.playing) {
      return undefined;
    }
    const timer = window.setInterval(() => setNow(performance.now()), TICK_MS);
    return () => window.clearInterval(timer);
  }, [media.playing]);

  const position = interpolatePosition(
    media.position,
    media.playing,
    now - receivedAt.current,
    media.duration,
  );

  // Reading the cover's colour costs about a millisecond, once per track.
  const onCoverLoad = (event: React.SyntheticEvent<HTMLImageElement>): void => {
    const image = event.currentTarget;
    try {
      const canvas = document.createElement("canvas");
      canvas.width = 8;
      canvas.height = 8;
      const context = canvas.getContext("2d", { willReadFrequently: false });
      if (!context) {
        return;
      }
      context.drawImage(image, 0, 0, 8, 8);
      onAccent(readableAccent(dominantColor(context.getImageData(0, 0, 8, 8).data)));
    } catch {
      // A cover from another origin taints the canvas; the default accent
      // is a fine answer, a broken panel is not.
      onAccent(DEFAULT_ACCENT);
    }
  };

  return (
    <div className="media">
      <div className="media-row">
        {art ? (
          <img className="media-cover" src={art} alt="" crossOrigin="anonymous"
               onLoad={onCoverLoad} onError={() => onAccent(DEFAULT_ACCENT)} />
        ) : (
          <div className="media-cover media-cover-empty" />
        )}
        <div className="media-text">
          <div className="media-title">{media.title || strings.nothingPlaying}</div>
          <div className="media-artist">{media.artist}</div>
        </div>
      </div>

      <Fader
        value={position}
        min={0}
        max={media.duration > 0 ? media.duration : 1}
        disabled={!media.canSeek || media.duration <= 0}
        label={strings.play}
        onChange={(value) => send(["seek", Math.round(value)])}
      />
      <div className="media-times">
        <span>{formatTime(position)}</span>
        <span>{formatTime(media.duration)}</span>
      </div>

      <div className="media-buttons">
        <button type="button" aria-label={strings.previous}
                onClick={() => send(["media", "prev"])}>⏮</button>
        <button type="button" aria-label={strings.play}
                onClick={() => send(["media", "play"])}>{media.playing ? "⏸" : "▶"}</button>
        <button type="button" aria-label={strings.next}
                onClick={() => send(["media", "next"])}>⏭</button>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Убедиться, что всё зелёное**

Run: `cd web && bun run test && bun run typecheck && bun run lint`

- [ ] **Step 6: Коммит**

```bash
git add web/src/position.ts web/src/position.test.ts web/src/components/MediaCard.tsx
git commit -m "feat: media card with seekable position and cover-derived accent

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 10: Ряд кликов, громкость, быстрые клавиши

Три простых компонента, у каждого один смысл.

**Files:**
- Create: `web/src/components/ClickRow.tsx`, `web/src/components/VolumeRow.tsx`, `web/src/components/QuickKeys.tsx`, `web/src/components/HoldButton.tsx`

**Interfaces:**
- Consumes: `protocol.Event`, `protocol.AudioState`, `components/Fader`, `i18n.Strings`
- Produces: компоненты `HoldButton`, `ClickRow`, `VolumeRow`, `QuickKeys`

- [ ] **Step 1: Написать `web/src/components/HoldButton.tsx`**

```tsx
import { useEffect, useRef } from "react";

interface Props {
  onFire: () => void;
  repeat?: boolean;
  className?: string;
  label: string;
  children: React.ReactNode;
}

const REPEAT_MS = 110;

/** A button that keeps firing while held, for arrows and volume steps. */
export function HoldButton({ onFire, repeat, className, label, children }: Props) {
  const timer = useRef<number | null>(null);

  useEffect(() => () => {
    if (timer.current !== null) {
      window.clearInterval(timer.current);
    }
  }, []);

  const start = (event: React.PointerEvent<HTMLButtonElement>): void => {
    event.preventDefault();
    onFire();
    if (repeat) {
      timer.current = window.setInterval(onFire, REPEAT_MS);
    }
  };

  const stop = (): void => {
    if (timer.current !== null) {
      window.clearInterval(timer.current);
      timer.current = null;
    }
  };

  return (
    <button
      type="button"
      className={className}
      aria-label={label}
      onPointerDown={start}
      onPointerUp={stop}
      onPointerCancel={stop}
      onPointerLeave={stop}
    >
      {children}
    </button>
  );
}
```

- [ ] **Step 2: Написать `web/src/components/ClickRow.tsx`**

```tsx
import type { Strings } from "../i18n";
import type { Event } from "../protocol";
import { HoldButton } from "./HoldButton";

interface Props {
  send: (event: Event) => void;
  strings: Strings;
}

export function ClickRow({ send, strings }: Props) {
  return (
    <div className="clicks">
      <HoldButton className="wide" label={strings.click}
                  onFire={() => send(["click", "l"])}>{strings.click}</HoldButton>
      <HoldButton label={strings.rightClick}
                  onFire={() => send(["click", "r"])}>{strings.rightClick}</HoldButton>
      <HoldButton label={strings.middleClick}
                  onFire={() => send(["click", "m"])}>···</HoldButton>
    </div>
  );
}
```

- [ ] **Step 3: Написать `web/src/components/VolumeRow.tsx`**

```tsx
import type { Strings } from "../i18n";
import type { AudioState, Event } from "../protocol";
import { Fader } from "./Fader";
import { HoldButton } from "./HoldButton";

interface Props {
  audio: AudioState | null;
  send: (event: Event) => void;
  strings: Strings;
}

export function VolumeRow({ audio, send, strings }: Props) {
  const muted = audio?.muted ?? false;
  return (
    <div className={`vol${muted ? " muted" : ""}`}>
      <HoldButton label={strings.mute} onFire={() => send(["volmute"])}>
        {muted ? "🔇" : "🔊"}
      </HoldButton>
      <Fader
        value={audio?.volume ?? null}
        min={0}
        max={100}
        label={strings.volume}
        onChange={(value) => send(["volset", Math.round(value)])}
        format={(value) => `${Math.round(value)}`}
      />
    </div>
  );
}
```

- [ ] **Step 4: Написать `web/src/components/QuickKeys.tsx`**

```tsx
import type { Strings } from "../i18n";
import type { Event } from "../protocol";
import { HoldButton } from "./HoldButton";

interface Props {
  send: (event: Event) => void;
  strings: Strings;
  onKeyboard: () => void;
}

interface Key {
  label: string;
  tap?: string;
  combo?: string[];
  repeat?: boolean;
}

const KEYS: Key[] = [
  { label: "Esc", tap: "escape" },
  { label: "Tab", tap: "tab" },
  { label: "↵", tap: "enter" },
  { label: "⌫", tap: "backspace" },
  { label: "↑", tap: "up", repeat: true },
  { label: "↓", tap: "down", repeat: true },
  { label: "←", tap: "left", repeat: true },
  { label: "→", tap: "right", repeat: true },
  { label: "⌘", tap: "super" },
  { label: "Alt+Tab", combo: ["alt", "tab"] },
  { label: "Ctrl+C", combo: ["ctrl", "c"] },
  { label: "Ctrl+V", combo: ["ctrl", "v"] },
];

export function QuickKeys({ send, strings, onKeyboard }: Props) {
  return (
    <div className="keys">
      {KEYS.map((key) => (
        <HoldButton
          key={key.label}
          label={key.label}
          repeat={key.repeat}
          onFire={() => send(key.combo ? ["combo", key.combo] : ["tap", key.tap ?? ""])}
        >
          {key.label}
        </HoldButton>
      ))}
      <button type="button" className="kbkey" aria-label={strings.keyboard}
              onClick={onKeyboard}>⌨</button>
    </div>
  );
}
```

- [ ] **Step 5: Убедиться, что всё зелёное**

Run: `cd web && bun run test && bun run typecheck && bun run lint`

- [ ] **Step 6: Коммит**

```bash
git add web/src/components
git commit -m "feat: click row, volume row and quick keys

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 11: Клавиатура

Механика переносится из прототипа: скрытое поле ввода с перехватом `beforeinput`. Выглядит странно, но это единственный надёжный способ на iOS.

**Files:**
- Create: `web/src/components/KeyboardSheet.tsx`, `web/src/keymap.ts`
- Create: `web/src/keymap.test.ts`

**Interfaces:**
- Consumes: `protocol.Event`, `i18n.Strings`
- Produces:
  - `namedKeyFor(key: string): string | null`
  - `canTypeDirectly(text: string): boolean`
  - Компонент `KeyboardSheet`

- [ ] **Step 1: Написать падающие тесты**

Создать `web/src/keymap.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import { canTypeDirectly, namedKeyFor } from "./keymap";

describe("namedKeyFor", () => {
  it("maps the keys the agent knows", () => {
    expect(namedKeyFor("Escape")).toBe("escape");
    expect(namedKeyFor("ArrowUp")).toBe("up");
    expect(namedKeyFor("Backspace")).toBe("backspace");
  });

  it("returns null for ordinary characters", () => {
    expect(namedKeyFor("a")).toBeNull();
    expect(namedKeyFor("Ж")).toBeNull();
  });
});

describe("canTypeDirectly", () => {
  it("accepts what the agent's layout covers", () => {
    expect(canTypeDirectly("hello world!")).toBe(true);
  });

  it("refuses what has to go through the clipboard", () => {
    // Cyrillic and emoji cannot be typed key by key on a US layout.
    expect(canTypeDirectly("привет")).toBe(false);
    expect(canTypeDirectly("🎧")).toBe(false);
    expect(canTypeDirectly("mixed привет")).toBe(false);
  });

  it("refuses an empty string", () => {
    expect(canTypeDirectly("")).toBe(false);
  });
});
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `cd web && bun run test src/keymap.test.ts`
Expected: FAIL — модуля нет

- [ ] **Step 3: Написать `web/src/keymap.ts`**

```ts
/** Browser key names the agent understands, by its own naming. */
const NAMED: Record<string, string> = {
  Escape: "escape",
  Tab: "tab",
  Enter: "enter",
  Backspace: "backspace",
  Delete: "delete",
  Home: "home",
  End: "end",
  PageUp: "pageup",
  PageDown: "pagedown",
  ArrowUp: "up",
  ArrowDown: "down",
  ArrowLeft: "left",
  ArrowRight: "right",
};

export function namedKeyFor(key: string): string | null {
  return NAMED[key] ?? null;
}

/**
 * Can the agent type this key by key?
 *
 * Its layout covers printable ASCII. Anything else — Cyrillic, emoji —
 * travels through the clipboard instead.
 */
export function canTypeDirectly(text: string): boolean {
  return text.length > 0 && /^[\x20-\x7e]+$/.test(text);
}
```

- [ ] **Step 4: Написать `web/src/components/KeyboardSheet.tsx`**

```tsx
import { useEffect, useRef, useState } from "react";

import type { Strings } from "../i18n";
import { canTypeDirectly, namedKeyFor } from "../keymap";
import type { Event } from "../protocol";

interface Props {
  open: boolean;
  onClose: () => void;
  send: (event: Event) => void;
  strings: Strings;
}

type Modifier = "ctrl" | "alt" | "shift" | "super";

const MODIFIERS: Modifier[] = ["ctrl", "alt", "shift", "super"];
const MODIFIER_LABELS: Record<Modifier, string> = {
  ctrl: "Ctrl", alt: "Alt", shift: "Shift", super: "⌘",
};

/**
 * The keyboard sheet.
 *
 * Input is captured from a hidden field through `beforeinput` rather than
 * from key events: it is the only approach that reports characters
 * reliably on iOS, where key events for software keyboards are unusable.
 */
export function KeyboardSheet({ open, onClose, send, strings }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const sheetRef = useRef<HTMLDivElement>(null);
  const [held, setHeld] = useState<Modifier[]>([]);
  const heldRef = useRef<Modifier[]>(held);
  heldRef.current = held;
  const [pasteText, setPasteText] = useState("");

  useEffect(() => {
    const field = inputRef.current;
    if (!field) {
      return undefined;
    }

    const pad = (): void => {
      if (field.value.length < 2) {
        field.value = "  ";
      }
      field.setSelectionRange(field.value.length, field.value.length);
    };

    const onBeforeInput = (event: InputEvent): void => {
      const { inputType, data } = event;
      if (inputType === "insertText" && data) {
        const modifiers = heldRef.current;
        if (modifiers.length > 0 && data.length === 1) {
          send(["combo", [...modifiers, data]]);
          setHeld([]);
        } else if (canTypeDirectly(data)) {
          send(["type", data]);
        } else {
          send(["paste", data]);
        }
      } else if (inputType === "insertLineBreak" || inputType === "insertParagraph") {
        send(["tap", "enter"]);
      } else if (inputType === "deleteContentBackward") {
        send(["tap", "backspace"]);
      } else if (inputType === "deleteWordBackward") {
        send(["combo", ["ctrl", "backspace"]]);
      } else if (inputType === "insertFromPaste" && data) {
        send(["paste", data]);
      }
      event.preventDefault();
    };

    const onKeyDown = (event: KeyboardEvent): void => {
      const named = namedKeyFor(event.key);
      if (named) {
        send(["tap", named]);
        event.preventDefault();
        return;
      }
      if (event.key.length === 1 && (event.ctrlKey || event.metaKey || event.altKey)) {
        const modifiers: string[] = [];
        if (event.ctrlKey) modifiers.push("ctrl");
        if (event.altKey) modifiers.push("alt");
        if (event.metaKey) modifiers.push("super");
        if (event.shiftKey) modifiers.push("shift");
        send(["combo", [...modifiers, event.key.toLowerCase()]]);
        event.preventDefault();
      }
    };

    field.addEventListener("beforeinput", onBeforeInput as EventListener);
    field.addEventListener("keydown", onKeyDown);
    field.addEventListener("input", pad);
    return () => {
      field.removeEventListener("beforeinput", onBeforeInput as EventListener);
      field.removeEventListener("keydown", onKeyDown);
      field.removeEventListener("input", pad);
    };
  }, [send]);

  useEffect(() => {
    const sheet = sheetRef.current;
    const field = inputRef.current;
    if (!sheet || !field) {
      return undefined;
    }
    if (!open) {
      sheet.style.setProperty("--kb-h", "0px");
      setHeld([]);
      return undefined;
    }
    field.focus();
    const viewport = window.visualViewport;
    if (!viewport) {
      return undefined;
    }
    // Lift the sheet above the on-screen keyboard as it appears.
    const onResize = (): void => {
      const hidden = Math.max(0, window.innerHeight - viewport.height - viewport.offsetTop);
      sheet.style.setProperty("--kb-h", `${hidden}px`);
    };
    viewport.addEventListener("resize", onResize);
    viewport.addEventListener("scroll", onResize);
    onResize();
    return () => {
      viewport.removeEventListener("resize", onResize);
      viewport.removeEventListener("scroll", onResize);
    };
  }, [open]);

  const toggle = (modifier: Modifier): void => {
    setHeld((current) => current.includes(modifier)
      ? current.filter((item) => item !== modifier)
      : [...current, modifier]);
    inputRef.current?.focus();
  };

  return (
    <div className={`kb${open ? " open" : ""}`} ref={sheetRef}>
      <div className="kb-mods">
        {MODIFIERS.map((modifier) => (
          <button key={modifier} type="button"
                  className={`kb-mod${held.includes(modifier) ? " on" : ""}`}
                  onPointerDown={(event) => { event.preventDefault(); toggle(modifier); }}>
            {MODIFIER_LABELS[modifier]}
          </button>
        ))}
      </div>
      <div className="kb-hint">{strings.keyboardHint}</div>
      <input ref={inputRef} className="kb-input" autoCapitalize="none"
             autoComplete="off" autoCorrect="off" spellCheck={false}
             aria-label={strings.keyboard} />
      <textarea className="kb-paste" value={pasteText} placeholder={strings.pasteField}
                onChange={(event) => setPasteText(event.target.value)} />
      <div className="kb-send">
        <button type="button" className="primary"
                onClick={() => pasteText && send(["paste", pasteText])}>{strings.paste}</button>
        <button type="button"
                onClick={() => pasteText && send(["tpaste", pasteText])}>{strings.pasteTerminal}</button>
      </div>
      <button type="button" className="kb-done" onClick={onClose}>{strings.done}</button>
    </div>
  );
}
```

- [ ] **Step 5: Убедиться, что всё зелёное**

Run: `cd web && bun run test && bun run typecheck && bun run lint`

- [ ] **Step 6: Коммит**

```bash
git add web/src/keymap.ts web/src/keymap.test.ts web/src/components/KeyboardSheet.tsx
git commit -m "feat: keyboard sheet capturing input the way iOS allows

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 12: Онбординг, настройки, манифест с токеном

Экран без токена, панель настроек, и подключение манифеста — без него установка на домашний экран не пройдёт.

**Files:**
- Create: `web/src/components/Onboarding.tsx`, `web/src/components/Settings.tsx`, `web/src/components/StatusBar.tsx`, `web/src/manifest.ts`
- Create: `web/src/manifest.test.ts`

**Interfaces:**
- Consumes: `settings.Settings`, `i18n.Strings`, `token.readToken`
- Produces:
  - `manifestHref(token: string): string`
  - `attachManifest(document: Document, token: string): void`
  - Компоненты `Onboarding`, `SettingsPanel`, `StatusBar`

- [ ] **Step 1: Написать падающие тесты**

Создать `web/src/manifest.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import { manifestHref } from "./manifest";

describe("manifestHref", () => {
  it("carries the token", () => {
    // The agent answers 403 without it, and add-to-home-screen then fails.
    expect(manifestHref("abc123")).toBe("/manifest.webmanifest?t=abc123");
  });

  it("escapes the token", () => {
    expect(manifestHref("a+b")).toBe("/manifest.webmanifest?t=a%2Bb");
  });

  it("returns an empty string without a token", () => {
    expect(manifestHref("")).toBe("");
  });
});
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run: `cd web && bun run test src/manifest.test.ts`
Expected: FAIL — модуля нет

- [ ] **Step 3: Написать `web/src/manifest.ts`**

```ts
/**
 * The manifest link, with the token.
 *
 * The agent refuses the manifest without a token because it carries the
 * token itself in `start_url`; a link without one gets 403 and installing
 * to the home screen fails silently.
 */
export function manifestHref(token: string): string {
  return token ? `/manifest.webmanifest?t=${encodeURIComponent(token)}` : "";
}

/**
 * Attach the manifest at runtime.
 *
 * It cannot sit in the static HTML: the token is only known once the page
 * is open at the address the QR code encoded.
 */
export function attachManifest(document: Document, token: string): void {
  const href = manifestHref(token);
  if (!href) {
    return;
  }
  const link = document.createElement("link");
  link.rel = "manifest";
  link.href = href;
  document.head.appendChild(link);
}
```

- [ ] **Step 4: Написать `web/src/components/Onboarding.tsx`**

```tsx
import type { Strings } from "../i18n";

export function Onboarding({ strings }: { strings: Strings }) {
  return (
    <div className="onboarding">
      <h1>{strings.onboardingTitle}</h1>
      <p>{strings.onboardingBody}</p>
    </div>
  );
}
```

- [ ] **Step 5: Написать `web/src/components/StatusBar.tsx`**

```tsx
import type { Strings } from "../i18n";

interface Props {
  connected: boolean;
  strings: Strings;
  onSettings: () => void;
  settingsOpen: boolean;
}

export function StatusBar({ connected, strings, onSettings, settingsOpen }: Props) {
  return (
    <div className="statusbar">
      <span className={`dot${connected ? " ok" : ""}`} />
      <span aria-live="polite">{connected ? strings.connected : strings.connecting}</span>
      <span className="spacer" />
      <button type="button" className={`icon-btn${settingsOpen ? " on" : ""}`}
              aria-label={strings.settings} onClick={onSettings}>⚙</button>
    </div>
  );
}
```

- [ ] **Step 6: Написать `web/src/components/Settings.tsx`**

```tsx
import type { Language, Strings } from "../i18n";
import type { Saturation, Settings } from "../settings";

interface Props {
  settings: Settings;
  strings: Strings;
  onChange: (settings: Settings) => void;
}

const SATURATIONS: Saturation[] = ["calm", "normal", "rich"];
const LANGUAGES: Language[] = ["en", "ru"];

export function SettingsPanel({ settings, strings, onChange }: Props) {
  const set = <K extends keyof Settings>(key: K, value: Settings[K]): void => {
    onChange({ ...settings, [key]: value });
  };

  const saturationLabel: Record<Saturation, string> = {
    calm: strings.saturationCalm,
    normal: strings.saturationNormal,
    rich: strings.saturationRich,
  };

  return (
    <div className="settings">
      <label className="field">
        {strings.sensitivity}
        <input type="range" min={0.5} max={2.4} step={0.1} value={settings.sensitivity}
               onChange={(event) => set("sensitivity", Number(event.target.value))} />
      </label>

      <div className="field">
        {strings.naturalScrolling}
        <button type="button" role="switch" aria-checked={settings.naturalScrolling}
                aria-label={strings.naturalScrolling}
                className={`toggle${settings.naturalScrolling ? " on" : ""}`}
                onClick={() => set("naturalScrolling", !settings.naturalScrolling)} />
      </div>

      <div className="field">
        {strings.haptics}
        <button type="button" role="switch" aria-checked={settings.haptics}
                aria-label={strings.haptics}
                className={`toggle${settings.haptics ? " on" : ""}`}
                onClick={() => set("haptics", !settings.haptics)} />
      </div>

      <div className="field">
        {strings.showMedia}
        <button type="button" role="switch" aria-checked={settings.showMedia}
                aria-label={strings.showMedia}
                className={`toggle${settings.showMedia ? " on" : ""}`}
                onClick={() => set("showMedia", !settings.showMedia)} />
      </div>

      <div className="field">
        {strings.saturation}
        <div className="choice">
          {SATURATIONS.map((mode) => (
            <button key={mode} type="button"
                    className={settings.saturation === mode ? "on" : ""}
                    onClick={() => set("saturation", mode)}>{saturationLabel[mode]}</button>
          ))}
        </div>
      </div>

      <div className="field">
        {strings.language}
        <div className="choice">
          {LANGUAGES.map((language) => (
            <button key={language} type="button"
                    className={settings.language === language ? "on" : ""}
                    onClick={() => set("language", language)}>{language.toUpperCase()}</button>
          ))}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 7: Убедиться, что всё зелёное**

Run: `cd web && bun run test && bun run typecheck && bun run lint`

- [ ] **Step 8: Коммит**

```bash
git add web/src/manifest.ts web/src/manifest.test.ts web/src/components
git commit -m "feat: onboarding, settings panel and token-bearing manifest link

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 13: Сборка экрана и стили

Всё соединяется. Здесь же оформление и обязательство по задержке.

**Files:**
- Create: `web/src/App.tsx`, `web/src/styles/app.css`
- Modify: `web/src/main.tsx`

**Interfaces:**
- Consumes: всё предыдущее
- Produces: компонент `App`

- [ ] **Step 1: Написать `web/src/App.tsx`**

```tsx
import { useCallback, useEffect, useMemo, useState } from "react";

import { ClickRow } from "./components/ClickRow";
import { KeyboardSheet } from "./components/KeyboardSheet";
import { MediaCard } from "./components/MediaCard";
import { Onboarding } from "./components/Onboarding";
import { QuickKeys } from "./components/QuickKeys";
import { SettingsPanel } from "./components/Settings";
import { StatusBar } from "./components/StatusBar";
import { Trackpad } from "./components/Trackpad";
import { VolumeRow } from "./components/VolumeRow";
import { strings as dictionary } from "./i18n";
import { attachManifest } from "./manifest";
import { DEFAULT_SETTINGS, loadSettings, saveSettings, type Settings } from "./settings";
import { DEFAULT_ACCENT, themeVariables } from "./theme";
import { readToken } from "./token";
import { useTransport } from "./transport";

export function App() {
  const token = useMemo(() => readToken(location.search), []);
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [accent, setAccent] = useState(DEFAULT_ACCENT);
  const [keyboardOpen, setKeyboardOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const transport = useTransport(token);

  useEffect(() => {
    setSettings(loadSettings(window.localStorage, navigator.languages ?? []));
  }, []);

  useEffect(() => {
    attachManifest(document, token);
  }, [token]);

  const changeSettings = useCallback((next: Settings) => {
    setSettings(next);
    saveSettings(window.localStorage, next);
  }, []);

  const strings = dictionary(settings.language);
  const theme = themeVariables(accent, settings.saturation);
  const media = settings.showMedia ? transport.state?.media ?? null : null;

  if (!token) {
    return (
      <div className="shell" style={theme}>
        <Onboarding strings={strings} />
      </div>
    );
  }

  return (
    <div className="shell" style={theme}>
      <div className="glow" aria-hidden="true" />
      <StatusBar connected={transport.connected} strings={strings}
                 settingsOpen={settingsOpen}
                 onSettings={() => setSettingsOpen((open) => !open)} />

      {settingsOpen ? (
        <SettingsPanel settings={settings} strings={strings} onChange={changeSettings} />
      ) : null}

      {media ? (
        <MediaCard media={media} send={transport.send} strings={strings}
                   onAccent={setAccent} />
      ) : null}

      <Trackpad send={transport.send} settings={settings} hint={strings.trackpadHint} />
      <ClickRow send={transport.send} strings={strings} />
      <VolumeRow audio={transport.state?.audio ?? null} send={transport.send}
                 strings={strings} />
      <QuickKeys send={transport.send} strings={strings}
                 onKeyboard={() => setKeyboardOpen(true)} />

      <KeyboardSheet open={keyboardOpen} onClose={() => setKeyboardOpen(false)}
                     send={transport.send} strings={strings} />
    </div>
  );
}
```

- [ ] **Step 2: Обновить `web/src/main.tsx`**

```tsx
import { createRoot } from "react-dom/client";

import { App } from "./App";
import "./styles/app.css";

const root = document.getElementById("root");
if (root) {
  createRoot(root).render(<App />);
}

// Pinch and double-tap zoom would fight the trackpad for the same gestures.
document.addEventListener("gesturestart", (event) => event.preventDefault());
document.addEventListener("dblclick", (event) => event.preventDefault());
```

- [ ] **Step 3: Написать `web/src/styles/app.css`**

```css
/*
 * Black base, accent lifted from the cover art.
 *
 * `backdrop-filter` appears nowhere on purpose: it recomputes every frame,
 * and the pad has to stay ahead of a finger. The glow is a static layer on
 * its own compositor plane; panels are flat fills tinted by a variable.
 */
:root {
  color-scheme: dark;
  --bg: #000;
  --panel: #0c0c0d;
  --border: #1c1c1e;
  --text: #fff;
  --muted: #8e8e93;
  --accent: hsl(265, 70%, 62%);
  --glow-opacity: 0.5;
  --panel-tint: 0;
}

* { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }

body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font: 15px/1.4 -apple-system, "SF Pro Text", "Segoe UI", system-ui, sans-serif;
  overscroll-behavior: none;
  user-select: none;
}

.shell {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 11px;
  min-height: 100dvh;
  padding: env(safe-area-inset-top) 14px calc(env(safe-area-inset-bottom) + 14px);
}

/* Repainted only when the track changes, never while a finger moves. */
.glow {
  position: fixed;
  inset: -90px -50px auto -50px;
  height: 340px;
  background: radial-gradient(52% 60% at 50% 0%, var(--accent), transparent 72%);
  filter: blur(58px);
  opacity: var(--glow-opacity);
  pointer-events: none;
  will-change: transform;
  transform: translateZ(0);
  transition: opacity 400ms ease;
}

.statusbar, .media, .pad, .vol, .clicks button, .keys button, .settings {
  position: relative;
  background: color-mix(in srgb, var(--accent) calc(var(--panel-tint) * 100%), var(--panel));
  border: 0.5px solid var(--border);
}

.statusbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  border-radius: 16px;
  font-size: 13px;
}
.dot { width: 7px; height: 7px; border-radius: 50%; background: var(--muted); }
.dot.ok { background: #34c759; box-shadow: 0 0 8px #34c759; }
.spacer { flex: 1; }
.icon-btn { background: none; border: 0; color: var(--muted); font-size: 17px; }
.icon-btn.on { color: var(--accent); }

.media { border-radius: 22px; padding: 13px; display: flex; flex-direction: column; gap: 10px; }
.media-row { display: flex; gap: 12px; align-items: center; }
.media-cover { width: 56px; height: 56px; border-radius: 12px; object-fit: cover; }
.media-cover-empty { background: var(--border); }
.media-title { font-size: 14px; font-weight: 640; }
.media-artist { font-size: 12px; color: var(--muted); margin-top: 3px; }
.media-times { display: flex; justify-content: space-between; font-size: 10.5px; color: var(--muted); }
.media-buttons { display: flex; justify-content: center; gap: 30px; font-size: 19px; }
.media-buttons button { background: none; border: 0; color: var(--text); }

/* No blur here, ever. The fill reads as glass and costs nothing. */
.pad {
  flex: 1;
  min-height: 150px;
  border-radius: 24px;
  overflow: hidden;
  touch-action: none;
}
.pad-hint {
  position: absolute; inset: 0;
  display: grid; place-items: center;
  color: #48484a; font-size: 12px; pointer-events: none;
}
.pad-strip {
  position: absolute; top: 0; right: 0; bottom: 0;
  width: max(10%, 28px);
  border-left: 0.5px solid var(--border);
  background: linear-gradient(90deg, transparent, color-mix(in srgb, var(--accent) 8%, transparent));
  pointer-events: none;
}
.pad-glow {
  position: absolute; width: 90px; height: 90px; margin: -45px 0 0 -45px;
  border-radius: 50%; opacity: 0; pointer-events: none;
  background: radial-gradient(circle, color-mix(in srgb, var(--accent) 45%, transparent), transparent 70%);
  transition: opacity 160ms ease;
}

.clicks { display: flex; gap: 8px; background: none; border: 0; }
.clicks button { flex: 1; border-radius: 15px; padding: 12px 0; color: var(--text); font-size: 13px; }
.clicks button.wide { flex: 1.7; background: var(--accent); border-color: transparent; }

.vol { border-radius: 19px; padding: 11px 14px; display: flex; align-items: center; gap: 11px; }
.vol button { background: none; border: 0; font-size: 15px; }
.vol.muted { opacity: 0.6; }

.fader { flex: 1; display: flex; align-items: center; gap: 10px; height: 44px; touch-action: none; }
.fader.disabled { opacity: 0.4; pointer-events: none; }
.fader-track { position: relative; flex: 1; height: 5px; border-radius: 3px; background: #2c2c2e; }
.fader-fill { position: absolute; inset: 0 auto 0 0; border-radius: 3px; background: var(--accent); }
.fader-knob {
  position: absolute; top: 50%; width: 17px; height: 17px; border-radius: 50%;
  background: #fff; transform: translate(-50%, -50%); box-shadow: 0 2px 7px rgb(0 0 0 / 50%);
}
.fader-value { font-size: 11px; color: var(--muted); min-width: 2ch; text-align: right; }

.keys { display: grid; grid-template-columns: repeat(6, 1fr); gap: 6px; background: none; border: 0; }
.keys button { border-radius: 11px; padding: 9px 0; color: #c7c7cc; font-size: 11px; }

.settings { border-radius: 18px; padding: 12px 14px; display: flex; flex-direction: column; gap: 12px; }
.field { display: flex; align-items: center; justify-content: space-between; gap: 12px; font-size: 13px; }
.toggle { width: 44px; height: 26px; border-radius: 13px; background: #2c2c2e; border: 0; position: relative; }
.toggle.on { background: var(--accent); }
.toggle::after {
  content: ""; position: absolute; top: 3px; left: 3px;
  width: 20px; height: 20px; border-radius: 50%; background: #fff;
  transition: transform 160ms ease;
}
.toggle.on::after { transform: translateX(18px); }
.choice { display: flex; gap: 6px; }
.choice button {
  border-radius: 10px; padding: 6px 10px; font-size: 12px;
  background: var(--panel); border: 0.5px solid var(--border); color: var(--muted);
}
.choice button.on { background: var(--accent); color: var(--text); border-color: transparent; }

.onboarding { margin: auto; text-align: center; padding: 32px; max-width: 30ch; }
.onboarding h1 { font-size: 20px; }
.onboarding p { color: var(--muted); font-size: 14px; }

.kb {
  position: fixed; inset: auto 0 0 0; z-index: 10;
  transform: translateY(100%); transition: transform 240ms ease;
  background: var(--panel); border-top: 0.5px solid var(--border);
  border-radius: 20px 20px 0 0; padding: 14px;
  display: flex; flex-direction: column; gap: 10px;
  padding-bottom: calc(14px + var(--kb-h, 0px));
}
.kb.open { transform: translateY(0); }
.kb-mods { display: flex; gap: 8px; }
.kb-mod { flex: 1; border-radius: 11px; padding: 9px 0; background: #1c1c1e; border: 0; color: #c7c7cc; }
.kb-mod.on { background: var(--accent); color: var(--text); }
.kb-hint { font-size: 12px; color: var(--muted); }
.kb-input { position: absolute; opacity: 0; pointer-events: none; height: 1px; width: 1px; }
.kb-paste {
  min-height: 70px; border-radius: 12px; padding: 10px; font: inherit;
  background: #1c1c1e; border: 0; color: var(--text); resize: none;
}
.kb-send { display: flex; gap: 8px; }
.kb-send button { flex: 1; border-radius: 12px; padding: 11px 0; background: #1c1c1e; border: 0; color: var(--text); }
.kb-send button.primary { background: var(--accent); }
.kb-done { border-radius: 12px; padding: 11px 0; background: none; border: 0.5px solid var(--border); color: var(--muted); }

@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; }
}
```

- [ ] **Step 4: Собрать и проверить имена файлов**

Run: `cd web && bun run build && bun run test && bun run typecheck && bun run lint`
Expected: всё зелёное; тест на имена файлов подтверждает шестнадцатеричные хеши

- [ ] **Step 5: Коммит**

```bash
git add web/src src/lanpad/web
git commit -m "feat: assemble the screen and its styling

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 14: Замена прототипа и сквозная проверка

Старые файлы прототипа уходят, собранное приложение занимает их место.

**Files:**
- Delete: остатки прототипа в `src/lanpad/web/assets/`
- Modify: `pyproject.toml` при необходимости

- [ ] **Step 1: Убедиться, что от прототипа ничего не осталось**

```bash
ls src/lanpad/web src/lanpad/web/assets
grep -rn "NoteOverlay\|note-overlay\|/vol\|serviceWorker" src/lanpad/web/ && echo "НАЙДЕНО" || echo "чисто"
```

Файлов `htm.js`, `react.js`, `react-dom.js`, `app.js`, `app.css` и шрифтов прототипа быть не должно — их заменила сборка. Если остались, удалить и пересобрать.

- [ ] **Step 2: Обновить `THIRD-PARTY.md`**

Библиотеки теперь приходят через сборку, а не лежат файлами. Замени таблицы на актуальные: React и React DOM (MIT) входят в собранный пакет; шрифты прототипа удалены. Если сборка не тянет шрифты — убери раздел про шрифты целиком.

- [ ] **Step 3: Проверить, что агент отдаёт новое приложение**

```bash
.venv/bin/python -m lanpad --port 8601
```

В другом терминале:
```bash
TOKEN=$(cat ~/.local/share/lanpad/token)
curl -s -o /dev/null -w "%{http_code} index\n" "http://127.0.0.1:8601/"
curl -s -o /dev/null -w "%{http_code} manifest без токена\n" "http://127.0.0.1:8601/manifest.webmanifest"
curl -s -o /dev/null -w "%{http_code} manifest с токеном\n" "http://127.0.0.1:8601/manifest.webmanifest?t=$TOKEN"
curl -s -D- -o /dev/null "http://127.0.0.1:8601/assets/$(ls src/lanpad/web/assets | head -1)" | grep -i cache-control
```

Ожидание: `200`, `403`, `200`, и `Cache-Control: public, max-age=31536000, immutable` на файле сборки. Последнее — доказательство, что имена с хешем распознаются агентом.

Приложи вывод в отчёт дословно.

- [ ] **Step 4: Прогнать оба набора тестов**

```bash
.venv/bin/pytest -q
.venv/bin/ruff check .
cd web && bun run test && bun run typecheck && bun run lint
```

- [ ] **Step 5: Коммит**

```bash
git add -A
git commit -m "chore: replace the prototype app with the built one

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

## Проверка перед сдачей плана

- [ ] `bun run test`, `bun run typecheck`, `bun run lint` — зелёные
- [ ] `.venv/bin/pytest -q`, `.venv/bin/ruff check .` — зелёные
- [ ] `grep -rn "backdrop-filter" web/src` — пусто
- [ ] `grep -rn "sw.js\|serviceWorker\|/vol" web/src src/lanpad/web` — пусто
- [ ] Имена файлов в `src/lanpad/web/assets/` совпадают с образцом агента `-[0-9a-f]{6,}\.[ext]`
- [ ] Манифест без токена даёт 403, с токеном 200
- [ ] Русские подписи кнопок не длиннее английских более чем на треть и не переносятся

## Что проверяет пользователь на телефоне

Из песочницы этого не проверить:

- [ ] QR сканируется, приложение открывается
- [ ] «На главный экран» ставится и запускается без адресной строки
- [ ] Курсор двигается плавно, прокрутка двумя пальцами работает
- [ ] Полоса у правого края прокручивает одним пальцем и не даёт случайных кликов
- [ ] Громкость тянется пальцем и не дёргается назад
- [ ] При включённом плеере видна обложка, трек, перемотка работает
- [ ] Цвет интерфейса меняется вслед за обложкой
- [ ] Язык определился сам, переключатель работает
- [ ] Кириллица вставляется через поле в клавиатуре
