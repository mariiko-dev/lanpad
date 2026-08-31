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
