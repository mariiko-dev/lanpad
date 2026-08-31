# Third-party components

lanpad is distributed under GPL-3.0-or-later. It ships files owned by other
authors and covered by their own terms.

## Bundled into the built front end

The web app and the desktop console are built from `web/` and the result is
shipped inside the Python package. The build embeds:

| Component | Licence |
|---|---|
| React and React DOM | MIT, Meta Platforms Inc. |

The full dependency tree used to produce the bundle is recorded in
`web/package.json` and the lockfile beside it.

## Python dependencies

Installed from PyPI, not vendored:

| Component | Licence |
|---|---|
| python-evdev | Revised BSD |
| dbus-next | MIT |
| qrcode | BSD |
| pypng | MIT |

Licence texts are available from the respective projects: MIT —
opensource.org/license/mit, BSD — opensource.org/license/bsd-3-clause.
