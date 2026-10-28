import pandas as pd

from audit_recipes import tests_catalog as tc
from audit_recipes.synthetic import generate, write_dataset

from .conftest import build_fixture


def flagged(fixture_dir, test_id):
    con = tc.connect(fixture_dir)
    spec = next(s for s in tc.CATALOG if s.test_id == test_id)
    return set(tc.run_test(con, spec).entity_id)


def test_exact_duplicate(fixture_dir):
    assert flagged(fixture_dir, "dup_invoice_exact") == {"I2"}


def test_fuzzy_duplicate(fixture_dir):
    assert flagged(fixture_dir, "dup_invoice_fuzzy") == {"I3"}


def test_split_purchase(fixture_dir):
    assert flagged(fixture_dir, "split_purchase") == {"P1", "P2"}


def test_payment_after_bank_change(fixture_dir):
    assert flagged(fixture_dir, "bank_change_payment") == {"PAY1"}


def test_round_amount(fixture_dir):
    assert flagged(fixture_dir, "je_round_amount") == {"J1"}


def test_weekend_holiday(fixture_dir):
    assert flagged(fixture_dir, "je_weekend_holiday") == {"J2", "J3"}


def test_unauthorized_poster(fixture_dir):
    assert flagged(fixture_dir, "je_unauthorized_poster") == {"J4"}


def test_leaver_active(fixture_dir):
    assert flagged(fixture_dir, "leaver_active_account") == {"U4"}


def test_dormant_privileged(fixture_dir):
    assert flagged(fixture_dir, "dormant_privileged_account") == {"U6"}


def test_sod_conflict(fixture_dir):
    assert flagged(fixture_dir, "sod_conflict") == {"U3"}


def test_benford_vendor(tmp_path):
    extra = [(f"X{i}", "V3", f"B{i}", "2025-07-01", 1000.0 + 97.13 * i, None) for i in range(60)]
    write_dataset(build_fixture(extra), tmp_path)
    assert flagged(tmp_path, "benford_vendor") == {"V3"}


def test_run_all_and_evaluate_on_full_sample(tmp_path):
    write_dataset(generate(42), tmp_path)
    result = tc.evaluate(tc.run_all(tmp_path), pd.read_csv(tmp_path / "anomaly_labels.csv"))
    assert (result.recall >= 0.8).all()
    assert len(result) == len(tc.CATALOG)
