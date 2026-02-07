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
| `admin` | Full access: manage users, jobs, and library items. |
| `editor`| Create and manage owned jobs or library items; view items shared with them. |
| `viewer`| View or export public/shared library items only; no edits. |

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

## REST API and dashboard integration

The FastAPI layer mirrors the CLI helpers so that the web dashboard and external
automation can authenticate without shell access:

- `POST /api/auth/login`, `GET /api/auth/session`, `POST /api/auth/logout`, and
  `POST /api/auth/password` are implemented in
  [`modules/webapi/auth_routes.py`](../modules/webapi/auth_routes.py). They
  produce the same session tokens managed by `SessionManager`, decorate responses
  with profile metadata (`email`, `first_name`, `last_name`, `last_login`), and
  enforce bearer authentication for session lookups or password changes.
- Administrative CRUD operations live under
  [`modules/webapi/admin_routes.py`](../modules/webapi/admin_routes.py) and are
  exposed as `/api/admin/*` routes. The
  routes surface normalised account status flags, allow administrators to create
  users with profile metadata, suspend or reactivate accounts, and reset
  passwords—all guarded by the `admin` role.

The React SPA consumes the same endpoints via the shared API client:

- `AuthProvider` restores persisted tokens from `localStorage`, forwards them
  with every request, reacts to `401/403` responses by clearing the session, and
  exposes `login`, `logout`, and `updatePassword` helpers to the component tree.
- `UserManagementPanel` grants administrators a self-service interface to list
  accounts, edit profile metadata, suspend/activate users, and trigger password
  resets. It normalises state returned by the admin routes so the UI can display
  consistent status badges and timestamps.

## Media and metadata responsibilities

- **Audio regeneration.** Users with the `admin` or `media_producer` roles can
  call `/api/media/generate` to re-run narration or other media for an existing
  job. The route is implemented in
  `modules/webapi/media_routes.py` and ultimately reuses
  `modules/render/audio_pipeline.py` plus the configured TTS backend, so keep
  those roles restricted to operators who understand the implications of
  voice/tempo changes.
- **Metadata verification.** When an operator triggers a regeneration the job
  manager rewrites `metadata/job.json`, `generated_files.chunks[]`, and all affected
  `metadata/chunk_XXXX.json` files. Admins should spot-check those artefacts (or
  run `MetadataLoader.for_job(job_id)` from `modules/metadata_manager.py`) before
  promoting the assets so stale highlighting data does not leak to readers.
- **Highlight policy enforcement.** Only administrators should toggle
  `EBOOK_HIGHLIGHT_POLICY`, `char_weighted_highlighting_default`, or forced
  alignment settings because they alter how `highlighting_summary` is generated
  and what the UI exposes. Document policy changes alongside credential updates
  so support teams know why audio or highlighting behaviour shifted.

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
