-- name: add_user<!
insert into user(email, user_id, created, password_hash, user_state)
values (:email, :user_id, :created, :password_hash, :user_state);

-- name: get_all_users()
-- Get all the users from the database
select * from user order by id;

-- name: get_user_by_email(email)^
-- Get a user from the database by email address
select * from user where email = :email;

-- name: get_user_by_id(id)^
-- Get the row id from the database by that id (used to confirm existence)
select id from user where id = :id;

-- name: get_user_by_user_id(user_id)^
-- Get a user from the database by user_id
select * from user where user_id = :user_id;
