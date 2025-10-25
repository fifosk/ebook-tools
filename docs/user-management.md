# User management guide

This document explains how authentication works inside **ebook-tools**, the
recommended roles, and how to tailor the storage backends for different
deployments.

## Components

The user system is intentionally small and ships with three main building
blocks:

- [`LocalUserStore`](../modules/user_management/local_user_store.py) persists
  credentials in a JSON file using bcrypt hashing. The default location is
  `config/users/users.json`.
- [`SessionManager`](../modules/user_management/session_manager.py) issues
  random session tokens and stores them in `~/.ebooktools_session.json`.
- [`AuthService`](../modules/user_management/auth_service.py) wraps the store
  and session manager to provide `login`, `logout`, decorator-based permission
  checks, and utility helpers for role lookups.

The CLI integrates these pieces through
[`modules/cli/user_commands.py`](../modules/cli/user_commands.py), which powers
commands such as `ebook-tools user add` and `ebook-tools user login`.

## Roles and permissions

Roles are arbitrary string labels stored on each
[`UserRecord`](../modules/user_management/user_store_base.py). They are only
interpreted by whatever checks your application applies, so you are free to
introduce custom semantics. A common pattern is:

| Role    | Intended capabilities |
|---------|----------------------|
| `admin` | Create, list, update, and delete users; run the pipeline; manage infrastructure secrets. |
| `editor`| Run the pipeline and upload assets but not manage other users. |
| `viewer`| Inspect generated artefacts without modifying configuration. |

Use `AuthService.require_role("admin")` or
`AuthService.require_role("editor", "admin")` to gate APIs or CLI handlers. A
helper such as `ensure_active_session` (used before running the pipeline) can
also be extended to enforce required roles.

## Bootstrapping credentials

The repository ships with `config/users/users.sample.json`, which contains
placeholder accounts for an administrator and an editor. The hashes are derived
with the same bcrypt-compatible helper used by the runtime, but **must be
replaced before deployment**. To get started:

1. Copy the template: `cp config/users/users.sample.json config/users/users.json`.
2. Rotate the administrator password with the CLI. For example,
   `ebook-tools user password admin --password 'new-secret'` prompts or accepts
   the replacement and updates the hash in place.
3. Repeat the command for the remaining seed accounts or delete them once real
   users have been created via `ebook-tools user add`.

The `ebook-tools user list` command prints the available users and their role
assignments, making it easy to verify that required capabilities (`admin`,
`editor`, or `viewer`) are present.

## Session flow

1. Create an account with `ebook-tools user add <username>`. If the `--password`
   flag is omitted you will be prompted interactively. Repeat the `--role`
   option to assign multiple roles.
2. Authenticate with `ebook-tools user login <username>`. Successful logins
   generate a token via `SessionManager.create_session` and save it to the active
   session file (`~/.ebooktools_active_session`). The token is also printed to
   stdout so it can be injected into automation.
3. Subsequent CLI invocations call `ensure_active_session`, which loads the
   active token and verifies it through `AuthService.authenticate`. You can
   bypass the lookup by exporting `EBOOKTOOLS_SESSION_TOKEN=<token>` in the
   environment.
4. Run `ebook-tools user logout` to revoke the token and clear the active session
   file. Logging out from another terminal simply deletes the stored token; if
   the token is missing, the command exits with a warning.

All session and token stores are simple JSON or text files, making them easy to
inspect or back up.

## Configuration reference

The repository includes `config/config.local.json` and
`modules/conf/config.local.json` as editable templates:

```json
{
  "authentication": {
    "user_store": {
      "backend": "local",
      "storage_path": "config/users/users.json"
    },
    "sessions": {
      "session_file": "~/.ebooktools_session.json",
      "active_session_file": "~/.ebooktools_active_session"
    }
  }
}
```

- **`backend`** – Identifier for the user store implementation. The built-in
  option is `local`, which maps to `LocalUserStore`.
- **`storage_path`** – Location of the credential file. Use an absolute path for
  shared deployments.
- **`session_file`** – Where `SessionManager` keeps active tokens.
- **`active_session_file`** – Path to the convenience file used by the CLI to
  remember the last successful login.

At runtime these settings can be overridden via environment variables:

| Variable | Purpose | Default |
|----------|---------|---------|
| `EBOOKTOOLS_USER_STORE` | Overrides the user store location. | `config/users/users.json` |
| `EBOOKTOOLS_SESSION_FILE` | Overrides the session JSON file. | `~/.ebooktools_session.json` |
| `EBOOKTOOLS_ACTIVE_SESSION_FILE` | Overrides the active session token file. | `~/.ebooktools_active_session` |
| `EBOOKTOOLS_SESSION_TOKEN` | Supplies an explicit session token for automation. | *(none)* |

The CLI flags `--store`, `--session-file`, and `--active-session-file` accept the
same paths.

## Migration and setup notes

1. **Initial bootstrap** – Deployments upgrading from a version without user
   management should create the credentials file (`config/users/users.json`) and
   add at least one administrator via `ebook-tools user add`. Existing scripts
   should export `EBOOKTOOLS_SESSION_TOKEN` with the generated token or run the
   login command once per environment to populate the active session file.
2. **Back up credentials** – Because both credentials and sessions are stored on
   disk, include `config/users/users.json` and `~/.ebooktools_session.json` in
   your backup policy. Rotate the bcrypt hashes periodically by deleting and
   recreating user accounts or by scripting against the `LocalUserStore`
   helpers.
3. **Extending backends** – To add an alternative persistence layer, subclass
   [`UserStoreBase`](../modules/user_management/user_store_base.py) and implement
   the CRUD methods. Update the configuration loader in your environment so that
   `authentication.user_store.backend` resolves to the new class and wire it into
   `modules/cli/user_commands.py`. The configuration schema already anticipates
   additional backends, so you can add backend-specific keys inside the same
   block.

With these steps in place you can enforce role-based access to the CLI and leave
room for more advanced authentication providers in the future.
