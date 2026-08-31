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
    </div>
  );
}
