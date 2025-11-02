-- name: CreatePoll :one
INSERT INTO poll (question, created_by, expires_at)
VALUES ($1, $2, $3)
RETURNING id;

-- name: CreateVoteOption :exec
INSERT INTO vote_option (caption, poll_id, presentation_order)
VALUES ($1, $2, $3);

-- name: GetPoll :one
SELECT p.id, p.question, p.expires_at, u.username as creator_name,
    array_agg(vo.caption ORDER BY vo.presentation_order)::text[] AS options,
    array_agg(vo.id ORDER BY vo.presentation_order)::bigint[] AS option_ids,
    max(v.vote_option_id) as user_vote
FROM poll p
INNER JOIN vote_option vo ON p.id = vo.poll_id
INNER JOIN "user" u ON p.created_by = u.id
LEFT JOIN vote v ON v.vote_option_id = vo.id AND v.user_id = sqlc.narg(user_id)
WHERE p.id = sqlc.arg(poll_id)
GROUP BY p.id, u.id;

-- name: GetPolls :many
SELECT p.id, p.question, p.expires_at, u.username as creator_name,
    array_agg(vo.caption ORDER BY vo.presentation_order)::text[] AS options,
    array_agg(vo.id ORDER BY vo.presentation_order)::bigint[] AS option_ids
FROM poll p
INNER JOIN vote_option vo ON p.id = vo.poll_id
INNER JOIN "user" u ON p.created_by = u.id
GROUP BY p.id, u.id;

-- name: DeleteVoteOptionsForPoll :exec
DELETE FROM vote_option WHERE poll_id = $1;

-- name: DeletePoll :exec
DELETE FROM poll WHERE id = $1;
