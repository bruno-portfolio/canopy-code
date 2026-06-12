from __future__ import annotations

from canopy.score import compute_score, grade, risk_index, score_factors


class TestScoreFactors:
    def test_clean_module_no_factors(self):
        factors = score_factors(funcs=4, n_cc_over=0, cc_max=1, dead=0, coverage=None)
        assert factors == ()
        assert compute_score(factors) == 100.0

    def test_complexity_spread_penalty(self):
        factors = score_factors(funcs=20, n_cc_over=4, cc_max=10, dead=0, coverage=None)
        assert len(factors) == 1
        assert factors[0].penalty == 30.0
        assert "4/20 functions CC>10" in factors[0].label

    def test_complexity_spread_capped_at_40(self):
        factors = score_factors(funcs=10, n_cc_over=9, cc_max=10, dead=0, coverage=None)
        assert factors[0].penalty == 40.0

    def test_worst_function_penalty(self):
        factors = score_factors(funcs=30, n_cc_over=1, cc_max=24, dead=0, coverage=None)
        worst = [f for f in factors if "worst function" in f.label]
        assert worst[0].penalty == 20.0

    def test_worst_function_below_threshold_no_penalty(self):
        factors = score_factors(funcs=10, n_cc_over=0, cc_max=9, dead=0, coverage=None)
        assert not any("worst function" in f.label for f in factors)

    def test_dead_ratio_penalty(self):
        factors = score_factors(funcs=20, n_cc_over=0, cc_max=5, dead=4, coverage=None)
        assert factors[0].penalty == 15.0

    def test_coverage_penalty(self):
        factors = score_factors(funcs=10, n_cc_over=0, cc_max=5, dead=0, coverage=0.6)
        assert factors[0].penalty == 10.0
        assert "coverage 60%" in factors[0].label

    def test_full_coverage_no_penalty(self):
        factors = score_factors(funcs=10, n_cc_over=0, cc_max=5, dead=0, coverage=1.0)
        assert factors == ()

    def test_no_coverage_data_no_penalty(self):
        factors = score_factors(funcs=10, n_cc_over=0, cc_max=5, dead=0, coverage=None)
        assert factors == ()

    def test_zero_funcs_no_division_error(self):
        factors = score_factors(funcs=0, n_cc_over=0, cc_max=0, dead=3, coverage=None)
        assert compute_score(factors) == 100.0


class TestComputeScore:
    def test_floor_at_zero(self):
        factors = score_factors(funcs=2, n_cc_over=2, cc_max=50, dead=10, coverage=0.0)
        assert compute_score(factors) == 0.0

    def test_constants_module_stays_green(self):
        factors = score_factors(funcs=4, n_cc_over=0, cc_max=1, dead=0, coverage=None)
        assert compute_score(factors) == 100.0

    def test_hidden_complex_function_drops_score(self):
        factors = score_factors(funcs=19, n_cc_over=3, cc_max=24, dead=0, coverage=None)
        score = compute_score(factors)
        assert score < 60.0


class TestRiskIndex:
    def test_high_churn_low_score_is_hotspot(self):
        assert risk_index(19, 19, 39.0) > 0.5

    def test_high_churn_healthy_code_near_zero(self):
        assert risk_index(18, 19, 100.0) == 0.0

    def test_no_churn_no_risk(self):
        assert risk_index(0, 19, 10.0) == 0.0

    def test_zero_max_churn_no_risk(self):
        assert risk_index(5, 0, 10.0) == 0.0

    def test_churn_outlier_does_not_flatten_others(self):
        # one healthy module with huge churn must not hide sick modules
        # with moderate churn: sqrt compression keeps them above threshold
        assert risk_index(8, 30, 35.0) > 0.2


class TestGrade:
    def test_boundaries(self):
        assert grade(100.0) == "A"
        assert grade(90.0) == "A"
        assert grade(89.9) == "B"
        assert grade(80.0) == "B"
        assert grade(70.0) == "C"
        assert grade(60.0) == "D"
        assert grade(59.9) == "F"
        assert grade(0.0) == "F"
