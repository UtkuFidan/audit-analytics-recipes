-- Test: benford_vendor (SQL half)
-- Risk:  Fabricated or manipulated amounts rarely follow Benford's law for first digits.
-- Logic: First-digit counts of invoice amounts per vendor. Python (benford.py) turns these
--        into chi-square, p-value and MAD (Nigrini) per vendor and overall.
-- Output: vendor_id, digit (1-9), n.
SELECT
    vendor_id,
    CAST(left(ltrim(replace(CAST(amount AS VARCHAR), '.', ''), '0'), 1) AS INTEGER) AS digit,
    count(*) AS n
FROM invoices
WHERE amount > 0
GROUP BY ALL
ORDER BY vendor_id, digit;
