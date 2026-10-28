-- Test: leaver_active_account
-- Risk:  Former employees retain system access.
-- Logic: Account status ACTIVE while the linked employee's leave date is on or before `as_of`.
--        Future leave dates (notice periods) and service accounts (no employee) are not flagged.
-- Output: entity_id = user_id.
SELECT
    u.user_id AS entity_id, u.employee_id, e.leave_date, u.last_login,
    date_diff('day', e.leave_date, p.as_of) AS days_since_leaving,
    u.last_login > e.leave_date             AS login_after_leaving
FROM user_accounts u
JOIN employees e USING (employee_id)
CROSS JOIN params p
WHERE u.status = 'ACTIVE'
  AND e.leave_date <= p.as_of
ORDER BY u.user_id;
