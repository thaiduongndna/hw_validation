import unittest
from dataclasses import replace
from decimal import Decimal

from hwval_demo.engine import Criterion, Measurement, evaluate, simulate


def criterion(lower=0.0, upper=1.0, unit="V", test_id="T-01"):
    return Criterion(test_id, "GPIO", "GPIO1", "Voltage", lower, upper, unit, 7)


def bundled_criteria():
    values = [
        ("GPIO-01", 2.4, None, "V"),
        ("GPIO-02", None, 0.4, "V"),
        ("SPI-01", 0.9, 1.1, "MHz"),
        ("SPI-02", 10, None, "ns"),
        ("I2C-01", None, 300, "ns"),
        ("I2C-02", 1300, None, "ns"),
        ("UART-01", 113000, 117000, "baud"),
        ("UART-02", 8, None, "us"),
    ]
    return [criterion(lo, hi, unit, test_id) for test_id, lo, hi, unit in values]


class EvaluationTests(unittest.TestCase):
    def test_inclusive_boundaries_and_no_rounding_tolerance(self):
        self.assertEqual(evaluate(criterion(), Measurement(0, 1, "V")).status, "PASS")
        self.assertEqual(
            evaluate(criterion(), Measurement(0, 1.0000000000000002, "V")).status, "FAIL"
        )
        self.assertEqual(
            evaluate(criterion(), Measurement(-0.0000000000000001, 1, "V")).status, "FAIL"
        )

    def test_unit_conversion_has_exact_decimal_comparison(self):
        result = evaluate(criterion(0.1, 0.3), Measurement(100, 300, "mV", 100))
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.measurement, Measurement(0.1, 0.3, "V", 100))
        self.assertEqual(
            evaluate(criterion(0.1, 0.3), Measurement(100, 300.0000000001, "mV")).status,
            "FAIL",
        )

    def test_micro_units_and_timing_conversion(self):
        for unit in ("us", "µs", "μs", " us "):
            with self.subTest(unit=unit):
                result = evaluate(criterion(10, 20, "ns"), Measurement(0.01, 0.02, unit))
                self.assertEqual(result.status, "PASS")
                self.assertEqual((result.measurement.minimum, result.measurement.maximum), (10, 20))

    def test_frequency_baud_and_percent_units(self):
        cases = [
            (criterion(0.9, 1.1, "MHz"), Measurement(999000, 1001000, "Hz")),
            (criterion(113000, 117000, "baud"), Measurement(115.2, 115.2, "kbaud")),
            (criterion(40, 60, "%"), Measurement(49, 51, "%")),
        ]
        for spec, measurement in cases:
            with self.subTest(unit=spec.unit):
                self.assertEqual(evaluate(spec, measurement).status, "PASS")

    def test_zero_limit_is_a_real_limit(self):
        spec = criterion(None, 0, "V")
        self.assertEqual(evaluate(spec, Measurement(-0.2, 0, "V")).status, "PASS")
        self.assertEqual(evaluate(spec, Measurement(0, 0.001, "V")).status, "FAIL")

    def test_one_sided_limits_and_partial_extrema(self):
        self.assertEqual(
            evaluate(criterion(None, 1), Measurement(None, 0.5, "V")).status, "PASS"
        )
        self.assertEqual(
            evaluate(criterion(0, None), Measurement(0.1, None, "V")).status, "PASS"
        )
        self.assertEqual(
            evaluate(criterion(0, 1), Measurement(None, 0.5, "V")).status, "INCONCLUSIVE"
        )
        self.assertEqual(
            evaluate(criterion(0, 1), Measurement(None, 1.5, "V")).status, "FAIL"
        )

    def test_spec_errors(self):
        specs = [
            criterion(None, None), criterion(2, 1), criterion(True, 1),
            criterion("0", 1), criterion(float("nan"), 1),
            criterion(0, float("inf")), criterion(0, 1, "banana"),
            criterion(0, 1, None),
        ]
        for spec in specs:
            with self.subTest(spec=spec):
                result = evaluate(spec, Measurement(0.1, 0.5, "V"))
                self.assertEqual(result.status, "SPEC ERROR")
                self.assertIsNone(result.measurement)

    def test_invalid_measurements_never_pass_or_fail(self):
        measurements = [
            None, Measurement(None, None, "V"), Measurement(float("nan"), 0.5, "V"),
            Measurement(0.1, float("inf"), "V"), Measurement(True, 0.5, "V"),
            Measurement("0.1", 0.5, "V"), Measurement(0.8, 0.2, "V"),
            Measurement(0.1, 0.5, "s"), Measurement(0.1, 0.5, "mHz"),
            Measurement(0.1, 0.5, "V", 0), Measurement(0.1, 0.5, "V", -1),
            Measurement(0.1, 0.5, "V", True), Measurement(0.1, 0.5, "V", 1.5),
        ]
        for measurement in measurements:
            with self.subTest(measurement=measurement):
                self.assertEqual(evaluate(criterion(), measurement).status, "INCONCLUSIVE")

    def test_numeric_overflow_or_underflow_is_not_silent(self):
        for value in (Decimal("1e1000"), Decimal("1e-1000")):
            with self.subTest(value=value):
                self.assertEqual(
                    evaluate(criterion(), Measurement(value, value, "V")).status,
                    "INCONCLUSIVE",
                )

    def test_violation_checks_extrema_not_average(self):
        result = evaluate(criterion(0, 1), Measurement(-0.01, 1.01, "V", 1000))
        self.assertEqual(result.status, "FAIL")
        self.assertIn("below Spec Min", result.note)
        self.assertIn("above Spec Max", result.note)


class SimulationTests(unittest.TestCase):
    def test_mixed_fixture_counts_and_order(self):
        results = simulate(bundled_criteria())
        self.assertEqual(
            [result.status for result in results],
            ["PASS", "FAIL", "PASS", "FAIL", "FAIL", "PASS", "PASS", "INCONCLUSIVE"],
        )
        self.assertTrue(all(result.note.startswith("SIMULATED:") for result in results))
        self.assertEqual(results[2].measurement.minimum, 0.999)

    def test_fixture_sets_and_missing_data(self):
        for scenario, status in (("pass", "PASS"), ("fail", "FAIL"), ("missing", "INCONCLUSIVE")):
            with self.subTest(scenario=scenario):
                self.assertTrue(all(r.status == status for r in simulate(bundled_criteria(), scenario)))

    def test_changing_spec_does_not_change_simulated_measurements(self):
        normal = bundled_criteria()[0]
        strict = replace(normal, spec_min=3.3)
        first = simulate([normal], "pass")[0]
        second = simulate([strict], "pass")[0]
        self.assertEqual(first.measurement, second.measurement)
        self.assertEqual(first.status, "PASS")
        self.assertEqual(second.status, "FAIL")

    def test_fixture_selection_uses_test_id_not_row_order(self):
        specs = bundled_criteria()
        forward = simulate(specs)
        reversed_results = simulate(list(reversed(specs)))
        self.assertEqual(forward, list(reversed(reversed_results)))

    def test_unknown_id_missing_fixture_and_invalid_scenario(self):
        result = simulate([criterion()])[0]
        self.assertEqual(result.status, "INCONCLUSIVE")
        self.assertIn("No demo fixture", result.note)
        with self.assertRaises(ValueError):
            simulate([], "random")


if __name__ == "__main__":
    unittest.main()
