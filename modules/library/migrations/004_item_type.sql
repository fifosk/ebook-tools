ALTER TABLE library_items ADD COLUMN item_type TEXT DEFAULT 'book';

UPDATE library_items
SET item_type = 'book'
WHERE item_type IS NULL
   OR TRIM(item_type) = '';
