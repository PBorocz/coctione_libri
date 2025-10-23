-- ----------------------------------------------------------------------
-- migrate:up
-- ----------------------------------------------------------------------
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

-- ----------------------------------------------------------------------
-- migrate:down
-- ----------------------------------------------------------------------
DROP TABLE user;
