-- migrate:up
CREATE TABLE user (
    -- Primary key
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Required attributes
    email TEXT NOT NULL UNIQUE,
    user_id TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- State attributes
    user_state TEXT,	-- JSON dict of last_search, last_searches, last_sort and last_category.
    -- state_last_search TEXT,
    -- state_last_searches TEXT,                    -- JSON array of strings
    -- state_last_sort TEXT DEFAULT '{"by": "title", "order": "desc"}', -- JSON object
    -- state_last_category TEXT NOT NULL,          -- Category enum value

    -- Other attributes
    updated DATETIME,
    last_login DATETIME
);

-- Indexes for performance
CREATE UNIQUE INDEX idx_user_email ON user(email);
CREATE INDEX idx_user_user_id ON user(user_id);
CREATE INDEX idx_user_created ON user(created);
CREATE INDEX idx_user_last_login ON user(last_login);


-- migrate:down
DROP TABLE user;
