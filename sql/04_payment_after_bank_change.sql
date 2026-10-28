-- Test: bank_change_payment
-- Risk:  Payment diversion fraud: attacker changes supplier bank details, then a payment follows.
-- Logic: A payment made to the *new* IBAN within `bank_window_days` after the change date.
-- Output: entity_id = payment_id (closest preceding change if several).
SELECT DISTINCT ON (pay.payment_id)
    pay.payment_id                               AS entity_id,
    pay.vendor_id,
    pay.payment_date,
    pay.amount,
    bc.change_id,
    bc.change_date,
    date_diff('day', bc.change_date, pay.payment_date) AS days_after_change
FROM payments pay
JOIN vendor_bank_changes bc
  ON bc.vendor_id = pay.vendor_id
 AND pay.bank_iban = bc.new_iban
 AND pay.payment_date >= bc.change_date
CROSS JOIN params p
WHERE date_diff('day', bc.change_date, pay.payment_date) <= p.bank_window_days
ORDER BY pay.payment_id, bc.change_date DESC;
