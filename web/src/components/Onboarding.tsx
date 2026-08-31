import type { Strings } from "../i18n";

export function Onboarding({ strings }: { strings: Strings }) {
  return (
    <div className="onboarding">
      <h1>{strings.onboardingTitle}</h1>
      <p>{strings.onboardingBody}</p>
    </div>
  );
}
