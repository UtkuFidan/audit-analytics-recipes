-- Test: dormant_privileged_account
-- Risk:  Unused powerful accounts are rarely monitored and attractive to attackers.
-- Logic: ACTIVE accounts holding a privileged role (roles.is_privileged) whose last login is
--        more than `dormant_days` before `as_of`, or that never logged in.
-- Output: entity_id = user_id.
SELECT
    u.user_id AS entity_id,
    list(DISTINCT r.role ORDER BY r.role) AS privileged_roles,
    u.last_login,
    date_diff('day', u.last_login, p.as_of) AS days_idle
FROM user_accounts u
JOIN user_roles ur USING (user_id)
JOIN roles r ON r.role = ur.role AND r.is_privileged
CROSS JOIN params p
WHERE u.status = 'ACTIVE'
  AND (u.last_login IS NULL OR date_diff('day', u.last_login, p.as_of) > p.dormant_days)
GROUP BY u.user_id, u.last_login, p.as_of
ORDER BY u.user_id;
