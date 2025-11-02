-- name: DeleteUserVoteOnPoll :one
DELETE FROM vote
WHERE vote_option_id IN (
    SELECT id FROM vote_option WHERE poll_id = $1
) AND user_id = $2
RETURNING vote_option_id;

-- name: SubmitVote :exec
INSERT INTO vote (user_id, vote_option_id)
VALUES ($1, $2);

-- name: GetVoteCounts :many
SELECT vo.id as vote_option_id, count(v.id) AS vote_count
FROM poll p
INNER JOIN vote_option vo ON p.id = vo.poll_id
LEFT JOIN vote v ON v.vote_option_id = vo.id  -- Keep options with 0 votes
WHERE p.id = $1
GROUP BY vo.id
ORDER BY vo.presentation_order;
