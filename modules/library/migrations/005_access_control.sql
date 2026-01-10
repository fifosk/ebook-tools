ALTER TABLE library_items ADD COLUMN owner_id TEXT;
ALTER TABLE library_items ADD COLUMN visibility TEXT DEFAULT 'public';

UPDATE library_items
SET visibility = 'public'
WHERE visibility IS NULL
   OR TRIM(visibility) = '';

CREATE TABLE IF NOT EXISTS library_item_grants (
  entry_id TEXT NOT NULL,
  subject_type TEXT NOT NULL,
  subject_id TEXT NOT NULL,
  permission TEXT NOT NULL,
  granted_by TEXT,
  granted_at TEXT,
  PRIMARY KEY (entry_id, subject_type, subject_id, permission),
  FOREIGN KEY(entry_id) REFERENCES library_items(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_library_item_grants_entry
  ON library_item_grants(entry_id);

CREATE INDEX IF NOT EXISTS idx_library_item_grants_subject
  ON library_item_grants(subject_type, subject_id);
