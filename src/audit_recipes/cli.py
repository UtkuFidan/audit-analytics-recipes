"""Command line interface: generate, run, evaluate, benford."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from . import benford, tests_catalog
from .synthetic import generate, write_dataset


def _cmd_generate(a) -> None:
    paths = write_dataset(generate(a.seed), a.out)
    size = sum(p.stat().st_size for p in paths) / 1e6
    print(f"wrote {len(paths)} files ({size:.2f} MB) to {a.out}")


def _cmd_run(a) -> None:
    findings = tests_catalog.run_all(a.data)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    findings.to_csv(a.out, index=False)
    print(findings.groupby("test_id").size().to_string())
    print(f"wrote {len(findings)} findings to {a.out}")


def _cmd_evaluate(a) -> None:
    findings = tests_catalog.run_all(a.data)
    labels = pd.read_csv(Path(a.data) / "anomaly_labels.csv")
    result = tests_catalog.evaluate(findings, labels)
    print(tests_catalog.to_markdown(result) if a.markdown else result.to_string(index=False))


def _cmd_benford(a) -> None:
    con = tests_catalog.connect(a.data)
    counts = benford.vendor_digit_counts(con)
    total = counts.groupby("digit")["n"].sum().reindex(range(1, 10), fill_value=0).to_numpy()
    panels = [("All invoices", total)]
    flagged = benford.flag_vendors(con).sort_values("mad", ascending=False)
    for vendor_id in flagged["entity_id"]:
        g = counts[counts.vendor_id == vendor_id].set_index("digit")["n"]
        counts_v = g.reindex(range(1, 10), fill_value=0).to_numpy()
        panels.append((f"Vendor {vendor_id} (flagged)", counts_v))
    for title, c in panels:
        s = benford.benford_stats(c)
        print(
            f"{title}: n={s['n']} chi2={s['chi_square']:.1f} p={s['p_value']:.3g} "
            f"MAD={s['mad']:.4f} ({s['conformity']})"
        )
    print(f"wrote {benford.plot_benford(panels[:2], a.out)}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="audit-recipes", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate", help="write the synthetic dataset as CSV")
    g.add_argument("--seed", type=int, default=42)
    g.add_argument("--out", default="data/")
    g.set_defaults(fn=_cmd_generate)
    r = sub.add_parser("run", help="run every test and write a findings table")
    r.add_argument("--data", default="data/")
    r.add_argument("--out", default="output/findings.csv")
    r.set_defaults(fn=_cmd_run)
    e = sub.add_parser("evaluate", help="precision and recall per test against injected labels")
    e.add_argument("--data", default="data/")
    e.add_argument("--markdown", action="store_true")
    e.set_defaults(fn=_cmd_evaluate)
    b = sub.add_parser("benford", help="Benford first-digit analysis and chart")
    b.add_argument("--data", default="data/")
    b.add_argument("--out", default="docs/benford_invoices.png")
    b.set_defaults(fn=_cmd_benford)
    a = p.parse_args(argv)
    a.fn(a)
