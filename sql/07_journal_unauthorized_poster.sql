-- Test: je_unauthorized_poster
-- Risk:  Journals posted by people whose role does not allow posting (access control failure).
-- Logic: Manual entries whose posted_by user holds no role with the `post_journal` permission.
-- Output: entity_id = je_id.
WITH allowed AS (
    SELECT DISTINCT ur.user_id
    FROM user_roles ur
    JOIN role_permissions rp USING (role)
    WHERE rp.permission = 'post_journal'
)
SELECT
    j.je_id AS entity_id, j.posting_date, j.amount, j.posted_by, j.description
FROM gl_journal j
WHERE j.source = 'MANUAL'
  AND j.posted_by NOT IN (SELECT user_id FROM allowed)
ORDER BY j.je_id;
