-- migrate:up
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE TYPE role AS ENUM ('creator', 'voter', 'viewer', 'moderator');
CREATE TYPE permission AS ENUM (
    'poll:assign_role',
    'poll:delete',
    'poll:vote',
    'poll:view'
);
CREATE TYPE scope AS ENUM (
    'user_poll',   -- specific user, specific poll
    'user_global', -- specific user, all polls
    'public_poll'  -- all users, specific poll
);

CREATE TABLE role_permissions (
    role role NOT NULL,
    permission permission NOT NULL,
    PRIMARY KEY (role, permission)
);

CREATE TABLE poll_grants (
    id BIGSERIAL PRIMARY KEY,
    role role NOT NULL,
    scope scope NOT NULL,

    -- NULLs mean "any user" or "any poll". Consistency with scope checked below.
    user_id BIGINT NULL REFERENCES "user"(id),
    poll_id BIGINT NULL REFERENCES poll(id),

    granted_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    expires_at TIMESTAMP WITH TIME ZONE NULL,
    period TSTZRANGE GENERATED ALWAYS AS
        (tstzrange(granted_at, coalesce(expires_at, 'infinity'::timestamptz))) STORED,

    CHECK (expires_at IS NULL OR expires_at > granted_at),
    CHECK (
        (scope = 'user_poll'   AND user_id IS NOT NULL AND poll_id IS NOT NULL) OR
        (scope = 'user_global' AND user_id IS NOT NULL AND poll_id IS NULL) OR
        (scope = 'public_poll' AND user_id IS NULL AND poll_id IS NOT NULL)
    ),

    -- no two equivalent roles that are temporally overlapping
    EXCLUDE USING gist (
        role WITH =,
        scope WITH =,
        user_id WITH =,
        poll_id WITH =,
        period WITH &&
    )
);

-- Default permissions per role
INSERT INTO role_permissions (role, permission) VALUES
    ('creator', 'poll:assign_role'),
    ('creator', 'poll:delete'),
    ('creator', 'poll:vote'),
    ('creator', 'poll:view'),

    ('voter', 'poll:vote'),
    ('voter', 'poll:view'),

    ('viewer', 'poll:view'),

    ('moderator', 'poll:view'),
    ('moderator', 'poll:delete');

CREATE OR REPLACE FUNCTION can_user_do_at(
    p_user_id BIGINT,
    p_poll_id BIGINT,
    p_permission permission,
    p_ts TIMESTAMPTZ DEFAULT now()
)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1
        FROM poll_grants pg
        JOIN role_permissions rp ON rp.role = pg.role
        WHERE rp.permission = p_permission
        AND (p_ts <@ pg.period)  -- timestamp falls inside grant period
        AND (
               (pg.scope = 'user_poll'   AND pg.user_id = p_user_id AND pg.poll_id = p_poll_id)
            OR (pg.scope = 'user_global' AND pg.user_id = p_user_id)
            OR (pg.scope = 'public_poll' AND pg.poll_id = p_poll_id)
        )
    );
END;
$$ LANGUAGE plpgsql STABLE;

-- migrate:down
DROP FUNCTION IF EXISTS can_user_do_at;
DROP TABLE IF EXISTS poll_grants;
DROP TABLE IF EXISTS role_permissions;
DROP TYPE IF EXISTS scope;
DROP TYPE IF EXISTS permission;
DROP TYPE IF EXISTS role;
DROP EXTENSION IF EXISTS btree_gist;
