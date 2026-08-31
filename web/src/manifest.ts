/**
 * The manifest link, with the token.
 *
 * The agent refuses the manifest without a token because it carries the
 * token itself in `start_url`; a link without one gets 403 and installing
 * to the home screen fails silently.
 */
export function manifestHref(token: string): string {
  return token ? `/manifest.webmanifest?t=${encodeURIComponent(token)}` : "";
}

/**
 * Attach the manifest at runtime.
 *
 * It cannot sit in the static HTML: the token is only known once the page
 * is open at the address the QR code encoded.
 */
export function attachManifest(document: Document, token: string): void {
  const href = manifestHref(token);
  if (!href) {
    return;
  }
  const link = document.createElement("link");
  link.rel = "manifest";
  link.href = href;
  document.head.appendChild(link);
}
