-- Test: split_purchase
-- Risk:  A purchase is split into several orders, each just under the approval limit, to avoid
--        the second approver.
-- Logic: Purchase orders below `approval_limit` but at least `split_floor_ratio` of it, raised by
--        the same requester on the same vendor within `split_window_days` of each other, whose
--        combined value exceeds the limit. Every member order is a finding.
-- Output: entity_id = purchase order id.
WITH near_limit AS (
    SELECT po.*
    FROM purchase_orders po CROSS JOIN params p
    WHERE po.amount < p.approval_limit
      AND po.amount >= p.split_floor_ratio * p.approval_limit
),
pairs AS (
    SELECT a.po_id AS a_id, b.po_id AS b_id
    FROM near_limit a
    JOIN near_limit b
      ON a.vendor_id = b.vendor_id
     AND a.requester_id = b.requester_id
     AND a.po_id < b.po_id
    CROSS JOIN params p
    WHERE abs(date_diff('day', a.po_date, b.po_date)) <= p.split_window_days
      AND a.amount + b.amount > p.approval_limit
),
members AS (
    SELECT a_id AS po_id, b_id AS partner FROM pairs
    UNION ALL
    SELECT b_id, a_id FROM pairs
)
SELECT
    po.po_id                                     AS entity_id,
    po.vendor_id,
    po.requester_id,
    po.po_date,
    po.amount,
    list(DISTINCT m.partner ORDER BY m.partner)  AS linked_po_ids
FROM members m
JOIN purchase_orders po USING (po_id)
GROUP BY ALL
ORDER BY po.po_id;
