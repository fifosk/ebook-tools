ALTER TABLE library_items ADD COLUMN isbn TEXT;
ALTER TABLE library_items ADD COLUMN source_path TEXT;

ALTER TABLE books ADD COLUMN isbn TEXT;
ALTER TABLE books ADD COLUMN source_path TEXT;

UPDATE books
SET isbn = (
    SELECT json_extract(meta_json, '$.book_metadata.isbn')
    FROM library_items
    WHERE library_items.id = books.id
)
WHERE isbn IS NULL;

UPDATE books
SET source_path = (
    SELECT source_path
    FROM library_items
    WHERE library_items.id = books.id
)
WHERE source_path IS NULL;
