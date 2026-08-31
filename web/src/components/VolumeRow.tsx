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
