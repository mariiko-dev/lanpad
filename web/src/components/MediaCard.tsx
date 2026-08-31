import { useEffect, useRef, useState } from "react";
import { LuPause, LuPlay, LuSkipBack, LuSkipForward } from "react-icons/lu";

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
                onClick={() => send(["media", "prev"])}><LuSkipBack /></button>
        <button type="button" className="play" aria-label={strings.play}
                onClick={() => send(["media", "play"])}>
          {media.playing ? <LuPause /> : <LuPlay />}
        </button>
        <button type="button" aria-label={strings.next}
                onClick={() => send(["media", "next"])}><LuSkipForward /></button>
      </div>
    </div>
  );
}
