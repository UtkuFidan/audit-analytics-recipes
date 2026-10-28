"""Tiny hand-built fixture: every test has known positive and negative cases."""

from __future__ import annotations

import pandas as pd
import pytest

from audit_recipes.synthetic import COLUMNS, HOLIDAYS, ROLES, SOD_PAIRS, write_dataset


def build_fixture(extra_invoices: list[tuple] | None = None) -> dict[str, pd.DataFrame]:
    def frame(name: str, rows: list[tuple]) -> pd.DataFrame:
        return pd.DataFrame(rows, columns=COLUMNS[name])

    inv = [
        # invoice_id, vendor, number, date, amount, po
        ("I1", "V1", "N1", "2025-03-01", 500.00, None),
        ("I2", "V1", "n1 ", "2025-03-05", 500.00, None),  # exact duplicate of I1
        ("I3", "V2", "N9", "2025-03-04", 777.00, None),  # fuzzy duplicate of I4 (name variant)
        ("I4", "V1", "N8", "2025-03-01", 777.00, None),
        ("I5", "V3", "N5", "2025-03-03", 500.00, None),  # same amount, different vendor: clean
        ("I6", "V1", "N6", "2025-04-20", 500.00, None),  # same vendor/amount, 50 days later
    ] + (extra_invoices or [])
    t = {
        "vendors": frame(
            "vendors",
            [
                ("V1", "Acme Ltd", "GB", "TX1", "OLD1", "2020-01-01"),
                ("V2", "ACME Limited", "GB", "TX1", "OLD2", "2020-01-01"),
                ("V3", "Other Inc", "US", "TX3", "NEW", "2020-01-01"),
            ],
        ),
        "vendor_bank_changes": frame(
            "vendor_bank_changes",
            [
                ("BC1", "V3", "2025-06-01", "OLD", "NEW", "U1"),
            ],
        ),
        "purchase_orders": frame(
            "purchase_orders",
            [
                ("P1", "V1", "2025-02-01", 9000.0, "U1", None),
                ("P2", "V1", "2025-02-04", 8500.0, "U1", None),  # split with P1
                ("P3", "V1", "2025-09-01", 9000.0, "U1", None),  # too far from P1/P2
                ("P4", "V3", "2025-02-01", 3000.0, "U1", None),  # small
                ("P5", "V3", "2025-02-02", 20000.0, "U1", "U9"),  # over limit, approved
            ],
        ),
        "invoices": frame("invoices", inv),
        "payments": frame(
            "payments",
            [
                ("PAY1", "I5", "V3", "2025-06-05", 500.0, "NEW"),  # 4 days after change: flagged
                ("PAY2", "I5", "V3", "2025-06-30", 500.0, "NEW"),  # 29 days after: clean
                ("PAY3", "I5", "V3", "2025-05-30", 500.0, "OLD"),  # before change: clean
            ],
        ),
        "gl_journal": frame(
            "gl_journal",
            [
                ("J1", "2025-03-04", "2025-03", "6100", "2000", 20000.00, "MANUAL", "U2", "x", ""),
                ("J2", "2025-03-08", "2025-03", "6100", "2000", 1234.56, "MANUAL", "U2", "x", ""),  # Sat
                ("J3", "2025-12-25", "2025-12", "6100", "2000", 500.10, "MANUAL", "U2", "x", ""),  # hol.
                ("J4", "2025-03-05", "2025-03", "6100", "2000", 321.55, "MANUAL", "U3", "x", ""),  # !post
                ("J5", "2025-03-08", "2025-03", "6100", "2000", 5000.0, "AUTO", "SYSTEM", "x", ""),
                ("J6", "2025-03-05", "2025-03", "6100", "2000", 12.34, "MANUAL", "U2", "x", ""),
                ("J7", "2025-03-05", "2025-03", "6100", "2000", 1000.0, "MANUAL", "U2", "x", ""),  # <5k
            ],
        ),
        "employees": frame(
            "employees",
            [
                ("E3", "Finance", "2018-01-01", None),
                ("E4", "Finance", "2018-01-01", "2025-06-30"),  # leaver, account active
                ("E5", "Finance", "2018-01-01", "2026-03-01"),  # future leaver
                ("E8", "Finance", "2018-01-01", "2025-05-01"),  # leaver, account disabled
            ],
        ),
        "user_accounts": frame(
            "user_accounts",
            [
                ("U1", None, "ACTIVE", "2020-01-01", "2025-12-20"),
                ("U2", None, "ACTIVE", "2020-01-01", "2025-12-20"),
                ("U3", "E3", "ACTIVE", "2020-01-01", "2025-12-20"),
                ("U4", "E4", "ACTIVE", "2020-01-01", "2025-12-20"),
                ("U5", "E5", "ACTIVE", "2020-01-01", "2025-12-20"),
                ("U6", None, "ACTIVE", "2020-01-01", "2025-01-15"),  # dormant privileged
                ("U7", None, "ACTIVE", "2020-01-01", "2025-12-20"),
                ("U8", "E8", "DISABLED", "2020-01-01", "2025-04-30"),
                ("U9", None, "ACTIVE", "2020-01-01", "2024-01-01"),  # idle but not privileged
            ],
        ),
        "user_roles": frame(
            "user_roles",
            [
                ("U1", "BUYER"),
                ("U2", "GL_POSTER"),
                ("U3", "AP_CLERK"),
                ("U3", "PAYMENT_RELEASER"),
                ("U4", "VIEWER"),
                ("U5", "VIEWER"),
                ("U6", "SYS_ADMIN"),
                ("U7", "SYS_ADMIN"),
                ("U8", "VIEWER"),
                ("U9", "VIEWER"),
            ],
        ),
        "roles": frame("roles", [(r, v[0], v[1]) for r, v in ROLES.items()]),
        "role_permissions": frame("role_permissions", [(r, p) for r, v in ROLES.items() for p in v[2]]),
        "sod_matrix": frame("sod_matrix", SOD_PAIRS),
        "holidays": frame("holidays", [(d.isoformat(), n) for d, n in HOLIDAYS]),
        "anomaly_labels": frame("anomaly_labels", []),
    }
    return t


@pytest.fixture()
def fixture_dir(tmp_path):
    write_dataset(build_fixture(), tmp_path)
    return tmp_path
