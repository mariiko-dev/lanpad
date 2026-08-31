# lanpad

**[English](README.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)**

Turn your phone into a touchpad, keyboard and media remote for your Linux
computer. Over your own Wi-Fi. No cloud, no account, no ads.

---

## Why this exists

I run Fedora on a 2015 MacBook with the lid shut, hooked up to a 27-inch
display. Great setup, one flaw: with the lid closed the keyboard and trackpad
are shut inside it. There is nothing to reach for.

I watch films that way with my girlfriend, and I wanted to skip a scene
without getting out of bed. My phone is an iPhone, and every app I tried for
this was either stuffed with ads, or broken, or wanted an account for the
privilege of moving a cursor across the room.

So this exists. It was built in a day, paired with Claude — most of the code
is model-written, and the design decisions and reviews are mine. Saying that
outright seems better than letting you guess from the commit history.

## What it does

- **Touchpad** — cursor, taps, two-finger scroll, drag, an edge strip for
  one-handed scrolling
- **Keyboard** — typing, modifiers, shortcuts, and a paste field for anything
  the layout cannot type directly
- **Media** — play, pause, next, previous, volume, and the current track with
  its cover art and a seek bar
- **Console on the computer** — a window in your launcher with the pairing QR
  code, connection status and service controls

## How it works

The agent runs on your computer and serves the app over your local network.
Your phone opens it in a browser and adds it to the home screen. Input is
injected through `/dev/uinput`; media comes from MPRIS, so it works with
Spotify, VLC, and video playing in a browser tab.

Nothing leaves your network. There is no server in the middle, because there
is nothing for one to do.

```
  computer ── agent ──┐
                      │  your Wi-Fi
  phone ── browser ───┘
```

## Install

Fedora and other Linux distributions with systemd.

`evdev` compiles a C extension, so the build tools have to be present. On a
fresh Fedora this is the first thing that will stop you:

```bash
sudo dnf install python3-devel gcc
pipx install lanpad
lanpad --install-service
```

Then open **lanpad** from your launcher, scan the QR code with your phone, and
add the page to your home screen.

If your network changes — a different Wi-Fi, a phone hotspot, a rebooted
router — the console window shows the new code by itself. No restart needed.

## Status

**Working:** the agent, the desktop console, pairing, cursor, keyboard,
volume, clipboard.

**In progress:** the phone app is being rewritten. The media panel, the
faders, the edge scroll strip and the two-language interface are designed and
specified, and the agent side already speaks the protocol they need. The app
that ships today is a prototype and does not use half of it yet.

No release is tagged, because tagging one now would advertise features the
app cannot deliver.

## Limitations

Worth knowing before you install:

- **Local network only.** By design. Remote access would mean a relay server
  and a dependency on someone else staying alive.
- **Linux only** for now. The platform layer is split so that Windows and
  macOS can be added without touching the protocol or the app.
- **The link is tied to your computer's address.** If DHCP hands it a new one,
  the icon on your home screen points nowhere. Reserve the address on your
  router, or open the console and scan the fresh code.
- **Anyone on your network who has the token controls your keyboard.** See
  below.

## Security, honestly

The threat model, stated plainly, because a tool that types into your machine
deserves that:

- The pairing token travels in the URL, so it lands in your phone's browser
  history. That is the price of pairing by QR code.
- **Anyone who is on your Wi-Fi and knows the token can type on your
  computer.** There is no second factor. On a home network that is the
  intended trade; on a café network, do not run this.
- The console — the window with the QR code and the service controls — is
  reachable only from the computer itself, never from the network.
- The token file lives in your data directory with `0600` permissions. That
  protects it from other users, not from other processes of your own.
- Any local program can claim to be a media player and hand the agent a cover
  image path. Only real image files under a size cap are ever served.

Found something? Open an issue.

## Development

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest && .venv/bin/ruff check .

cd web && npm install && npm test && npm run build
```

The front end builds into `src/lanpad/web`, which the agent serves. Asset
names carry a content hash, and the agent grants them permanent caching only
when the hash is hexadecimal — change the build config and upgrades stop
reaching paired phones.

## Licence

GPL-3.0-or-later. Take it, change it, run it — but if you ship it to other
people, ship the source too. This exists because the alternatives were closed
and full of ads, and that is not a trick worth repeating.

Third-party components are listed in [THIRD-PARTY.md](THIRD-PARTY.md).
