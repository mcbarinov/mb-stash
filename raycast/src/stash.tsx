/** Raycast command for searching and copying secrets. */

import {
  Action,
  ActionPanel,
  Clipboard,
  Form,
  Icon,
  List,
  Toast,
  getPreferenceValues,
  showToast,
} from "@raycast/api";
import { useCallback, useEffect, useState } from "react";
import * as daemon from "./lib/daemon";

/** Resolve the daemon socket path from Raycast preferences. */
function useSocketPath(): string {
  const prefs = getPreferenceValues<Preferences>();
  return daemon.resolveSocketPath(prefs.dataDir);
}

/** Master-password prompt shown when the stash is locked. */
function UnlockForm({ onUnlocked }: { onUnlocked: () => void }) {
  const socketPath = useSocketPath();
  const [isLoading, setIsLoading] = useState(false);

  async function handleSubmit(values: { password: string }) {
    setIsLoading(true);
    try {
      const resp = await daemon.unlock(socketPath, values.password);
      if (resp.ok) {
        await showToast({
          style: Toast.Style.Success,
          title: "Stash unlocked",
        });
        onUnlocked();
      } else {
        await showToast({
          style: Toast.Style.Failure,
          title: "Wrong password",
        });
      }
    } catch {
      await showToast({
        style: Toast.Style.Failure,
        title: "Failed to connect to daemon",
      });
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <Form
      isLoading={isLoading}
      actions={
        <ActionPanel>
          <Action.SubmitForm title="Unlock" onSubmit={handleSubmit} />
        </ActionPanel>
      }
    >
      <Form.PasswordField id="password" title="Master Password" />
    </Form>
  );
}

/** Searchable list of all secret keys with copy action. */
function SecretList() {
  const socketPath = useSocketPath();
  const [keys, setKeys] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchKeys = useCallback(async () => {
    setIsLoading(true);
    try {
      const resp = await daemon.listKeys(socketPath);
      if (resp.ok) {
        setKeys(resp.data.keys as string[]);
      } else {
        await showToast({
          style: Toast.Style.Failure,
          title: resp.message || "Failed to list keys",
        });
      }
    } catch {
      await showToast({
        style: Toast.Style.Failure,
        title: "Failed to connect to daemon",
      });
    } finally {
      setIsLoading(false);
    }
  }, [socketPath]);

  useEffect(() => {
    fetchKeys();
  }, [fetchKeys]);

  async function handleCopy(key: string) {
    try {
      const resp = await daemon.get(socketPath, key);
      if (resp.ok) {
        await Clipboard.copy(resp.data.value as string);
        await showToast({
          style: Toast.Style.Success,
          title: "Copied to clipboard",
        });
        daemon
          .scheduleClipboardClear(socketPath, resp.data.value as string)
          .catch(() => {});
      } else {
        await showToast({
          style: Toast.Style.Failure,
          title: resp.message || "Failed to get secret",
        });
      }
    } catch {
      await showToast({
        style: Toast.Style.Failure,
        title: "Failed to connect to daemon",
      });
    }
  }

  async function handleLock() {
    try {
      await daemon.lock(socketPath);
      await showToast({ style: Toast.Style.Success, title: "Stash locked" });
    } catch {
      // Already locked or daemon down
    }
  }

  return (
    <List isLoading={isLoading} searchBarPlaceholder="Search secrets...">
      {keys.map((key) => (
        <List.Item
          key={key}
          icon={Icon.Key}
          title={key}
          actions={
            <ActionPanel>
              <Action
                title="Copy to Clipboard"
                icon={Icon.Clipboard}
                onAction={() => handleCopy(key)}
              />
              <Action
                title="Lock Stash"
                icon={Icon.Lock}
                shortcut={{ modifiers: ["cmd"], key: "l" }}
                onAction={handleLock}
              />
            </ActionPanel>
          }
        />
      ))}
    </List>
  );
}

/** Entry point: starts the daemon, checks lock state, and renders the appropriate view. */
export default function Command() {
  const prefs = getPreferenceValues<Preferences>();
  const socketPath = daemon.resolveSocketPath(prefs.dataDir);
  const [state, setState] = useState<"loading" | "locked" | "unlocked">(
    "loading",
  );

  useEffect(() => {
    (async () => {
      try {
        await daemon.ensureDaemon(prefs);
        const resp = await daemon.health(socketPath);
        if (resp.ok && resp.data.unlocked) {
          setState("unlocked");
        } else {
          setState("locked");
        }
      } catch (err) {
        console.error("[Command] ensureDaemon failed:", err);
        await showToast({
          style: Toast.Style.Failure,
          title: "Could not start mb-stash daemon",
          message:
            err instanceof Error ? err.message : "Is mb-stash installed?",
        });
        setState("locked");
      }
    })();
  }, []);

  if (state === "loading") {
    return <List isLoading={true} searchBarPlaceholder="Starting daemon..." />;
  }

  if (state === "locked") {
    return <UnlockForm onUnlocked={() => setState("unlocked")} />;
  }

  return <SecretList />;
}
