-- name: add_user<!
insert into user(email, user_id, password_hash, state_last_category) values (:email, :user_id, :password_hash, :state_last_category);

-- name: get_all_users()
-- Get all the users from the database
select id, email, created
  from user
 order by id;

-- name: get_user_by_email(email)^
-- Get a user from the database using a named parameter
select id, email, user_id
  from user
  where email = :email;

-- name: get_user_by_id(id)^
-- Get a user from the database using a named parameter
select id, email, user_id
  from user
  where id = :id;
