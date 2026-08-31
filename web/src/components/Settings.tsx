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
