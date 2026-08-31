/** The pairing token travels in the URL the QR code encodes. */
export function readToken(search: string): string {
  return new URLSearchParams(search).get("t") ?? "";
}
