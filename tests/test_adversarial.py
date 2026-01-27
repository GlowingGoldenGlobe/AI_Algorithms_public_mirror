import pytest

from module_adversarial_test import run_scenario


def test_adversarial_small_noise_validated_no_rollback():
    report = run_scenario("S1_small_noise", deterministic_mode=True)
    res = report["result"]
    assert res["rolled_back"] is False
    assert res["task_status"] == "validated"


def test_adversarial_large_outlier_needs_review():
    report = run_scenario("S2_large_outlier", deterministic_mode=True)
    res = report["result"]
    assert res["needs_review"] is True
    assert res["task_status"] == "needs_review"
    assert abs(float(res["record_value_after"]) - 10.0) < 1e-9


def test_adversarial_context_swap_misassociation():
    report = run_scenario("S3_context_swap", deterministic_mode=True)
    res = report["result"]
    assert res["mis_association"] is True


def test_adversarial_poisoned_retrieval_flagged():
    report = run_scenario("S4_poisoned_retrieval", deterministic_mode=True)
    res = report["result"]
    assert res["top_record_id"]
    assert res["flagged"] is True


def test_adversarial_rollback_storm_escalates():
    report = run_scenario("S5_rollback_storm", deterministic_mode=True)
    res = report["result"]
    assert res["escalation_action"] == "escalate"


def test_adversarial_counterfactual_negative_gain_re_evaluate():
    report = run_scenario("S6_counterfactual_negative_gain", deterministic_mode=True)
    res = report["result"]
    assert res["negative_gain"] is True
    assert res["re_evaluate"] is True


def test_adversarial_deterministic_repro():
    a = run_scenario("S1_small_noise", deterministic_mode=True)
    b = run_scenario("S1_small_noise", deterministic_mode=True)
    assert a == b
