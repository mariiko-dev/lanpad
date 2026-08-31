# lanpad

**[English](README.md) · [Deutsch](README.de.md) · [Русский](README.ru.md)**

Das Handy wird zum Touchpad, zur Tastatur und zur Medienfernbedienung für
deinen Linux-Rechner. Über dein eigenes WLAN. Ohne Cloud, ohne Konto, ohne
Werbung.

---

## Warum es das gibt

Auf meinem MacBook von 2015 läuft Fedora, der Deckel ist zu, das Bild geht auf
einen 27-Zoll-Monitor. Ein gutes Setup mit einem Haken: bei geschlossenem
Deckel sind Tastatur und Trackpad darin eingesperrt. Es gibt nichts, wonach man
greifen könnte.

So schauen meine Freundin und ich Filme, und ich wollte eine Szene
überspringen, ohne aus dem Bett zu steigen. Mein Handy ist ein iPhone, und
jede App, die ich dafür ausprobiert habe, war entweder voller Werbung oder
kaputt oder wollte ein Konto — dafür, einen Mauszeiger im Nebenzimmer zu
bewegen.

Daher dieses Projekt. Es entstand an einem Tag gemeinsam mit Claude: der Code
stammt größtenteils vom Modell, Entwurf und Prüfung der Befunde von mir. Das
offen zu sagen ist ehrlicher, als es dich aus der Commit-Historie erraten zu
lassen.

## Was es kann

- **Touchpad** — Zeiger, Tippen, Zwei-Finger-Scrollen, Ziehen sowie ein
  Streifen am Rand zum einhändigen Scrollen
- **Tastatur** — Eingabe, Modifikatoren, Tastenkürzel und ein Einfügefeld für
  alles, was das Layout nicht direkt tippen kann
- **Medien** — Wiedergabe, Pause, vor, zurück, Lautstärke sowie der laufende
  Titel mit Cover und Fortschrittsregler
- **Konsole am Rechner** — ein Fenster im Anwendungsmenü mit dem QR-Code zum
  Koppeln, dem Verbindungsstatus und der Dienststeuerung

## Wie es funktioniert

Der Agent läuft auf deinem Rechner und liefert die App im lokalen Netz aus.
Das Handy öffnet sie im Browser und legt sie auf den Startbildschirm. Eingaben
gehen über `/dev/uinput`, die Medieninformationen kommen von MPRIS — das
funktioniert mit Spotify, VLC und mit Videos in einem Browser-Tab.

Nichts verlässt dein Netz. Es gibt keinen Server dazwischen, weil es für ihn
nichts zu tun gäbe.

```
  Rechner ── Agent ────┐
                       │  dein WLAN
  Handy ── Browser ────┘
```

## Installation

Fedora und andere Linux-Distributionen mit systemd.

`evdev` übersetzt eine C-Erweiterung, deshalb müssen die Build-Werkzeuge da
sein. Auf einem frischen Fedora ist genau das die erste Hürde:

```bash
sudo dnf install python3-devel gcc
pipx install lanpad
lanpad --install-service
```

Danach **lanpad** aus dem Anwendungsmenü öffnen, den QR-Code mit dem Handy
scannen und die Seite auf den Startbildschirm legen.

Wenn sich das Netz ändert — anderes WLAN, Hotspot, neu gestarteter Router —
zeigt das Konsolenfenster den neuen Code von selbst. Ein Neustart ist nicht
nötig.

## Stand

**Funktioniert:** der Agent, die Konsole am Rechner, das Koppeln, Zeiger,
Tastatur, Lautstärke, Zwischenablage.

**In Arbeit:** die Handy-App wird neu geschrieben. Medienpanel, Regler, der
Scroll-Streifen am Rand und die zweisprachige Oberfläche sind entworfen und
spezifiziert, und die Agentenseite spricht das nötige Protokoll bereits. Die
heute ausgelieferte App ist ein Prototyp und nutzt die Hälfte davon noch nicht.

Es ist kein Release getaggt, denn das würde Funktionen versprechen, die die
App nicht liefern kann.

## Grenzen

Was du vor der Installation wissen solltest:

- **Nur im lokalen Netz.** Das ist eine Entscheidung, kein Mangel. Fernzugriff
  hieße ein Relais-Server und die Abhängigkeit davon, dass jemand ihn am Leben
  hält.
- **Vorerst nur Linux.** Die Plattformschicht ist so getrennt, dass Windows und
  macOS ergänzt werden können, ohne Protokoll oder App anzufassen.
- **Der Link hängt an der Adresse deines Rechners.** Vergibt DHCP eine neue,
  zeigt das Symbol auf dem Startbildschirm ins Leere. Reserviere die Adresse im
  Router oder öffne die Konsole und scanne den frischen Code.
- **Wer in deinem Netz ist und den Token kennt, steuert deine Tastatur.**
  Näheres unten.

## Sicherheit, ehrlich gesagt

Das Bedrohungsmodell im Klartext — ein Werkzeug, das auf deinem Rechner tippt,
hat das verdient:

- Der Kopplungs-Token steht in der Adresse und landet damit im Browserverlauf
  des Handys. Das ist der Preis fürs Koppeln per QR-Code.
- **Wer in deinem WLAN ist und den Token kennt, kann auf deinem Rechner
  tippen.** Einen zweiten Faktor gibt es nicht. Zu Hause ist das der bewusste
  Handel; im Café solltest du das nicht laufen lassen.
- Die Konsole — das Fenster mit QR-Code und Dienststeuerung — ist ausschließlich
  vom Rechner selbst erreichbar, nie aus dem Netz.
- Die Token-Datei liegt im Datenverzeichnis mit den Rechten `0600`. Das schützt
  sie vor anderen Benutzern, nicht vor anderen Prozessen deines eigenen Kontos.
- Jedes lokale Programm kann sich als Medienplayer ausgeben und dem Agenten
  einen Coverpfad unterschieben. Ausgeliefert werden nur echte Bilddateien und
  nur bis zu einer Größengrenze.

Etwas gefunden? Mach ein Issue auf.

## Entwicklung

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest && .venv/bin/ruff check .

cd web && npm install && npm test && npm run build
```

Das Frontend wird nach `src/lanpad/web` gebaut, von wo der Agent es ausliefert.
Die Dateinamen tragen einen Inhalts-Hash, und der Agent erlaubt dauerhaftes
Caching nur bei hexadezimalem Hash — ändert man die Build-Konfiguration,
erreichen Updates gekoppelte Handys nicht mehr.

## Lizenz

GPL-3.0-or-later. Nimm es, ändere es, betreibe es — aber wenn du es an andere
weitergibst, gib den Quelltext mit. Dieses Projekt entstand, weil die
Alternativen geschlossen und voller Werbung waren, und dieses Kunststück muss
man nicht wiederholen.

Fremdkomponenten sind in [THIRD-PARTY.md](THIRD-PARTY.md) aufgeführt.
