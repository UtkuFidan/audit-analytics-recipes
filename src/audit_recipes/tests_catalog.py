"""Test catalogue: run every SQL test over a data directory and evaluate against labels."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd

from . import SQL_DIR, benford


@dataclass(frozen=True)
class TestSpec:
    __test__ = False  # not a pytest class

    test_id: str
    title: str
    risk: str
    logic: str
    sql_file: str
    entity_type: str


CATALOG: list[TestSpec] = [
    TestSpec(
        "dup_invoice_exact",
        "Exact duplicate invoices",
        "Double payment",
        "Same vendor, invoice number and amount",
        "01_duplicate_invoices_exact.sql",
        "invoice",
    ),
    TestSpec(
        "dup_invoice_fuzzy",
        "Fuzzy duplicate invoices",
        "Double payment, vendor master dupes",
        "Same amount, dates within 7 days, same or near-identical vendor name",
        "02_duplicate_invoices_fuzzy.sql",
        "invoice",
    ),
    TestSpec(
        "split_purchase",
        "Split purchases",
        "Approval-limit avoidance",
        "POs at 70-100% of the limit, same requester and vendor within 7 days, sum over limit",
        "03_split_purchases.sql",
        "purchase_order",
    ),
    TestSpec(
        "bank_change_payment",
        "Payment after bank-detail change",
        "Payment diversion fraud",
        "Payment to the new IBAN within 14 days of the change",
        "04_payment_after_bank_change.sql",
        "payment",
    ),
    TestSpec(
        "je_round_amount",
        "Round-amount manual journals",
        "Management override, plugs",
        "Manual entry of 5,000 or more that is a multiple of 1,000",
        "05_journal_round_amounts.sql",
        "journal_entry",
    ),
    TestSpec(
        "je_weekend_holiday",
        "Weekend/holiday manual journals",
        "Unreviewed postings",
        "Manual entry posted on Saturday, Sunday or a public holiday",
        "06_journal_weekend_holiday.sql",
        "journal_entry",
    ),
    TestSpec(
        "je_unauthorized_poster",
        "Journals by unauthorised users",
        "Access control failure",
        "Poster holds no role with post_journal",
        "07_journal_unauthorized_poster.sql",
        "journal_entry",
    ),
    TestSpec(
        "leaver_active_account",
        "Leavers with active accounts",
        "Unauthorised access",
        "Account ACTIVE and HR leave date on or before cut-off",
        "08_leavers_active_accounts.sql",
        "user",
    ),
    TestSpec(
        "dormant_privileged_account",
        "Dormant privileged accounts",
        "Unmonitored access",
        "Active account with privileged role, idle over 90 days",
        "09_dormant_privileged_accounts.sql",
        "user",
    ),
    TestSpec(
        "sod_conflict",
        "Segregation-of-duties conflicts",
        "Fraud, error",
        "User holds both roles of a pair in the SoD matrix",
        "10_sod_conflicts.sql",
        "user",
    ),
    TestSpec(
        "benford_vendor",
        "Benford first-digit by vendor",
        "Fabricated amounts",
        "Vendor with 40+ invoices rejects Benford (chi-square p < 0.001)",
        "11_benford_first_digit.sql",
        "vendor",
    ),
]


def connect(data_dir: str | Path) -> duckdb.DuckDBPyConnection:
    """In-memory DuckDB with views over the CSVs in `data_dir` and the `params` table."""
    data_dir = Path(data_dir).resolve()
    con = duckdb.connect()
    setup = (SQL_DIR / "00_setup.sql").read_text().replace("'data/", f"'{data_dir.as_posix()}/")
    con.execute(setup)
    return con


def _plain(v):
    return v.tolist() if hasattr(v, "tolist") else v


def run_test(con, spec: TestSpec) -> pd.DataFrame:
    """Findings for one test: columns test_id, entity_type, entity_id, detail (JSON)."""
    if spec.test_id == "benford_vendor":
        df = benford.flag_vendors(con)
    else:
        df = con.execute((SQL_DIR / spec.sql_file).read_text()).df()
    extra = [c for c in df.columns if c != "entity_id"]
    detail = [json.dumps({c: _plain(row[c]) for c in extra}, default=str) for _, row in df.iterrows()]
    return pd.DataFrame(
        {
            "test_id": spec.test_id,
            "entity_type": spec.entity_type,
            "entity_id": df["entity_id"].astype(str),
            "detail": detail,
        }
    )


def run_all(data_dir: str | Path) -> pd.DataFrame:
    con = connect(data_dir)
    parts = [run_test(con, s) for s in CATALOG]
    return pd.concat(parts, ignore_index=True)


def evaluate(findings: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    """Precision and recall per test against the injected labels."""
    rows = []
    for spec in CATALOG:
        got = set(findings.loc[findings.test_id == spec.test_id, "entity_id"])
        truth = set(labels.loc[labels.test_id == spec.test_id, "entity_id"])
        tp = len(got & truth)
        fp, fn = len(got - truth), len(truth - got)
        precision = tp / (tp + fp) if got else float("nan")
        recall = tp / len(truth) if truth else float("nan")
        f1 = 2 * precision * recall / (precision + recall) if tp else 0.0
        rows.append(
            {
                "test_id": spec.test_id,
                "injected": len(truth),
                "flagged": len(got),
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "precision": round(precision, 3),
                "recall": round(recall, 3),
                "f1": round(f1, 3),
            }
        )
    return pd.DataFrame(rows)


def to_markdown(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(lines)
