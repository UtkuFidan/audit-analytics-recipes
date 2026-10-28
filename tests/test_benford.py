import numpy as np

from audit_recipes import benford


def test_perfect_benford_conforms():
    s = benford.benford_stats(benford.EXPECTED * 100_000)
    assert s["mad"] < 1e-6 and s["conformity"] == "close conformity" and s["p_value"] > 0.99


def test_uniform_digits_rejected():
    s = benford.benford_stats(np.full(9, 500))
    assert s["conformity"] == "nonconformity" and s["p_value"] < 1e-6


def test_first_digit_counts():
    c = benford.first_digit_counts([1.5, 1000, 0.023, 9.99, 0, -5, 1999.99])
    assert c.tolist() == [3, 1, 0, 0, 0, 0, 0, 0, 1]
