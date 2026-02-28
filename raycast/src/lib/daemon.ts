/** Client and lifecycle management for the mb-stash daemon. */

import net from "net";
import os from "os";
import path from "path";
import { spawn } from "child_process";

const TIMEOUT_MS = 10_000;
const POLL_INTERVAL_MS = 50;
const POLL_TIMEOUT_MS = 5000;

/** JSON response returned by the mb-stash daemon for every command. */
interface DaemonResponse {
  ok: boolean;
  data: Record<string, unknown>;
  error?: string;
  message?: string;
}

// --- Socket communication ---

/** Send a JSON command to the daemon and return the parsed response. */
function sendRequest(
  socketPath: string,
  command: string,
  params?: Record<string, string>,
): Promise<DaemonResponse> {
  return new Promise((resolve, reject) => {
    const client = new net.Socket();
    let data = "";

    client.setTimeout(TIMEOUT_MS);

    client.connect(socketPath, () => {
      const payload = JSON.stringify({ command, params: params ?? {} }) + "\n";
      client.write(payload);
    });

    client.on("data", (chunk) => {
      data += chunk.toString();
      if (data.includes("\n")) {
        client.destroy();
        resolve(JSON.parse(data.trim()) as DaemonResponse);
      }
    });

    client.on("timeout", () => {
      client.destroy();
      reject(new Error("Socket timeout"));
    });

    client.on("error", (err) => {
      client.destroy();
      reject(err);
    });
  });
}

/** Check daemon status (running, locked/unlocked). */
export function health(socketPath: string): Promise<DaemonResponse> {
  return sendRequest(socketPath, "health");
}

/** Unlock the stash with the master password. */
export function unlock(
  socketPath: string,
  password: string,
): Promise<DaemonResponse> {
  return sendRequest(socketPath, "unlock", { password });
}

/** Lock the stash, wiping decrypted secrets from daemon memory. */
export function lock(socketPath: string): Promise<DaemonResponse> {
  return sendRequest(socketPath, "lock");
}

/** List stored secret keys. */
export function listKeys(socketPath: string): Promise<DaemonResponse> {
  return sendRequest(socketPath, "list");
}

/** Retrieve the decrypted value of a secret by key. */
export function get(socketPath: string, key: string): Promise<DaemonResponse> {
  return sendRequest(socketPath, "get", { key });
}

/** Tell the daemon to clear the clipboard after the configured timeout. */
export function scheduleClipboardClear(
  socketPath: string,
  value: string,
): Promise<DaemonResponse> {
  return sendRequest(socketPath, "schedule_clipboard_clear", { value });
}

// --- Daemon lifecycle ---

/** Resolve the absolute path to the daemon's Unix socket from the data directory. */
export function resolveSocketPath(dataDir: string): string {
  const resolved = dataDir.replace(/^~/, os.homedir());
  return path.join(resolved, "daemon.sock");
}

/** Test whether the daemon socket accepts connections. */
function isConnectable(socketPath: string): Promise<boolean> {
  return new Promise((resolve) => {
    const client = new net.Socket();
    client.setTimeout(1000);

    client.connect(socketPath, () => {
      client.destroy();
      resolve(true);
    });

    client.on("error", () => {
      client.destroy();
      resolve(false);
    });

    client.on("timeout", () => {
      client.destroy();
      resolve(false);
    });
  });
}

/** Start the daemon if it is not already running, then wait until it is connectable. */
export async function ensureDaemon(prefs: Preferences): Promise<void> {
  const socketPath = resolveSocketPath(prefs.dataDir);

  console.log("[ensureDaemon] socketPath:", socketPath);
  console.log("[ensureDaemon] prefs.mbStashPath:", prefs.mbStashPath);
  console.log("[ensureDaemon] prefs.dataDir:", prefs.dataDir);

  if (await isConnectable(socketPath)) {
    console.log("[ensureDaemon] daemon already running, skipping start");
    return;
  }
  console.log("[ensureDaemon] daemon not running, starting...");

  // Build CLI args
  const args: string[] = [];
  const resolvedDataDir = prefs.dataDir.replace(/^~/, os.homedir());
  const defaultDir = path.join(os.homedir(), ".local", "mb-stash");
  if (resolvedDataDir !== defaultDir) {
    args.push("--data-dir", resolvedDataDir);
  }
  args.push("daemon");

  const resolvedBinary = prefs.mbStashPath.replace(/^~/, os.homedir());

  // Raycast inherits a minimal macOS launchd PATH — augment with common install locations
  const extraDirs = [
    path.join(os.homedir(), ".local", "bin"),
    "/usr/local/bin",
    "/opt/homebrew/bin",
  ];
  const augmentedPath = [...extraDirs, process.env.PATH].join(":");

  console.log("[ensureDaemon] resolvedBinary:", resolvedBinary);
  console.log("[ensureDaemon] args:", args);
  console.log("[ensureDaemon] augmentedPath:", augmentedPath);

  // Spawn detached daemon and wait for spawn result
  await new Promise<void>((resolve, reject) => {
    const child = spawn(resolvedBinary, args, {
      detached: true,
      stdio: "ignore",
      env: { ...process.env, PATH: augmentedPath },
    });

    child.on("error", (err) => {
      console.error("[ensureDaemon] spawn error:", err);
      reject(new Error(`mb-stash binary not found at "${resolvedBinary}"`));
    });

    // If the process spawned without error, detach and continue
    child.on("spawn", () => {
      console.log("[ensureDaemon] spawn succeeded, pid:", child.pid);
      child.unref();
      resolve();
    });
  });

  // Poll until socket is ready
  const deadline = Date.now() + POLL_TIMEOUT_MS;
  let pollCount = 0;
  while (Date.now() < deadline) {
    if (await isConnectable(socketPath)) {
      console.log("[ensureDaemon] daemon ready after", pollCount, "polls");
      return;
    }
    pollCount++;
    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
  }

  console.error("[ensureDaemon] poll timeout after", pollCount, "polls");
  throw new Error("Daemon failed to start within 5s");
}
