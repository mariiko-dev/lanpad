/**
 * How a batch of typed text reaches the computer.
 *
 * Always through the clipboard, never as key codes. A key code is turned
 * into a letter by whatever layout is active on the *computer*, so typing
 * "hello" on a machine set to Russian produces "руддщ". The phone cannot
 * know the remote layout, and the clipboard carries letters as letters.
 */
export function flushMethod(_buffer: string): "paste" {
  return "paste";
}
