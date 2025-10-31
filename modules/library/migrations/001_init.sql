CREATE TABLE IF NOT EXISTS library_items (
  id TEXT PRIMARY KEY,
  author TEXT,
  book_title TEXT,
  genre TEXT,
  language TEXT,
  status TEXT,
  created_at TEXT,
  updated_at TEXT,
  library_path TEXT,
  meta_json TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS library_items_fts
  USING fts5(author, book_title, genre, language, content='library_items', content_rowid='rowid');

CREATE TRIGGER IF NOT EXISTS library_items_ai AFTER INSERT ON library_items BEGIN
  INSERT INTO library_items_fts(rowid, author, book_title, genre, language)
  VALUES (new.rowid, new.author, new.book_title, new.genre, new.language);
END;

CREATE TRIGGER IF NOT EXISTS library_items_ad AFTER DELETE ON library_items BEGIN
  INSERT INTO library_items_fts(library_items_fts, rowid, author, book_title, genre, language)
  VALUES('delete', old.rowid, old.author, old.book_title, old.genre, old.language);
END;

CREATE TRIGGER IF NOT EXISTS library_items_au AFTER UPDATE ON library_items BEGIN
  INSERT INTO library_items_fts(library_items_fts, rowid, author, book_title, genre, language)
  VALUES('delete', old.rowid, old.author, old.book_title, old.genre, old.language);
  INSERT INTO library_items_fts(rowid, author, book_title, genre, language)
  VALUES (new.rowid, new.author, new.book_title, new.genre, new.language);
END;
