-- migrate:up
CREATE TABLE poll (
    id BIGSERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT null,

    created_by BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),

    FOREIGN KEY (created_by) REFERENCES "user"(id)
);

CREATE TABLE vote_option (
    id BIGSERIAL PRIMARY KEY,
    poll_id BIGINT NOT NULL,
    caption TEXT NOT NULL,
    presentation_order INT NOT NULL,

    FOREIGN KEY (poll_id) REFERENCES poll(id)
);

CREATE TABLE vote (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    vote_option_id BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),

    FOREIGN KEY (user_id) REFERENCES "user"(id),
    FOREIGN KEY (vote_option_id) REFERENCES vote_option(id)
);

-- migrate:down
DROP TABLE IF EXISTS vote;
DROP TABLE IF EXISTS vote_option;
DROP TABLE IF EXISTS poll;
