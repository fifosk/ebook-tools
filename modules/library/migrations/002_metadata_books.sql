ALTER TABLE library_items ADD COLUMN cover_path TEXT;

CREATE TABLE IF NOT EXISTS books (
  id TEXT PRIMARY KEY,
  title TEXT,
  author TEXT,
  genre TEXT,
  language TEXT,
  cover_path TEXT,
  created_at TEXT,
  updated_at TEXT
);

INSERT OR IGNORE INTO books (
  id, title, author, genre, language, cover_path, created_at, updated_at
)
SELECT
  id,
  book_title AS title,
  author,
  genre,
  language,
  cover_path,
  created_at,
  updated_at
FROM library_items;
