-- name: CanUserDoAt :one
SELECT can_user_do_at(
    sqlc.arg(user_id), sqlc.arg(poll_id),
    sqlc.arg(permission), COALESCE(sqlc.narg(timestamp), now()));

-- name: MakeModerator :exec
INSERT INTO poll_grants (role, scope, user_id, expires_at)
VALUES ('moderator', 'user_global', $1, $2);

-- name: RemoveModerator :exec
UPDATE poll_grants SET expires_at = now()
WHERE user_id = $1
    AND role = 'moderator'
    AND scope = 'user_global'
    AND now() <@ period;
