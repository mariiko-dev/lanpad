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
