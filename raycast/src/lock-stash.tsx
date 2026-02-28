/** Raycast command that locks the stash immediately (no-view, suitable for a hotkey). */

import { getPreferenceValues, showHUD } from "@raycast/api";
import { lock, resolveSocketPath } from "./lib/daemon";

/** Lock the stash and show a HUD confirmation. */
export default async function Command() {
  const prefs = getPreferenceValues<Preferences>();
  const socketPath = resolveSocketPath(prefs.dataDir);
  try {
    await lock(socketPath);
  } catch {
    // Daemon not running or already locked — that's fine
  }
  await showHUD("Stash locked");
}
