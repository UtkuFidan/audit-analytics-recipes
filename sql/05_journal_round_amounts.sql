-- Test: je_round_amount
-- Risk:  Estimated or "plugged" manual journals, often used to manage results.
-- Logic: Manual entries of at least `round_min_amount` that are an exact multiple of
--        `round_modulus` (cents included, so 20,000.00 qualifies and 20,000.37 does not).
-- Output: entity_id = je_id.
SELECT
    j.je_id AS entity_id, j.posting_date, j.amount, j.posted_by, j.description
FROM gl_journal j CROSS JOIN params p
WHERE j.source = 'MANUAL'
  AND j.amount >= p.round_min_amount
  AND CAST(round(j.amount * 100) AS BIGINT) % CAST(p.round_modulus * 100 AS BIGINT) = 0
ORDER BY j.je_id;
