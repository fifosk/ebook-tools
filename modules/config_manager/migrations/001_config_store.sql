-- Configuration Management Database Schema
-- Version: 001
-- Description: Initial schema for configuration snapshots, auditing, and secrets management

-- Configuration snapshots table
-- Stores complete configuration snapshots for backup/restore functionality
CREATE TABLE IF NOT EXISTS config_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id TEXT NOT NULL UNIQUE,
    label TEXT,
    description TEXT,
    config_json TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    created_by TEXT,
    created_at TEXT NOT NULL,
    is_active INTEGER DEFAULT 0,
    source TEXT DEFAULT 'manual'  -- 'manual', 'import', 'auto_backup', 'migration', 'pre_restart'
);

CREATE INDEX IF NOT EXISTS idx_config_snapshots_active
    ON config_snapshots(is_active);
CREATE INDEX IF NOT EXISTS idx_config_snapshots_created
    ON config_snapshots(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_config_snapshots_source
    ON config_snapshots(source);

-- Configuration change audit log
-- Records all configuration changes for compliance and debugging
CREATE TABLE IF NOT EXISTS config_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    username TEXT,
    action TEXT NOT NULL,  -- 'create', 'update', 'restore', 'export', 'import', 'delete', 'reload', 'restart'
    snapshot_id TEXT,
    group_name TEXT,
    key_name TEXT,
    old_value TEXT,  -- NULL for sensitive values, stores placeholder instead
    new_value TEXT,  -- NULL for sensitive values, stores placeholder instead
    ip_address TEXT,
    user_agent TEXT,
    metadata_json TEXT,
    success INTEGER DEFAULT 1,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_config_audit_timestamp
    ON config_audit_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_config_audit_username
    ON config_audit_log(username);
CREATE INDEX IF NOT EXISTS idx_config_audit_action
    ON config_audit_log(action);
CREATE INDEX IF NOT EXISTS idx_config_audit_group
    ON config_audit_log(group_name);

-- Sensitive keys registry
-- Defines which configuration keys contain sensitive data
CREATE TABLE IF NOT EXISTS config_sensitive_keys (
    key_path TEXT PRIMARY KEY,
    mask_in_ui INTEGER DEFAULT 1,
    mask_in_export INTEGER DEFAULT 1,
    mask_in_audit INTEGER DEFAULT 1
);

-- Pre-populate known sensitive keys
INSERT OR IGNORE INTO config_sensitive_keys (key_path, mask_in_ui, mask_in_export, mask_in_audit) VALUES
    ('ollama_api_key', 1, 1, 1),
    ('database_url', 1, 1, 1),
    ('job_store_url', 1, 1, 1),
    ('api_keys.ollama', 1, 1, 1),
    ('api_keys.openai', 1, 1, 1),
    ('api_keys.anthropic', 1, 1, 1);

-- Encrypted sensitive values storage
-- Stores encrypted values for sensitive configuration keys
-- Values are encrypted using Fernet (AES-128-CBC with HMAC)
CREATE TABLE IF NOT EXISTS config_secrets (
    key_path TEXT PRIMARY KEY,
    encrypted_value BLOB NOT NULL,
    encryption_version INTEGER DEFAULT 1,  -- For key rotation support
    updated_at TEXT NOT NULL,
    updated_by TEXT
);

CREATE INDEX IF NOT EXISTS idx_config_secrets_updated
    ON config_secrets(updated_at DESC);

-- Configuration groups metadata
-- Stores per-group settings like collapsed state in UI
CREATE TABLE IF NOT EXISTS config_group_settings (
    group_name TEXT PRIMARY KEY,
    is_collapsed INTEGER DEFAULT 0,
    display_order INTEGER DEFAULT 0,
    custom_icon TEXT,
    metadata_json TEXT
);

-- Pre-populate group display order
INSERT OR IGNORE INTO config_group_settings (group_name, display_order) VALUES
    ('backend', 1),
    ('audio', 2),
    ('video', 3),
    ('images', 4),
    ('translation', 5),
    ('highlighting', 6),
    ('storage', 7),
    ('processing', 8),
    ('api_keys', 9);

-- Configuration validation rules
-- Custom validation rules beyond Pydantic model validation
CREATE TABLE IF NOT EXISTS config_validation_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key_path TEXT NOT NULL,
    rule_type TEXT NOT NULL,  -- 'regex', 'range', 'enum', 'path_exists', 'url_reachable'
    rule_value TEXT NOT NULL,
    error_message TEXT,
    is_warning INTEGER DEFAULT 0,  -- Warning vs error
    is_active INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_config_validation_key
    ON config_validation_rules(key_path);

-- System restart tracking
-- Records restart requests and outcomes
CREATE TABLE IF NOT EXISTS config_restart_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requested_at TEXT NOT NULL,
    requested_by TEXT,
    reason TEXT,
    delay_seconds INTEGER,
    pre_restart_snapshot_id TEXT,
    completed_at TEXT,
    success INTEGER,
    error_message TEXT,
    FOREIGN KEY (pre_restart_snapshot_id) REFERENCES config_snapshots(snapshot_id)
);

CREATE INDEX IF NOT EXISTS idx_restart_log_requested
    ON config_restart_log(requested_at DESC);
