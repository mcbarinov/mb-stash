# Architecture Decision Records

## ADR-001: Background daemon with Unix socket

### Problem

Without a daemon, every `mb-stash get` would need to: read `stash.json` from disk, prompt for password, derive the encryption key with scrypt (~0.5s), and decrypt. Doing this on every call is slow and unusable for frequent access.

### Decision

Run a background daemon that holds the derived key and decrypted secrets in memory. The user enters the password once, then all subsequent operations are instant until the stash is locked. CLI and daemon communicate over a Unix domain socket with a JSON-over-newline protocol — the standard approach used by ssh-agent and gpg-agent.

### Consequences

**CLI**: operations are instant after the first unlock — no repeated scrypt derivation, no password prompts.

**GUI clients (Raycast)**: the socket is not just convenient, it is required. GUI clients have no TTY, so they cannot use `getpass()` to prompt for a password interactively. The socket protocol lets them send the password programmatically. Without the daemon, a Raycast extension would have no way to unlock the stash.
