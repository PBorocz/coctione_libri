-- migrate:up
-- -----------------------------------------------------------------------------
-- Core user table
-- -----------------------------------------------------------------------------
CREATE TABLE user (
    -- Primary key
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    user_id TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated DATETIME,
    last_login DATETIME,
    s_payload TEXT -- JSON dict of all user non-key information (user_state etc.)
);

CREATE UNIQUE INDEX idx_user_email ON user(email);


-- -----------------------------------------------------------------------------
-- Document meta-information table
-- -----------------------------------------------------------------------------
CREATE TABLE document (
    -- Primary key
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Required fields
    user_id INTEGER NOT NULL,
    title VARCHAR(120) NOT NULL,
    category TEXT NOT NULL,
    created DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Optional generic document fields
    fileid   TEXT,                       -- Wasabi file object identifier
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

-- Index on tags (for searching within JSON)
CREATE INDEX idx_document_tags ON document(tags);

-- Additional useful indexes
CREATE INDEX idx_document_user_id ON document(user_id);
CREATE INDEX idx_document_category ON document(category);
CREATE INDEX idx_document_created ON document(created);


-- migrate:down
DROP TABLE document;
DROP TABLE user;
