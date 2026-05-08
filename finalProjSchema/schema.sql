-- ============================================================
-- snickr — schema + sample data
-- Usage:
--   createdb snickr          (first time only)
--   psql -d snickr -f schema.sql
-- ============================================================


-- ============================================================
-- TEARDOWN  (reverse dependency order so FKs don't block drops)
-- ============================================================

DROP TABLE IF EXISTS message             CASCADE;
DROP TABLE IF EXISTS channel_invitation  CASCADE;
DROP TABLE IF EXISTS channel_membership  CASCADE;
DROP TABLE IF EXISTS channel             CASCADE;
DROP TABLE IF EXISTS workspace_invitation CASCADE;
DROP TABLE IF EXISTS workspace_membership CASCADE;
DROP TABLE IF EXISTS workspace           CASCADE;
DROP TABLE IF EXISTS users               CASCADE;

DROP TYPE IF EXISTS member_role   CASCADE;
DROP TYPE IF EXISTS channel_kind  CASCADE;


-- ============================================================
-- CUSTOM TYPES
-- ============================================================

CREATE TYPE member_role  AS ENUM ('admin', 'member');
CREATE TYPE channel_kind AS ENUM ('public', 'private', 'direct');


-- ============================================================
-- TABLES
-- ============================================================

CREATE TABLE users (
    user_id       SERIAL       PRIMARY KEY,
    email         VARCHAR(255) NOT NULL UNIQUE,
    username      VARCHAR(100) NOT NULL UNIQUE,
    nickname      VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at    TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE TABLE workspace (
    workspace_id SERIAL       PRIMARY KEY,
    name         VARCHAR(100) NOT NULL,
    description  TEXT,
    created_by   INT          NOT NULL REFERENCES users(user_id),
    created_at   TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE TABLE workspace_membership (
    workspace_id INT         NOT NULL REFERENCES workspace(workspace_id),
    user_id      INT         NOT NULL REFERENCES users(user_id),
    role         member_role NOT NULL DEFAULT 'member',
    joined_at    TIMESTAMP   NOT NULL DEFAULT NOW(),
    PRIMARY KEY (workspace_id, user_id)
);

CREATE TABLE workspace_invitation (
    invitation_id   SERIAL       PRIMARY KEY,
    workspace_id    INT          NOT NULL REFERENCES workspace(workspace_id),
    invited_by      INT          NOT NULL REFERENCES users(user_id),
    invitee_user_id INT          REFERENCES users(user_id),   -- NULL if invitee has no account yet
    invitee_email   VARCHAR(255) NOT NULL,
    invited_at      TIMESTAMP    NOT NULL DEFAULT NOW(),
    accepted        BOOLEAN      NOT NULL DEFAULT FALSE,
    accepted_at     TIMESTAMP                               -- NULL until accepted
);

CREATE TABLE channel (
    channel_id   SERIAL       PRIMARY KEY,
    name         VARCHAR(100) NOT NULL,
    workspace_id INT          NOT NULL REFERENCES workspace(workspace_id),
    channel_type channel_kind NOT NULL,
    created_by   INT          NOT NULL REFERENCES users(user_id),
    created_at   TIMESTAMP    NOT NULL DEFAULT NOW(),
    UNIQUE (name, workspace_id)
);

CREATE TABLE channel_membership (
    channel_id INT       NOT NULL REFERENCES channel(channel_id),
    user_id    INT       NOT NULL REFERENCES users(user_id),
    joined_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (channel_id, user_id)
);

CREATE TABLE channel_invitation (
    invitation_id   SERIAL    PRIMARY KEY,
    channel_id      INT       NOT NULL REFERENCES channel(channel_id),
    invited_by      INT       NOT NULL REFERENCES users(user_id),
    invitee_user_id INT       NOT NULL REFERENCES users(user_id),
    invited_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    accepted        BOOLEAN   NOT NULL DEFAULT FALSE,
    accepted_at     TIMESTAMP                           -- NULL until accepted
);

CREATE TABLE message (
    message_id SERIAL    PRIMARY KEY,
    body       TEXT      NOT NULL,
    channel_id INT       NOT NULL REFERENCES channel(channel_id),
    posted_by  INT       NOT NULL REFERENCES users(user_id),
    posted_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE message_reaction (
    id         SERIAL       PRIMARY KEY,
    message_id INT          NOT NULL REFERENCES message(message_id) ON DELETE CASCADE,
    user_id    INT          NOT NULL REFERENCES users(user_id),
    emoji      VARCHAR(10)  NOT NULL,
    created_at TIMESTAMP    NOT NULL DEFAULT NOW(),
    UNIQUE (message_id, user_id, emoji)
);


-- ============================================================
-- SAMPLE DATA
-- ============================================================

-- ------------------------------------------------------------
-- Users
--   1 alice  — Engineering admin
--   2 bob    — Marketing admin, Engineering member
--   3 carol  — member of both workspaces
--   4 dave   — Engineering member
--   5 eve    — Marketing member (pending Engineering invite)
--   6 frank  — Engineering member (pending channel invites)
-- ------------------------------------------------------------

INSERT INTO users (user_id, email, username, nickname, password_hash, created_at, updated_at) VALUES
(1, 'alice@nyu.edu', 'alice', 'AliceA', 'pbkdf2_sha256$600000$saltforalice1$tOxxngHKr889H6aWvS+ewIobxZRs2LWFYN1n5Omt+No=', '2026-02-01 09:00:00', '2026-02-01 09:00:00'),
(2, 'bob@nyu.edu',   'bob',   'BobB',   'pbkdf2_sha256$600000$saltforbob123$tKnyPx5NxkX+0/aZQIUm4r/yFTn8uToaUxhdlvDtYUY=', '2026-02-03 10:00:00', '2026-02-03 10:00:00'),
(3, 'carol@nyu.edu', 'carol', 'CarolC', 'pbkdf2_sha256$600000$saltforcarol1$3zInhe1eIJA4wdmJ32o3zm1rQ/R+TFDzZXW826Z/CqY=', '2026-02-10 11:00:00', '2026-02-10 11:00:00'),
(4, 'dave@nyu.edu',  'dave',  'DaveD',  'pbkdf2_sha256$600000$saltfordave11$qDeUDrtsa4yiQrknqypknYrZhUMPL4EmMGDxl+tbI9k=', '2026-02-15 12:00:00', '2026-02-15 12:00:00'),
(5, 'eve@nyu.edu',   'eve',   'EveE',   'pbkdf2_sha256$600000$saltforeve111$MyxFrxSrSWIPkvPlbk29L4oebm5WB7Kgp2zE8zjIvZI=', '2026-03-01 09:00:00', '2026-03-01 09:00:00'),
(6, 'frank@nyu.edu', 'frank', 'FrankF', 'pbkdf2_sha256$600000$saltforfrank1$ZvkHJ1uVNhyjklombotvBQX2KFGBeG4EBLXcj52XHG8=', '2026-03-10 14:00:00', '2026-03-10 14:00:00');

-- ------------------------------------------------------------
-- Workspaces
--   1 Engineering  (alice)
--   2 Marketing    (bob)
-- ------------------------------------------------------------

INSERT INTO workspace (workspace_id, name, description, created_by, created_at) VALUES
(1, 'Engineering', 'Engineering team workspace',  1, '2026-02-01 10:00:00'),
(2, 'Marketing',   'Marketing and growth team',   2, '2026-03-01 10:00:00');

-- ------------------------------------------------------------
-- Workspace memberships
-- ------------------------------------------------------------

INSERT INTO workspace_membership (workspace_id, user_id, role, joined_at) VALUES
-- Engineering
(1, 1, 'admin',  '2026-02-01 10:00:00'),  -- alice (creator)
(1, 2, 'member', '2026-02-05 09:00:00'),  -- bob
(1, 3, 'member', '2026-02-10 11:30:00'),  -- carol
(1, 4, 'member', '2026-02-15 13:00:00'),  -- dave
(1, 6, 'member', '2026-03-12 08:00:00'),  -- frank
-- Marketing
(2, 2, 'admin',  '2026-03-01 10:00:00'),  -- bob (creator)
(2, 3, 'member', '2026-03-05 14:00:00'),  -- carol
(2, 5, 'member', '2026-03-10 16:00:00');  -- eve

-- ------------------------------------------------------------
-- Workspace invitations
--   Pending invites older than 5 days test the workspace-level
--   invite audit; channel-level c4 is handled below.
-- ------------------------------------------------------------

INSERT INTO workspace_invitation (invitation_id, workspace_id, invited_by, invitee_user_id, invitee_email, invited_at, accepted, accepted_at) VALUES
-- eve invited to Engineering 10 days ago — still pending
(1, 1, 1, 5, 'eve@nyu.edu',   '2026-04-17 09:00:00', FALSE, NULL),
-- frank invited to Engineering (accepted, hence the membership above)
(2, 1, 1, 6, 'frank@nyu.edu', '2026-03-11 09:00:00', TRUE,  '2026-03-12 08:00:00');

-- ------------------------------------------------------------
-- Channels
--   1 general      Engineering  public
--   2 backend      Engineering  public
--   3 secret-proj  Engineering  private
--   4 dm-alice-bob Engineering  direct
--   5 general      Marketing    public
--   6 announcements Marketing   public
-- ------------------------------------------------------------

INSERT INTO channel (channel_id, name, workspace_id, channel_type, created_by, created_at) VALUES
(1, 'general',       1, 'public',  1, '2026-02-01 10:05:00'),
(2, 'backend',       1, 'public',  1, '2026-02-01 10:10:00'),
(3, 'secret-proj',   1, 'private', 1, '2026-02-20 09:00:00'),
(4, 'dm-alice-bob',  1, 'direct',  1, '2026-02-22 11:00:00'),
(5, 'general',       2, 'public',  2, '2026-03-01 10:05:00'),
(6, 'announcements', 2, 'public',  2, '2026-03-01 10:10:00');

-- ------------------------------------------------------------
-- Channel memberships
-- ------------------------------------------------------------

INSERT INTO channel_membership (channel_id, user_id, joined_at) VALUES
-- #general (Engineering)
(1, 1, '2026-02-01 10:05:00'),  -- alice
(1, 2, '2026-02-05 09:05:00'),  -- bob
(1, 3, '2026-02-10 11:35:00'),  -- carol
(1, 4, '2026-02-15 13:05:00'),  -- dave
-- #backend (Engineering)
(2, 1, '2026-02-01 10:10:00'),  -- alice
(2, 2, '2026-02-05 09:10:00'),  -- bob
(2, 4, '2026-02-16 10:00:00'),  -- dave (invited, accepted)
-- #secret-proj (Engineering, private)
(3, 1, '2026-02-20 09:00:00'),  -- alice (creator)
(3, 3, '2026-02-21 10:00:00'),  -- carol (invited, accepted)
-- dm-alice-bob (direct)
(4, 1, '2026-02-22 11:00:00'),  -- alice
(4, 2, '2026-02-22 11:00:00'),  -- bob
-- #general (Marketing)
(5, 2, '2026-03-01 10:05:00'),  -- bob
(5, 3, '2026-03-05 14:05:00'),  -- carol
(5, 5, '2026-03-10 16:05:00'),  -- eve
-- #announcements (Marketing)
(6, 2, '2026-03-01 10:10:00'),  -- bob
(6, 3, '2026-03-05 14:10:00');  -- carol

-- ------------------------------------------------------------
-- Channel invitations
--   Accepted ones explain the memberships above.
--   Pending ones older than 5 days are the test cases for c4.
-- ------------------------------------------------------------

INSERT INTO channel_invitation (invitation_id, channel_id, invited_by, invitee_user_id, invited_at, accepted, accepted_at) VALUES
-- carol → #secret-proj (accepted)
(1, 3, 1, 3, '2026-02-20 09:10:00', TRUE,  '2026-02-21 10:00:00'),
-- dave → #backend (accepted)
(2, 2, 1, 4, '2026-02-15 13:30:00', TRUE,  '2026-02-16 10:00:00'),
-- frank → #general Engineering, invited 10 days ago, NOT accepted  [c4 test]
(3, 1, 1, 6, '2026-04-17 08:00:00', FALSE, NULL),
-- frank → #backend Engineering, invited 8 days ago, NOT accepted   [c4 test]
(4, 2, 1, 6, '2026-04-19 08:00:00', FALSE, NULL),
-- eve → #general Engineering, invited 6 days ago, NOT accepted     [c4 test]
-- (eve is a workspace member via pending invite only — app-level guard would catch this,
--  but the row exists to populate c4 results)
(5, 1, 1, 5, '2026-04-21 08:00:00', FALSE, NULL);

-- ------------------------------------------------------------
-- Messages
--   Includes several with the word "perpendicular" spread across
--   channels alice can and cannot access — tests c7.
-- ------------------------------------------------------------

INSERT INTO message (message_id, body, channel_id, posted_by, posted_at) VALUES
-- #general Engineering (ch 1)
(1,  'Welcome everyone to the Engineering workspace!',                                    1, 1, '2026-02-01 10:06:00'),
(2,  'Thanks Alice, happy to be here.',                                                   1, 2, '2026-02-05 09:10:00'),
(3,  'Reminder: stand-up is at 10am.',                                                    1, 1, '2026-02-10 08:00:00'),
(4,  'The new API design is perpendicular to the old one — totally different axis.',       1, 2, '2026-02-15 11:00:00'),
(5,  'Good point Bob. Lets sync this afternoon.',                                         1, 1, '2026-02-15 11:05:00'),
(6,  'Sprint planning moved to Thursday.',                                                1, 4, '2026-03-01 09:00:00'),

-- #backend Engineering (ch 2)
(7,  'PR #42 is ready for review.',                                                       2, 4, '2026-02-17 14:00:00'),
(8,  'Left some comments — the auth middleware is perpendicular to the request pipeline.', 2, 1, '2026-02-18 10:30:00'),
(9,  'Fixed. Can you re-review?',                                                         2, 4, '2026-02-18 15:00:00'),
(10, 'LGTM. Merging.',                                                                    2, 2, '2026-02-19 09:00:00'),

-- #secret-proj Engineering (ch 3)
(11, 'Kicking off the stealth project today.',                                            3, 1, '2026-02-20 09:05:00'),
(12, 'The architecture here is perpendicular to anything we have done before.',           3, 3, '2026-02-21 10:10:00'),

-- dm-alice-bob (ch 4)
(13, 'Hey Bob, can you take a look at the staging env?',                                  4, 1, '2026-03-05 16:00:00'),
(14, 'Sure, on it.',                                                                      4, 2, '2026-03-05 16:05:00'),

-- #general Marketing (ch 5) — alice has NO access to this workspace
(15, 'Q2 campaign: the messaging is perpendicular to last quarter — totally fresh angle.', 5, 3, '2026-03-10 10:00:00'),
(16, 'Love it. Lets go with that positioning.',                                           5, 2, '2026-03-10 10:15:00'),

-- #announcements Marketing (ch 6)
(17, 'New brand guidelines are live — check the drive.',                                  6, 2, '2026-03-15 09:00:00'),
(18, 'Thanks! Will review today.',                                                        6, 3, '2026-03-15 10:00:00'),

-- #general Engineering — more activity
(19, 'Anyone free for a quick sync at 2pm?',                                              1, 3, '2026-03-15 10:00:00'),
(20, 'I am, adding it to the calendar.',                                                  1, 4, '2026-03-15 10:05:00'),
(21, 'Same here.',                                                                        1, 2, '2026-03-15 10:06:00'),
(22, 'Heads up: deploying the new auth service tonight at 11pm.',                         1, 1, '2026-04-01 17:00:00'),
(23, 'Is the rollback plan ready just in case?',                                          1, 4, '2026-04-01 17:10:00'),
(24, 'Yes, tested it this morning. Should be smooth.',                                    1, 1, '2026-04-01 17:15:00'),

-- #backend Engineering — deeper technical thread
(25, 'The new caching layer is perpendicular to what Redis was doing — totally decoupled.', 2, 4, '2026-04-05 11:00:00'),
(26, 'Good. Means we can swap it out later without touching the API.',                    2, 1, '2026-04-05 11:10:00'),
(27, 'Exactly. PR is up — link in the description.',                                      2, 4, '2026-04-05 11:12:00'),
(28, 'Reviewed. One nit on the error handling, otherwise LGTM.',                         2, 2, '2026-04-05 14:00:00'),
(29, 'Fixed, re-review when you get a chance.',                                           2, 4, '2026-04-05 14:30:00'),
(30, 'Merged. Nice work.',                                                                2, 1, '2026-04-05 15:00:00'),

-- #secret-proj Engineering — stealth planning
(31, 'Got sign-off from leadership. We are greenlit.',                                    3, 1, '2026-04-10 09:00:00'),
(32, 'Finally! When do we kick off the design phase?',                                    3, 3, '2026-04-10 09:15:00'),
(33, 'Next Monday. I will send out a doc today.',                                         3, 1, '2026-04-10 09:20:00'),

-- #general Marketing — campaign planning
(34, 'We hit 10k signups this month. Great work everyone.',                               5, 2, '2026-04-12 10:00:00'),
(35, 'Incredible! The referral campaign really paid off.',                                5, 5, '2026-04-12 10:10:00'),
(36, 'Next target: 25k by end of Q2.',                                                   5, 3, '2026-04-12 10:15:00'),

-- dm-alice-bob — more direct messages
(37, 'Bob, can you take the 4pm call with the client today? I have a conflict.',          4, 1, '2026-04-15 13:00:00'),
(38, 'Sure, I will handle it. Anything I should know going in?',                         4, 2, '2026-04-15 13:05:00'),
(39, 'They want a timeline on the API integration. We said Q3, stick to that.',          4, 1, '2026-04-15 13:07:00'),
(40, 'Got it. Talk later.',                                                               4, 2, '2026-04-15 13:08:00');

-- ------------------------------------------------------------
-- Reset sequences so future INSERTs auto-increment correctly
-- ------------------------------------------------------------

SELECT setval('users_user_id_seq',                (SELECT MAX(user_id)       FROM users));
SELECT setval('workspace_workspace_id_seq',        (SELECT MAX(workspace_id)  FROM workspace));
SELECT setval('workspace_invitation_invitation_id_seq', (SELECT MAX(invitation_id) FROM workspace_invitation));
SELECT setval('channel_channel_id_seq',            (SELECT MAX(channel_id)    FROM channel));
SELECT setval('channel_invitation_invitation_id_seq',   (SELECT MAX(invitation_id) FROM channel_invitation));
SELECT setval('message_message_id_seq',            (SELECT MAX(message_id)    FROM message));
