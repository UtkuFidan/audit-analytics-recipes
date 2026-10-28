-- Test: je_weekend_holiday
-- Risk:  Manual entries outside normal working time are less likely to be reviewed.
-- Logic: Manual entries whose posting date is a Saturday, Sunday or listed public holiday.
-- Output: entity_id = je_id.
SELECT
    j.je_id AS entity_id, j.posting_date, dayname(j.posting_date) AS weekday,
    h.name AS holiday, j.amount, j.posted_by, j.description
FROM gl_journal j
LEFT JOIN holidays h ON h.holiday_date = j.posting_date
WHERE j.source = 'MANUAL'
  AND (isodow(j.posting_date) IN (6, 7) OR h.holiday_date IS NOT NULL)
ORDER BY j.je_id;
