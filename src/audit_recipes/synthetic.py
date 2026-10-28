"""Seeded generator for a small fictional company ("Lumen Components").

Everything is synthetic. The generator builds a clean background population and then
injects labelled anomalies. The labels (``anomaly_labels``) are the ground truth the
``evaluate`` command measures every test against.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

FY_START = date(2025, 1, 1)
AS_OF = date(2025, 12, 31)
APPROVAL_LIMIT = 10_000.0

HOLIDAYS = [
    (date(2025, 1, 1), "New Year's Day"),
    (date(2025, 4, 18), "Good Friday"),
    (date(2025, 4, 21), "Easter Monday"),
    (date(2025, 5, 1), "Labour Day"),
    (date(2025, 12, 25), "Christmas Day"),
    (date(2025, 12, 26), "Boxing Day"),
]

COLUMNS: dict[str, list[str]] = {
    "vendors": ["vendor_id", "name", "country", "tax_id", "bank_iban", "created_date"],
    "vendor_bank_changes": [
        "change_id",
        "vendor_id",
        "change_date",
        "old_iban",
        "new_iban",
        "changed_by",
    ],
    "purchase_orders": [
        "po_id",
        "vendor_id",
        "po_date",
        "amount",
        "requester_id",
        "approver_id",
    ],
    "invoices": ["invoice_id", "vendor_id", "invoice_number", "invoice_date", "amount", "po_id"],
    "payments": ["payment_id", "invoice_id", "vendor_id", "payment_date", "amount", "bank_iban"],
    "gl_journal": [
        "je_id",
        "posting_date",
        "period",
        "debit_account",
        "credit_account",
        "amount",
        "source",
        "posted_by",
        "description",
        "reference",
    ],
    "employees": ["employee_id", "department", "hire_date", "leave_date"],
    "user_accounts": ["user_id", "employee_id", "status", "created_date", "last_login"],
    "user_roles": ["user_id", "role"],
    "roles": ["role", "is_privileged", "description"],
    "role_permissions": ["role", "permission"],
    "sod_matrix": ["role_a", "role_b", "rationale"],
    "holidays": ["holiday_date", "name"],
    "anomaly_labels": ["test_id", "entity_type", "entity_id", "note"],
}

# role -> (is_privileged, description, permissions)
ROLES: dict[str, tuple[bool, str, list[str]]] = {
    "AP_CLERK": (False, "Enters supplier invoices", ["enter_invoice"]),
    "AP_APPROVER": (False, "Approves supplier invoices", ["approve_invoice"]),
    "PAYMENT_RELEASER": (False, "Releases payment runs", ["release_payment"]),
    "VENDOR_MASTER_ADMIN": (True, "Maintains vendor master data", ["edit_vendor", "change_bank"]),
    "BUYER": (False, "Creates purchase orders", ["create_po"]),
    "PO_APPROVER": (False, "Approves purchase orders above the limit", ["approve_po"]),
    "GL_POSTER": (True, "Posts manual journal entries", ["post_journal"]),
    "GL_APPROVER": (False, "Approves manual journal entries", ["approve_journal"]),
    "SYS_ADMIN": (True, "System administration", ["admin_system"]),
    "USER_ADMIN": (True, "Creates and changes user accounts", ["manage_users"]),
    "VIEWER": (False, "Read-only reporting", ["view_reports"]),
}

SOD_PAIRS = [
    ("AP_CLERK", "PAYMENT_RELEASER", "Entering invoices and releasing payments"),
    ("AP_CLERK", "VENDOR_MASTER_ADMIN", "Entering invoices and editing vendor master data"),
    ("BUYER", "PO_APPROVER", "Creating and approving the same purchase order"),
    ("GL_POSTER", "GL_APPROVER", "Posting and approving the same journal entry"),
    ("SYS_ADMIN", "GL_POSTER", "System administration combined with journal posting"),
]

_ROLE_COUNTS = {
    "AP_CLERK": 22,
    "AP_APPROVER": 6,
    "PAYMENT_RELEASER": 6,
    "VENDOR_MASTER_ADMIN": 4,
    "BUYER": 18,
    "PO_APPROVER": 8,
    "GL_POSTER": 8,
    "GL_APPROVER": 5,
    "SYS_ADMIN": 3,
    "USER_ADMIN": 3,
}  # everyone else eligible gets VIEWER

_WORD_A = [
    "Apex",
    "Birch",
    "Cobalt",
    "Delta",
    "Ember",
    "Falcon",
    "Granite",
    "Harbor",
    "Iris",
    "Juniper",
    "Keystone",
    "Lumen",
    "Meridian",
    "Nimbus",
    "Orchid",
    "Pioneer",
    "Quartz",
    "Ridge",
    "Summit",
    "Tidal",
    "Umber",
    "Vertex",
    "Willow",
    "Xenon",
    "Yarrow",
    "Zenith",
    "Argent",
    "Bolt",
    "Cedar",
    "Dune",
]
_WORD_B = [
    "Freight",
    "Metals",
    "Plastics",
    "Logistics",
    "Electronics",
    "Packaging",
    "Tooling",
    "Fasteners",
    "Chemicals",
    "Textiles",
    "Software",
    "Consulting",
    "Catering",
    "Cleaning",
    "Security",
    "Printing",
    "Lighting",
    "Bearings",
    "Cables",
    "Coatings",
    "Hydraulics",
    "Sensors",
    "Labels",
    "Pallets",
    "Filters",
    "Valves",
    "Wiring",
    "Castings",
    "Optics",
    "Adhesives",
]
_SUFFIXES = ["Ltd", "GmbH", "Inc", "LLC", "SA"]
_VARIANT_SUFFIX = {
    "Ltd": ["Limited", "LTD."],
    "GmbH": ["GMBH", "GmbH."],
    "Inc": ["Incorporated", "INC."],
    "LLC": ["L.L.C.", "LLC."],
    "SA": ["S.A.", "SA."],
}
_COUNTRIES = ["DE", "NL", "PL", "TR", "GB", "FR", "ES", "IT"]
_DEPARTMENTS = ["Finance", "Procurement", "Operations", "IT", "Sales", "HR", "Logistics", "Legal"]
_JE_TEXT = [
    "Accrual adjustment",
    "Reclassification",
    "Prepayment release",
    "Depreciation true-up",
    "Intercompany settlement",
    "Provision update",
    "Cost allocation",
    "FX revaluation",
]
_EXPENSE_ACCOUNTS = ["5000", "5100", "6100", "6200", "6300", "6400", "7000"]


class _Table:
    """Collects rows, then assigns sequential ids ordered by date."""

    def __init__(self, prefix: str, id_col: str, sort_col: str):
        self.prefix, self.id_col, self.sort_col = prefix, id_col, sort_col
        self.rows: list[dict] = []
        self.idmap: dict[int, str] = {}

    def add(self, **row) -> int:
        self.rows.append(row)
        return len(self.rows) - 1

    def finalize(self) -> pd.DataFrame:
        df = pd.DataFrame(self.rows)
        df["_k"] = range(len(df))
        df = df.sort_values([self.sort_col, "_k"], kind="stable").reset_index(drop=True)
        df.insert(0, self.id_col, [f"{self.prefix}-{i + 1:06d}" for i in range(len(df))])
        self.idmap = dict(zip(df["_k"], df[self.id_col], strict=True))
        return df.drop(columns="_k")


def _day(offset: int) -> date:
    return FY_START + timedelta(days=int(offset))


def _is_business_day(d: date) -> bool:
    return d.weekday() < 5 and d not in {h for h, _ in HOLIDAYS}


class _Generator:
    def __init__(self, seed: int):
        self.rng = np.random.default_rng(seed)
        self.labels: list[tuple[str, str, str, str]] = []

    # -- helpers ---------------------------------------------------------------------------
    def label(self, test_id: str, entity_type: str, entity_id: str, note: str = "") -> None:
        self.labels.append((test_id, entity_type, entity_id, note))

    def pick(self, seq, n: int | None = None, replace: bool = False):
        seq = list(seq)
        if n is None:
            return seq[int(self.rng.integers(len(seq)))]
        idx = self.rng.choice(len(seq), size=n, replace=replace)
        return [seq[int(i)] for i in idx]

    def amount(self, lo: float = 2.0, hi: float = 5.0) -> float:
        """Log-uniform amount, which follows Benford's law by construction."""
        return round(float(10 ** self.rng.uniform(lo, hi)), 2)

    def iban(self) -> str:
        return "ZZ" + "".join(str(int(x)) for x in self.rng.integers(0, 10, 18))

    def business_day(self, lo: int = 0, hi: int = 364) -> date:
        while True:
            d = _day(self.rng.integers(lo, hi + 1))
            if _is_business_day(d):
                return d

    # -- people and access -----------------------------------------------------------------
    def build_people(self) -> None:
        rng = self.rng
        n = 160
        emp_ids = [f"E{i + 1:04d}" for i in range(n)]
        order = list(rng.permutation(n))
        past_leavers = set(order[:14])
        future_leavers = set(order[14:20])
        newbies = set(order[20:30])

        rows = []
        for i, eid in enumerate(emp_ids):
            hire = _day(-int(rng.integers(400, 4500)))
            leave = None
            if i in past_leavers:
                leave = _day(int(rng.integers(40, 350)))
            elif i in future_leavers:
                leave = date(2026, int(rng.integers(1, 7)), int(rng.integers(1, 28)))
            elif i in newbies:
                hire = _day(int(rng.integers(30, 330)))
            rows.append((eid, self.pick(_DEPARTMENTS), hire, leave))
        self.employees = pd.DataFrame(rows, columns=COLUMNS["employees"])

        eligible = [i for i in order if i not in past_leavers and i not in newbies]
        eligible_set = set(eligible)
        roles_of: dict[int, list[str]] = {}
        pos = 0
        for role, cnt in _ROLE_COUNTS.items():
            for i in eligible[pos : pos + cnt]:
                roles_of[i] = [role]
            pos += cnt
        for i in eligible[pos:]:
            roles_of[i] = ["VIEWER"]
        for i in newbies:
            roles_of[i] = ["VIEWER"]
        for i in sorted(past_leavers):
            roles_of[i] = [self.pick(["VIEWER", "AP_CLERK", "BUYER", "VIEWER"])]

        by_role: dict[str, list[int]] = {}
        for i in sorted(roles_of):
            by_role.setdefault(roles_of[i][0], []).append(i)

        # Injected: SoD conflicts (second role added to a distinct user per case).
        used: set[int] = set()
        sod_plan = [
            ("AP_CLERK", "PAYMENT_RELEASER", 3),
            ("BUYER", "PO_APPROVER", 3),
            ("AP_CLERK", "VENDOR_MASTER_ADMIN", 2),
            ("GL_APPROVER", "GL_POSTER", 2),
        ]
        sod_users = []
        for base, extra, cnt in sod_plan:
            pool = [i for i in by_role[base] if i not in used and i in eligible_set]
            for i in self.pick(pool, cnt):
                used.add(i)
                roles_of[i].append(extra)
                sod_users.append((i, base, extra))

        # Injected: dormant privileged accounts (single privileged role, long idle).
        dormant_pool = [
            i for r in ("SYS_ADMIN", "USER_ADMIN", "VENDOR_MASTER_ADMIN") for i in by_role[r] if i not in used
        ]
        dormant = set(self.pick(dormant_pool, 5))
        # Injected: leavers whose accounts are still active.
        active_leavers = set(self.pick(sorted(past_leavers), 5))

        privileged = {r for r, v in ROLES.items() if v[0]}
        users, urole = [], []
        for i, eid in enumerate(emp_ids):
            uid = f"U{i + 1:04d}"
            emp = self.employees.iloc[i]
            status, last = "ACTIVE", AS_OF - timedelta(days=int(rng.integers(0, 40)))
            if i in past_leavers:
                last = emp.leave_date - timedelta(days=int(rng.integers(0, 4)))
                if i in active_leavers:
                    if rng.random() < 0.5:
                        last = AS_OF - timedelta(days=int(rng.integers(1, 30)))
                    self.label("leaver_active_account", "user", uid, "leaver, account active")
                else:
                    status = "DISABLED"
            elif i in dormant:
                last = AS_OF - timedelta(days=int(rng.integers(110, 300)))
                self.label("dormant_privileged_account", "user", uid, "privileged, idle >90d")
            elif not (set(roles_of[i]) & privileged) and rng.random() < 0.08:
                last = AS_OF - timedelta(days=int(rng.integers(100, 400)))  # benign idle viewer
            created = max(emp.hire_date, date(2012, 1, 1))
            users.append((uid, eid, status, created, last))
            urole += [(uid, r) for r in roles_of[i]]
        for idx, base, extra in sod_users:
            self.label("sod_conflict", "user", f"U{idx + 1:04d}", f"{base}+{extra}")
        for k in range(3):
            uid = f"U{n + k + 1:04d}"
            users.append((uid, None, "ACTIVE", date(2020, 1, 1), AS_OF - timedelta(days=k)))
            urole.append((uid, "SYS_ADMIN"))
        self.users = pd.DataFrame(users, columns=COLUMNS["user_accounts"])
        self.user_roles = pd.DataFrame(urole, columns=COLUMNS["user_roles"])

        def uids(role: str) -> list[str]:
            u = self.user_roles[self.user_roles.role == role].user_id
            act = set(self.users[self.users.status == "ACTIVE"].user_id)
            gone = {f"U{i + 1:04d}" for i in past_leavers}
            return [x for x in u if x in act and x not in gone]

        self.buyers, self.po_approvers = uids("BUYER"), uids("PO_APPROVER")
        self.posters = uids("GL_POSTER")
        self.vma = uids("VENDOR_MASTER_ADMIN")
        posters = set(self.user_roles[self.user_roles.role == "GL_POSTER"].user_id)
        non_post = self.user_roles[~self.user_roles.user_id.isin(posters)]
        cand = set(non_post[non_post.role.isin(["AP_CLERK", "BUYER", "VIEWER"])].user_id)
        gone = {f"U{i + 1:04d}" for i in past_leavers}
        self.non_posters = sorted(cand - gone)

        self.roles = pd.DataFrame([(r, v[0], v[1]) for r, v in ROLES.items()], columns=COLUMNS["roles"])
        self.role_permissions = pd.DataFrame(
            [(r, p) for r, v in ROLES.items() for p in v[2]], columns=COLUMNS["role_permissions"]
        )
        self.sod = pd.DataFrame(SOD_PAIRS, columns=COLUMNS["sod_matrix"])

    # -- vendors, purchasing, invoices, payments ------------------------------------------
    def build_vendors(self) -> None:
        rng = self.rng
        combos = rng.choice(len(_WORD_A) * len(_WORD_B), size=128, replace=False)
        rows = []
        for j, c in enumerate(combos):
            name = f"{_WORD_A[c // len(_WORD_B)]} {_WORD_B[c % len(_WORD_B)]} {self.pick(_SUFFIXES)}"
            rows.append(
                {
                    "vendor_id": f"V{j + 1:04d}",
                    "name": name,
                    "country": self.pick(_COUNTRIES),
                    "tax_id": "TX" + "".join(str(int(x)) for x in rng.integers(0, 10, 9)),
                    "iban0": self.iban(),
                    "created_date": _day(-int(rng.integers(200, 3500))),
                }
            )
        self.n_base = 120
        # Fuzzy-duplicate vendor masters: same supplier registered twice under a name variant.
        self.variant_of: dict[str, str] = {}
        for k in range(8):
            base = rows[int(rng.integers(0, self.n_base))]
            suffix = base["name"].rsplit(" ", 1)[1]
            stem = base["name"].rsplit(" ", 1)[0]
            alt = self.pick(_VARIANT_SUFFIX[suffix])
            name = f"{stem} {alt}"
            if k % 3 == 2:
                name = name.upper()
            if k % 4 == 3:
                name = name.replace(" ", "-", 1)
            vid = f"V{len(rows) + 1:04d}"
            rows.append(
                {
                    "vendor_id": vid,
                    "name": name,
                    "country": base["country"],
                    "tax_id": base["tax_id"],
                    "iban0": self.iban(),
                    "created_date": _day(int(rng.integers(0, 200))),
                }
            )
            self.variant_of[vid] = base["vendor_id"]
        self.benford_vendor = f"V{len(rows) + 1:04d}"
        rows.append(
            {
                "vendor_id": self.benford_vendor,
                "name": "Zephyr Consulting Ltd",
                "country": "GB",
                "tax_id": "TX" + "".join(str(int(x)) for x in rng.integers(0, 10, 9)),
                "iban0": self.iban(),
                "created_date": _day(-int(rng.integers(200, 900))),
            }
        )
        self.vendors = pd.DataFrame(rows)
        w = rng.dirichlet(np.full(self.n_base, 0.6))
        self.vendor_weights = w
        self.base_vendor_ids = list(self.vendors.vendor_id[: self.n_base])

    def build_purchasing(self) -> None:
        rng = self.rng
        pos = _Table("PO", "po_id", "po_date")
        self.pos = pos
        invoices = _Table("INV", "invoice_id", "invoice_date")
        self.invoices = invoices
        self.invoice_labels: list[tuple[str, int, str]] = []
        self.po_labels: list[tuple[str, int, str]] = []

        def vendor() -> str:
            return str(rng.choice(self.base_vendor_ids, p=self.vendor_weights))

        def add_po(vid, d, amt, req, approver=None) -> int:
            return pos.add(vendor_id=vid, po_date=d, amount=amt, requester_id=req, approver_id=approver)

        # Background POs, 85% of which are invoiced 3-30 days later.
        po_rows = []
        for _ in range(4000):
            d = _day(rng.integers(0, 334))
            amt = self.amount()
            appr = self.pick(self.po_approvers) if amt >= APPROVAL_LIMIT else None
            k = add_po(vendor(), d, amt, self.pick(self.buyers), appr)
            po_rows.append((k, d, amt, rng.random() < 0.85))
        # Decoys: legitimate repeat purchases just under the limit (rule fires, not a split).
        for _ in range(4):
            vid, req, d = vendor(), self.pick(self.buyers), _day(rng.integers(0, 320))
            for off in (0, int(rng.integers(1, 4))):
                amt = round(float(rng.uniform(0.75, 0.97) * APPROVAL_LIMIT), 2)
                k = add_po(vid, d + timedelta(days=off), amt, req)
                po_rows.append((k, d + timedelta(days=off), amt, True))
        # Injected splits.
        for g in range(18):
            vid, req, d = vendor(), self.pick(self.buyers), _day(rng.integers(0, 310))
            hard = g >= 16  # spaced 9+ days apart, beyond the 7-day window
            cnt = int(rng.integers(2, 5))
            off = 0
            members = []
            for _ in range(cnt):
                amt = round(float(rng.uniform(0.72, 0.99) * APPROVAL_LIMIT), 2)
                k = add_po(vid, d + timedelta(days=off), amt, req)
                po_rows.append((k, d + timedelta(days=off), amt, True))
                members.append(k)
                off += int(rng.integers(9, 12)) if hard else int(rng.integers(0, 4))
            for k in members:
                self.po_labels.append(("split_purchase", k, f"split group {g + 1}"))
        self.po_rows = po_rows

        def add_inv(vid, d, amt, po_k, lag=None, number=None) -> int:
            return invoices.add(
                vendor_id=vid,
                invoice_number=number or f"INV-{int(rng.integers(100000, 999999))}",
                invoice_date=d,
                amount=amt,
                po_k=po_k,
                pay_lag=int(rng.integers(15, 46)) if lag is None else lag,
            )

        self.pos_df = pos.finalize()
        for k, d, amt, invoiced in po_rows:
            if invoiced:
                add_inv(pos.rows[k]["vendor_id"], d + timedelta(days=int(rng.integers(3, 31))), amt, k)

        # Invoices without a PO (utilities, fees) from base vendors.
        for _ in range(700):
            add_inv(vendor(), _day(rng.integers(0, 355)), self.amount(), None)

        # Benford-violating vendor: fabricated-looking amounts, uniform over 1,000-6,900.
        for _ in range(90):
            add_inv(
                self.benford_vendor,
                _day(rng.integers(0, 355)),
                round(float(rng.uniform(1000, 6900)), 2),
                None,
            )
        self.label("benford_vendor", "vendor", self.benford_vendor, "uniform fabricated amounts")

        # Exact duplicates: same vendor, number, amount re-submitted 1-15 days later.
        orig_pool = [
            k
            for k, r in enumerate(invoices.rows)
            if r["invoice_date"] < _day(330) and r["vendor_id"] in self.base_vendor_ids
        ]
        fuzzy_used: set[int] = set()  # invoices already involved in a duplicate pair
        for k in self.pick(orig_pool, 25):
            fuzzy_used.add(k)
            r = invoices.rows[k]
            dk = add_inv(
                r["vendor_id"],
                r["invoice_date"] + timedelta(days=int(rng.integers(1, 16))),
                r["amount"],
                r["po_k"],
                number=r["invoice_number"],
            )
            fuzzy_used.add(dk)
            self.invoice_labels.append(("dup_invoice_exact", dk, f"copy of row {k}"))

        # Fuzzy duplicates: same amount, near date, other invoice number, vendor-name variant.
        variants = sorted(self.variant_of)
        for vid in variants:  # make sure each variant's base vendor has an invoice to copy
            base = self.variant_of[vid]
            if not any(r["vendor_id"] == base and r["invoice_date"] < _day(330) for r in invoices.rows):
                add_inv(base, _day(rng.integers(0, 320)), self.amount(), None)
        for n_i in range(24):
            vid = variants[n_i % len(variants)]
            cands = [
                k
                for k, r in enumerate(invoices.rows)
                if r["vendor_id"] == self.variant_of[vid] and r["invoice_date"] < _day(330)
            ]
            cands = [k for k in cands if k not in fuzzy_used]
            if not cands:  # every invoice of this supplier is taken: add a fresh original
                cands = [add_inv(self.variant_of[vid], _day(rng.integers(0, 320)), self.amount(), None)]
            k = self.pick(cands)
            fuzzy_used.add(k)
            r = invoices.rows[k]
            hard = n_i >= 20
            gap = int(rng.integers(9, 15)) if hard else int(rng.integers(1, 7))
            dk = add_inv(
                vid,
                r["invoice_date"] + timedelta(days=gap),
                r["amount"],
                None,
                number=r["invoice_number"].replace("INV-", "INV") + "A",
            )
            self.invoice_labels.append(("dup_invoice_fuzzy", dk, "variant vendor copy"))

        # Injected: invoice paid shortly after a bank-detail change.
        self.injected_changes = []
        pool = [v for v in self.base_vendor_ids]
        for n_i, vid in enumerate(self.pick(pool, 12, replace=False)):
            cd = _day(rng.integers(30, 320))
            hard = n_i >= 10  # payment 16-20 days later, outside the 14-day window
            lag_days = int(rng.integers(16, 21)) if hard else int(rng.integers(1, 13))
            idate = cd - timedelta(days=int(rng.integers(0, 2)))
            k = add_inv(
                vid,
                idate,
                round(float(rng.uniform(12_000, 120_000)), 2),
                None,
                lag=(cd - idate).days + lag_days,
            )
            self.injected_changes.append((vid, cd, k))

    def finalize_invoices_payments(self) -> None:
        rng = self.rng
        inv = self.invoices
        po_ids = self.pos.idmap
        for r in inv.rows:
            r["po_id"] = po_ids.get(r.pop("po_k"))
        inv_df = inv.finalize()
        lags = inv_df.pop("pay_lag")
        self.invoices_df = inv_df

        pays = _Table("PAY", "payment_id", "payment_date")
        self.pays = pays
        for (_, r), lag in zip(inv_df.iterrows(), lags, strict=True):
            pd_ = r.invoice_date + timedelta(days=int(lag))
            if pd_ <= AS_OF:
                pays.add(
                    invoice_id=r.invoice_id,
                    vendor_id=r.vendor_id,
                    payment_date=pd_,
                    amount=r.amount,
                    bank_iban=None,
                )

        # Bank changes: injected ones first, then benign ones that mostly avoid payments.
        iban0 = dict(zip(self.vendors.vendor_id, self.vendors.iban0, strict=True))
        changes: list[dict] = []
        injected_inv_ids = set()
        for vid, cd, k in self.injected_changes:
            injected_inv_ids.add(inv.idmap[k])
            changes.append({"vendor_id": vid, "change_date": cd, "injected": True})
        pay_dates: dict[str, list[date]] = {}
        for r in pays.rows:
            pay_dates.setdefault(r["vendor_id"], []).append(r["payment_date"])
        busy = {c["vendor_id"] for c in changes}
        for vid in self.pick([v for v in self.vendors.vendor_id if v not in busy], 14):
            for _ in range(40):
                cd = _day(rng.integers(0, 350))
                hit = any(0 <= (p - cd).days <= 14 for p in pay_dates.get(vid, []))
                if not hit or rng.random() < 0.15:
                    break
            changes.append({"vendor_id": vid, "change_date": cd, "injected": False})
        by_vendor: dict[str, list[dict]] = {}
        for c in sorted(changes, key=lambda c: c["change_date"]):
            by_vendor.setdefault(c["vendor_id"], []).append(c)
        for vid, lst in by_vendor.items():
            cur = iban0[vid]
            for c in lst:
                c["old_iban"], cur = cur, self.iban()
                c["new_iban"] = cur
                c["changed_by"] = self.pick(self.vma)
        ch_tbl = _Table("BC", "change_id", "change_date")
        for c in sorted(changes, key=lambda c: (c["change_date"], c["vendor_id"])):
            ch_tbl.add(
                vendor_id=c["vendor_id"],
                change_date=c["change_date"],
                old_iban=c["old_iban"],
                new_iban=c["new_iban"],
                changed_by=c["changed_by"],
            )
        self.bank_changes = ch_tbl.finalize()
        current = {vid: lst[-1]["new_iban"] for vid, lst in by_vendor.items()}
        self.vendors["bank_iban"] = [current.get(v, iban0[v]) for v in self.vendors.vendor_id]

        def iban_at(vid: str, d: date) -> str:
            cur = iban0[vid]
            for c in by_vendor.get(vid, []):
                if c["change_date"] <= d:
                    cur = c["new_iban"]
            return cur

        for r in pays.rows:
            r["bank_iban"] = iban_at(r["vendor_id"], r["payment_date"])
        self.payments_df = pays.finalize()
        for pid, iid in zip(self.payments_df.payment_id, self.payments_df.invoice_id, strict=True):
            if iid in injected_inv_ids:
                self.label("bank_change_payment", "payment", pid, "paid after bank change")

        for tid, k, note in self.invoice_labels:
            self.label(tid, "invoice", inv.idmap[k], note)
        for tid, k, note in self.po_labels:
            self.label(tid, "purchase_order", self.pos.idmap[k], note)

    # -- general ledger -------------------------------------------------------------------
    def build_gl(self) -> None:
        rng = self.rng
        gl = _Table("JE", "je_id", "posting_date")
        for r in self.invoices_df.itertuples():
            d = r.invoice_date + timedelta(days=1)
            gl.add(
                posting_date=d,
                debit_account=self.pick(_EXPENSE_ACCOUNTS),
                credit_account="2000",
                amount=r.amount,
                source="AUTO",
                posted_by="SYSTEM",
                description=f"Invoice {r.invoice_number}",
                reference=r.invoice_id,
            )
        for r in self.payments_df.itertuples():
            gl.add(
                posting_date=r.payment_date,
                debit_account="2000",
                credit_account="1000",
                amount=r.amount,
                source="AUTO",
                posted_by="SYSTEM",
                description="Supplier payment",
                reference=r.payment_id,
            )

        def manual(d, amt, poster, text=None, tag=None):
            k = gl.add(
                posting_date=d,
                debit_account=self.pick(_EXPENSE_ACCOUNTS + ["1200", "7100"]),
                credit_account=self.pick(["2000", "1200", "2200", "3000"]),
                amount=amt,
                source="MANUAL",
                posted_by=poster,
                description=text or self.pick(_JE_TEXT),
                reference="",
            )
            if tag:
                self.je_labels.append((tag[0], k, tag[1]))
            return k

        self.je_labels: list[tuple[str, int, str]] = []

        def plain_amount() -> float:
            a = self.amount(2.7, 5.5)
            return a + 0.37 if round(a * 100) % 100_000 == 0 else a

        for _ in range(1100):
            manual(self.business_day(), plain_amount(), self.pick(self.posters))
        for _ in range(22):  # round-amount entries
            m = 1000 if rng.random() < 0.9 else 500
            amt = float(int(rng.integers(5, 500)) * 1000 + (0 if m == 1000 else 500))
            manual(
                self.business_day(),
                amt,
                self.pick(self.posters),
                "Manual adjustment",
                ("je_round_amount", "round amount"),
            )
        for _ in range(4):  # benign round entries (rent accrual)
            manual(
                self.business_day(),
                float(int(rng.integers(2, 9)) * 10_000),
                self.pick(self.posters),
                "Rent accrual",
            )
        weekend_days = [_day(i) for i in range(365) if not _is_business_day(_day(i))]
        for _ in range(18):  # weekend/holiday entries
            manual(
                self.pick(weekend_days),
                plain_amount(),
                self.pick(self.posters),
                tag=("je_weekend_holiday", "posted on weekend/holiday"),
            )
        saturdays = [_day(i) for i in range(365) if _day(i).weekday() == 5]
        for _ in range(5):  # benign period-close entries on a Saturday
            manual(self.pick(saturdays), plain_amount(), self.pick(self.posters), "Period-close adjustment")
        for _ in range(15):  # unauthorized posters
            manual(
                self.business_day(),
                plain_amount(),
                self.pick(self.non_posters),
                tag=("je_unauthorized_poster", "poster lacks post_journal"),
            )
        df = gl.finalize()
        df["period"] = [d.strftime("%Y-%m") for d in df.posting_date]
        self.gl_df = df
        for tid, k, note in self.je_labels:
            self.label(tid, "journal_entry", gl.idmap[k], note)

    # -- assembly -------------------------------------------------------------------------
    def build(self) -> dict[str, pd.DataFrame]:
        self.build_people()
        self.build_vendors()
        self.build_purchasing()
        self.finalize_invoices_payments()
        self.build_gl()
        vendors = self.vendors.drop(columns="iban0")
        labels = pd.DataFrame(self.labels, columns=COLUMNS["anomaly_labels"])
        labels = labels.sort_values(["test_id", "entity_id"]).reset_index(drop=True)
        tables = {
            "vendors": vendors,
            "vendor_bank_changes": self.bank_changes,
            "purchase_orders": self.pos_df,
            "invoices": self.invoices_df,
            "payments": self.payments_df,
            "gl_journal": self.gl_df,
            "employees": self.employees,
            "user_accounts": self.users,
            "user_roles": self.user_roles,
            "roles": self.roles,
            "role_permissions": self.role_permissions,
            "sod_matrix": self.sod,
            "holidays": pd.DataFrame(HOLIDAYS, columns=COLUMNS["holidays"]),
            "anomaly_labels": labels,
        }
        return {name: df[COLUMNS[name]].reset_index(drop=True) for name, df in tables.items()}


def generate(seed: int = 42) -> dict[str, pd.DataFrame]:
    """Return all tables for the given seed. Same seed gives identical tables."""
    return _Generator(seed).build()


def write_dataset(tables: dict[str, pd.DataFrame], out_dir: str | Path) -> list[Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, df in tables.items():
        p = out / f"{name}.csv"
        df.to_csv(p, index=False, lineterminator="\n")
        paths.append(p)
    return paths
