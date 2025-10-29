-- name: GetUser :one
SELECT * FROM "user"
WHERE id = $1 LIMIT 1;

-- name: GetUserByUsernameOrEmail :one
SELECT * FROM "user"
WHERE username = $1 OR email = $1 LIMIT 1;

-- name: CreateUser :one
INSERT INTO "user" (
    username, email, password_hash
) VALUES (
    $1, $2, $3
)
RETURNING *;