-- Test: dup_invoice_exact
-- Risk:  The same supplier invoice is paid twice.
-- Logic: Same vendor, same invoice number (case/space-insensitive) and same amount. The earliest
--        copy is treated as the original; every later copy is a finding.
-- Output: entity_id = the duplicate invoice_id.
SELECT
    invoice_id AS entity_id, original_invoice_id, vendor_id, invoice_number, amount, invoice_date
FROM (
    SELECT
        *,
        row_number() OVER w  AS rn,
        first_value(invoice_id) OVER w AS original_invoice_id
    FROM invoices
    WINDOW w AS (PARTITION BY vendor_id, upper(trim(invoice_number)), amount
                 ORDER BY invoice_date, invoice_id)
)
WHERE rn > 1
ORDER BY invoice_id;
