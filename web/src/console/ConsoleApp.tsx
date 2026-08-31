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

  // The buster changes with the address, not with every poll: tying it to
  // the clock reloads the QR every two seconds and makes it flicker.
  const qrSource = `/console/qr.png?of=${encodeURIComponent(state.url)}`;

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
            {/* Re-fetched when the address changes: the address moves with
                the network, and a stale QR is what this window exists to
                prevent. */}
            <img className="qr" src={qrSource} alt="Pairing QR code" />
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
