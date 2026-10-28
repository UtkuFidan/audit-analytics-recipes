-- Test: sod_conflict
-- Risk:  One person can run a process end to end (e.g. create and approve), enabling fraud.
-- Logic: Users holding both roles of any pair listed in the SoD matrix.
-- Output: entity_id = user_id.
SELECT
    a.user_id AS entity_id,
    list(m.role_a || ' + ' || m.role_b ORDER BY m.role_a) AS conflicts
FROM user_roles a
JOIN user_roles b ON a.user_id = b.user_id
JOIN sod_matrix m ON a.role = m.role_a AND b.role = m.role_b
GROUP BY a.user_id
ORDER BY a.user_id;
