CREATE TABLE IF NOT EXISTS "schema_migrations" (version varchar(128) primary key);
CREATE TABLE document (
    -- Primary key
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Required fields
    user_id INTEGER NOT NULL,
    title VARCHAR(120) NOT NULL,
    category TEXT NOT NULL,
    created DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Optional generic document fields
    file_content BLOB,                    -- GridFS equivalent stored as blob
    filename TEXT,
    filesize INTEGER DEFAULT 0,
    mimetype TEXT DEFAULT 'application/pdf',
    notes TEXT,
    source TEXT,
    tags TEXT,                           -- JSON array of tags as TEXT
    updated DATETIME,
    url TEXT,                            -- max_length constraint handled at app level

    -- Recipe category specific fields
    dates_cooked TEXT,                   -- JSON array of ISO datetime strings
    quality INTEGER CHECK (quality BETWEEN 0 AND 5),
    complexity INTEGER CHECK (complexity BETWEEN 0 AND 5),

    -- Foreign key constraint (assuming users table exists)
    FOREIGN KEY (user_id) REFERENCES users(id)
);
CREATE INDEX idx_document_tags ON document(tags);
CREATE INDEX idx_document_user_id ON document(user_id);
CREATE INDEX idx_document_category ON document(category);
CREATE INDEX idx_document_created ON document(created);
CREATE TABLE user (
    -- Primary key
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Required attributes
    email TEXT NOT NULL UNIQUE,
    user_id TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- State attributes
    state_last_search TEXT,
    state_last_searches TEXT,                    -- JSON array of strings
    state_last_sort TEXT DEFAULT '{"by": "title", "order": "desc"}', -- JSON object
    state_last_category TEXT NOT NULL,          -- Category enum value

    -- Other attributes
    updated DATETIME,
    last_login DATETIME
);
CREATE UNIQUE INDEX idx_user_email ON user(email);
CREATE INDEX idx_user_user_id ON user(user_id);
CREATE INDEX idx_user_created ON user(created);
CREATE INDEX idx_user_last_login ON user(last_login);
-- Dbmate schema migrations
INSERT INTO "schema_migrations" (version) VALUES
  ('20251013214923'),
  ('20251013215617');
