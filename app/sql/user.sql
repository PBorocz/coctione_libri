-- name: insert_user<!
INSERT INTO user( email,  user_id,  password_hash,  user_state,  created)
VALUES          (:email, :user_id, :password_hash, :user_state, :created);

-- name: update_user!
UPDATE user
SET email	  = :email,
    user_id	  = :user_id,
    password_hash = :password_hash,
    user_state	  = :user_state,
    created	  = :created,
    updated	  = :updated
WHERE id = :id;

-- name: get_all_users()
-- Get all the users FROM the database
SELECT * FROM user ORDER BY id;

-- name: get_user_by_email^
-- Get a user FROM the database by email address
SELECT * FROM user WHERE email = :email;

-- name: get_user_by_id(id)^
-- Get the row id FROM the database by that id (used to confirm existence)
SELECT id FROM user WHERE id = :id;

-- name: get_user_by_user_id(user_id)^
-- Get a user FROM the database by user_id
SELECT * FROM user WHERE user_id = :user_id;

-- name: DELETE_user_by_id(id)!
-- DELETE the specified user
DELETE FROM user WHERE id = :id;

-- name: DELETE_all_users()!
-- DELETE all users
DELETE FROM user;
