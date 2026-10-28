-- Test: dup_invoice_fuzzy
-- Risk:  A duplicate escapes the exact test because the invoice number was retyped or the
--        supplier exists twice in the vendor master under a name variant.
-- Logic: Same amount, invoice dates within `fuzzy_date_days`, and either the same vendor or
--        vendor names that are near-identical after normalisation (lower case, "limited" ->
--        "ltd", punctuation removed, Jaro-Winkler >= `fuzzy_name_similarity`). Pairs that are
--        exact duplicates (same vendor and number) are left to test 01.
-- Output: entity_id = the later invoice of the pair.
WITH inv AS (
    SELECT
        i.invoice_id, i.vendor_id, i.invoice_number, i.invoice_date, i.amount,
        regexp_replace(
            replace(replace(lower(v.name), 'limited', 'ltd'), 'incorporated', 'inc'),
            '[^a-z0-9]', '', 'g')                AS name_norm
    FROM invoices i
    JOIN vendors v USING (vendor_id)
)
SELECT DISTINCT ON (b.invoice_id)
    b.invoice_id                                 AS entity_id,
    a.invoice_id                                 AS matched_invoice_id,
    a.vendor_id                                  AS matched_vendor_id,
    b.vendor_id,
    b.invoice_number,
    b.amount,
    b.invoice_date,
    date_diff('day', a.invoice_date, b.invoice_date) AS days_apart
FROM inv a
JOIN inv b
  ON a.amount = b.amount
 AND (b.invoice_date, b.invoice_id) > (a.invoice_date, a.invoice_id)
CROSS JOIN params p
WHERE date_diff('day', a.invoice_date, b.invoice_date) <= p.fuzzy_date_days
  AND NOT (a.vendor_id = b.vendor_id AND upper(trim(a.invoice_number)) = upper(trim(b.invoice_number)))
  AND (a.vendor_id = b.vendor_id
       OR jaro_winkler_similarity(a.name_norm, b.name_norm) >= p.fuzzy_name_similarity)
ORDER BY b.invoice_id, a.invoice_date;
