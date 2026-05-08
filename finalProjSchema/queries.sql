-- ============================================================
-- snickr — SQL Queries (Deliverable C)
-- Run against: psql -d snickr -f queries.sql
-- ============================================================


-- ------------------------------------------------------------
-- C1: Create a new user account
--     Placeholder values: email, username, nickname, password hash
-- ------------------------------------------------------------

INSERT INTO users (email, username, nickname, password_hash)
VALUES ('grace@nyu.edu', 'grace', 'GraceG', '$2b$12$hashed_grace');


-- ------------------------------------------------------------
-- C2: Create a new public channel inside a workspace
--     Includes authorization check that the user is a workspace member.
--     Placeholder values: channel name 'devops', workspace_id=1, user_id=2 (bob)
--
--     The INSERT ... SELECT with WHERE EXISTS is the auth check —
--     if the user is not a member the SELECT returns no rows and
--     nothing is inserted.  The CTE then auto-enrolls the creator.
-- ------------------------------------------------------------

WITH new_channel AS (
    INSERT INTO channel (name, workspace_id, channel_type, created_by)
    SELECT 'devops', 1, 'public', 2
    WHERE EXISTS (
        SELECT 1 FROM workspace_membership
        WHERE workspace_id = 1
          AND user_id = 2
    )
    RETURNING channel_id, created_by
)
INSERT INTO channel_membership (channel_id, user_id)
SELECT channel_id, created_by FROM new_channel;


-- ------------------------------------------------------------
-- C3: For each workspace, list all current administrators
-- ------------------------------------------------------------

SELECT
    w.name       AS workspace,
    u.username,
    u.email
FROM workspace w
JOIN workspace_membership wm ON w.workspace_id = wm.workspace_id
JOIN users u                  ON wm.user_id     = u.user_id
WHERE wm.role = 'admin'
ORDER BY w.name, u.username;


-- ------------------------------------------------------------
-- C4: For each public channel in a given workspace, list the
--     number of users invited more than 5 days ago who have
--     not yet joined.
--     Placeholder value: workspace_id = 1 (Engineering)
-- ------------------------------------------------------------

SELECT
    c.name                   AS channel,
    COUNT(ci.invitation_id)  AS pending_invites_over_5_days
FROM channel c
LEFT JOIN channel_invitation ci
       ON c.channel_id  = ci.channel_id
      AND ci.accepted   = FALSE
      AND ci.invited_at < NOW() - INTERVAL '5 days'
WHERE c.workspace_id  = 1
  AND c.channel_type  = 'public'
GROUP BY c.channel_id, c.name
ORDER BY c.name;


-- ------------------------------------------------------------
-- C5: For a particular channel, list all messages in
--     chronological order.
--     Placeholder value: channel_id = 1 (#general, Engineering)
-- ------------------------------------------------------------

SELECT
    m.message_id,
    u.username  AS author,
    m.body,
    m.posted_at
FROM message m
JOIN users u ON m.posted_by = u.user_id
WHERE m.channel_id = 1
ORDER BY m.posted_at ASC;


-- ------------------------------------------------------------
-- C6: For a particular user, list all messages they have posted
--     in any channel.
--     Placeholder value: user_id = 1 (alice)
-- ------------------------------------------------------------

SELECT
    w.name  AS workspace,
    c.name  AS channel,
    m.body,
    m.posted_at
FROM message m
JOIN channel   c ON m.channel_id  = c.channel_id
JOIN workspace w ON c.workspace_id = w.workspace_id
WHERE m.posted_by = 1
ORDER BY m.posted_at ASC;


-- ------------------------------------------------------------
-- C7: For a particular user, list all messages that:
--     (a) are accessible — user is a member of the workspace
--         AND a member of the specific channel
--     (b) contain the keyword 'perpendicular'
--     Placeholder value: user_id = 1 (alice)
-- ------------------------------------------------------------

SELECT
    w.name      AS workspace,
    c.name      AS channel,
    u.username  AS author,
    m.body,
    m.posted_at
FROM message m
JOIN channel   c ON m.channel_id   = c.channel_id
JOIN workspace w ON c.workspace_id = w.workspace_id
JOIN users     u ON m.posted_by    = u.user_id
WHERE m.body ILIKE '%perpendicular%'
  AND EXISTS (
      SELECT 1 FROM workspace_membership wm
      WHERE wm.workspace_id = c.workspace_id
        AND wm.user_id = 1
  )
  AND EXISTS (
      SELECT 1 FROM channel_membership cm
      WHERE cm.channel_id = m.channel_id
        AND cm.user_id = 1
  )
ORDER BY m.posted_at ASC;
