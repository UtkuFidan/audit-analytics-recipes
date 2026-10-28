import hashlib

from audit_recipes.synthetic import COLUMNS, generate, write_dataset


def _digest(tmp_path, seed):
    write_dataset(generate(seed), tmp_path)
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(tmp_path.glob("*.csv"))}


def test_same_seed_is_identical(tmp_path):
    assert _digest(tmp_path / "a", 7) == _digest(tmp_path / "b", 7)


def test_different_seed_differs(tmp_path):
    assert _digest(tmp_path / "a", 7) != _digest(tmp_path / "b", 8)


def test_schema_and_labels():
    t = generate(42)
    assert set(t) == set(COLUMNS)
    for name, df in t.items():
        assert list(df.columns) == COLUMNS[name]
    counts = t["anomaly_labels"].groupby("test_id").size()
    assert len(counts) == 11 and counts.min() >= 1
    # Every labelled entity exists in its source table.
    ids = {
        "invoice": set(t["invoices"].invoice_id),
        "payment": set(t["payments"].payment_id),
        "purchase_order": set(t["purchase_orders"].po_id),
        "journal_entry": set(t["gl_journal"].je_id),
        "user": set(t["user_accounts"].user_id),
        "vendor": set(t["vendors"].vendor_id),
    }
    for r in t["anomaly_labels"].itertuples():
        assert r.entity_id in ids[r.entity_type]
