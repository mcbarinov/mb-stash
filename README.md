# mb-stash

Quick access to your non-critical secrets from the terminal.

mb-stash is **not** a password manager. Use a proper password manager (1Password, Bitwarden, KeePass) for critical secrets like passwords, bank credentials, and private keys.

mb-stash is for everything else — API tokens, service URLs, license keys, snippets you need 10 times a day but don't want to dig through a password manager every time.

## How it works

mb-stash stores secrets encrypted on disk. On first access it starts a background daemon and asks for your master password. While the daemon is running and unlocked, you have instant access to your secrets. When you lock mb-stash (or walk away from your computer), the decryption key is wiped from memory — secrets are safe until you enter your password again.

```
mb-stash get my-token    # daemon starts automatically, asks password if locked
                             # → copied to clipboard
```

One command. Token in your clipboard.

## Security model

### Encryption

All secrets are stored as a single encrypted blob on disk. The encryption pipeline:

1. **Master password → key (scrypt):** Your password is passed through [scrypt](https://en.wikipedia.org/wiki/Scrypt) — a memory-hard key derivation function. scrypt takes the password + a random 16-byte salt and produces a 32-byte AES key. This is deliberately slow (~0.5s) so that brute-force attacks are impractical. The salt is stored alongside the ciphertext — it's not a secret, its purpose is to ensure identical passwords produce different keys.

2. **Plaintext → ciphertext (AES-256-GCM):** The secrets (a JSON dict of key-value pairs) are encrypted with [AES-256-GCM](https://en.wikipedia.org/wiki/Galois/Counter_Mode) — an authenticated encryption algorithm. "Authenticated" means it provides both confidentiality (data is unreadable) and integrity (any tampering is detected). A random 12-byte nonce is generated on every write. Wrong password → wrong key → GCM tag verification fails → we know the password is wrong without needing a separate password hash.

All crypto is handled by [`cryptography`](https://github.com/pyca/cryptography) (PyCA) — Python's standard cryptography library backed by OpenSSL.

### Storage

Data directory: `~/.mb-stash/`

```
~/.mb-stash/
├── stash.json      # encrypted store
├── config.toml     # settings (timeouts, etc.)
├── daemon.sock     # Unix domain socket (while daemon is running)
└── daemon.pid      # daemon PID file (while daemon is running)
```

The encrypted store (`stash.json`):

```json
{
  "version": 1,
  "kdf": {
    "algorithm": "scrypt",
    "salt": "<base64>",
    "n": 1048576,
    "r": 8,
    "p": 1
  },
  "encryption": {
    "algorithm": "aes-256-gcm",
    "nonce": "<base64>",
    "ciphertext": "<base64>"
  }
}
```

Everything except `ciphertext` is public metadata (salt, nonce, KDF parameters). This is by design — these values are useless without the password. The `ciphertext`, when decrypted, contains a flat JSON dict:

```json
{
  "my-token": "xxxxxxxxxxxx",
  "work/api-key": "xxxxxxxxxxxx"
}
```

Every write (add, delete, change-password) generates a new random nonce and rewrites the file atomically (write to `.tmp`, then `os.replace` — no corruption even on crash).

### Daemon and locking

The background daemon holds the derived key and decrypted secrets in memory:

- **Unlock:** CLI prompts for password → sends it to daemon via Unix socket → daemon derives key with scrypt → decrypts ciphertext → stores key + secrets in memory
- **Lock:** daemon wipes key and secrets from memory (`None`). The only way to recover them is to enter the password again
- **Get/add/delete:** CLI sends command to daemon → daemon performs the operation using in-memory data → returns result. The derived key never leaves the daemon process

CLI ↔ daemon communication uses a Unix domain socket (`~/.mb-stash/daemon.sock`) with `0600` permissions (owner-only access). This is the same approach used by `ssh-agent` and `gpg-agent`.

### Auto-lock

mb-stash automatically locks when:
- Manually via `mb-stash lock`
- Configurable inactivity timeout
- System screen locks (macOS, Linux) — *planned*

Clipboard is automatically cleared after a configurable timeout (default: 30s). Repeated `get` resets the timer. `mb-stash lock` also clears the clipboard.

### What mb-stash does NOT protect against

- **Compromised machine:** if an attacker has access to your running system (malware, root access), they can read daemon memory or intercept socket communication. This is a fundamental limitation shared by ssh-agent, gpg-agent, and similar tools.
- **Memory forensics:** Python cannot guarantee secure memory wiping (garbage collector, no `mlock`). After locking, key material may linger in process memory briefly. Acceptable for non-critical secrets.
- **Other processes running as your user:** any process running under your UID can connect to the Unix socket. Same limitation as ssh-agent.

mb-stash is NOT a replacement for a password manager. It is NOT suitable for team/shared secret management.

## Commands

### Setup

| Command                    | Description                              |
| -------------------------- | ---------------------------------------- |
| `mb-stash init`            | First-time setup: create master password |
| `mb-stash change-password` | Change master password                   |

### Daemon

| Command            | Description                                    |
| ------------------ | ---------------------------------------------- |
| `mb-stash stop`    | Stop the daemon                                |
| `mb-stash lock`    | Lock the stash and clear clipboard             |
| `mb-stash unlock`  | Unlock with master password                    |
| `mb-stash health`  | Show daemon status (running, locked/unlocked)  |

### Secrets

| Command                        | Description                                         |
| ------------------------------ | --------------------------------------------------- |
| `mb-stash get <key>`, `g`      | Copy secret to clipboard (or `--stdout` for stdout) |
| `mb-stash list [filter]`, `l`  | List stored keys, optionally filter by substring    |
| `mb-stash add <key>`           | Add a new secret (value entered interactively)      |
| `mb-stash delete <key>`        | Delete a secret                                     |

## Usage examples

```bash
# First run
mb-stash init
# Create master password: ****
# Confirm: ****

# Add some secrets
mb-stash add my-token
# Enter value: ****

mb-stash add work/api-key
# Enter value: ****

# Daily usage — daemon starts and unlocks automatically on first access
mb-stash get my-token      # copied to clipboard ✓
mb-stash g work/api-key     # short alias works too

# Use in scripts
curl -H "Authorization: Bearer $(mb-stash get my-token --stdout)"

# See what's stored
mb-stash list
# my-token
# work/api-key

# Filter
mb-stash list work
# work/api-key

# Going away? Lock it (or just lock your screen — mb-stash locks with it)
mb-stash lock

# Back? Just get what you need — it will ask for password
mb-stash get my-token
# Enter master password: ****
# copied to clipboard ✓
```

## Auto-lock

mb-stash locks on inactivity timeout and manual `mb-stash lock`. Screen lock detection (macOS, Linux) is planned.

## Raycast extension

Search and copy secrets without touching the terminal. The extension communicates directly with the mb-stash daemon over Unix socket — no CLI spawning, instant responses.

### Installation

```bash
cd raycast
npm install
npm run dev    # opens in Raycast automatically
```

Requires [Raycast](https://raycast.com) and Node.js 22+.

### Commands

| Command | Description |
| --- | --- |
| **Search Secrets** | List all keys, filter by typing, copy to clipboard |
| **Lock Stash** | Lock the stash immediately (no UI, good for a keyboard shortcut) |

If the stash is locked, Search Secrets prompts for the master password before showing the list. The daemon starts automatically if not running.

### Keyboard shortcuts (in Search Secrets)

| Shortcut | Action |
| --- | --- |
| Enter | Copy secret to clipboard |
| Cmd+L | Lock stash |

### Configuration

In Raycast extension preferences:

| Setting | Default | Description |
| --- | --- | --- |
| Data Directory | `~/.local/mb-stash` | Path to mb-stash data directory |
| mb-stash CLI Path | `mb-stash` | Path to CLI binary (used only for daemon startup) |

## Tech stack

- Python 3.14
- Typer (CLI framework)
- cryptography (AES-256-GCM, scrypt — PyCA/OpenSSL)

## License

MIT