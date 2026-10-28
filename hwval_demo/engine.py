"""Deterministic demo measurements and unit-aware criteria evaluation.

The simulator contains fixed fixtures. It never derives a measurement from a
user's limits, and it never communicates with real hardware.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
import math
from typing import Sequence


@dataclass(frozen=True)
class Criterion:
    test_id: str
    interface: str
    signal: str
    parameter: str
    spec_min: float | None
    spec_max: float | None
    unit: str
    row: int


@dataclass(frozen=True)
class Measurement:
    minimum: float | None
    maximum: float | None
    unit: str
    samples: int = 1


@dataclass(frozen=True)
class Result:
    criterion: Criterion
    measurement: Measurement | None
    status: str
    note: str


# Preserve unit case: MHz and mHz must never silently become interchangeable.
_UNITS: dict[str, tuple[str, Decimal]] = {
    "V": ("voltage", Decimal("1")),
    "mV": ("voltage", Decimal("0.001")),
    "uV": ("voltage", Decimal("0.000001")),
    "s": ("time", Decimal("1")),
    "ms": ("time", Decimal("0.001")),
    "us": ("time", Decimal("0.000001")),
    "ns": ("time", Decimal("0.000000001")),
    "ps": ("time", Decimal("0.000000000001")),
    "Hz": ("frequency", Decimal("1")),
    "kHz": ("frequency", Decimal("1000")),
    "MHz": ("frequency", Decimal("1000000")),
    "GHz": ("frequency", Decimal("1000000000")),
    "baud": ("baud", Decimal("1")),
    "kbaud": ("baud", Decimal("1000")),
    "Mbaud": ("baud", Decimal("1000000")),
    "%": ("percentage", Decimal("1")),
}


def _unit_info(unit: object) -> tuple[str, Decimal]:
    if not isinstance(unit, str):
        raise ValueError("Unit must be text.")
    normalized = unit.strip().replace("µ", "u").replace("μ", "u")
    try:
        return _UNITS[normalized]
    except KeyError as exc:
        raise ValueError(f"Unsupported unit: {unit!r}.") from exc


def _number(value: object, label: str) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError(f"{label} must be a numeric cell or blank.")
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"{label} is not a valid number.") from exc
    if not number.is_finite():
        raise ValueError(f"{label} must be finite.")
    return number


def _as_float(value: Decimal | None) -> float | None:
    if value is None:
        return None
    number = float(value)
    if not math.isfinite(number) or (value != 0 and number == 0):
        raise ValueError("Converted measurement is outside the supported numeric range.")
    return number


def evaluate(criterion: Criterion, measurement: Measurement | None) -> Result:
    """Evaluate inclusive min/max limits without rounding before comparison.

    Every available event must meet its applicable limit: the lower limit is
    checked against the measured minimum and the upper against the maximum.
    A valid observed violation is FAIL even if another required extremum is
    unavailable. Missing prerequisites alone never produce PASS or FAIL.
    """
    try:
        lower = _number(criterion.spec_min, "Spec Min")
        upper = _number(criterion.spec_max, "Spec Max")
        if lower is None and upper is None:
            raise ValueError("Missing both specification limits.")
        if lower is not None and upper is not None and lower > upper:
            raise ValueError("Spec Min is greater than Spec Max.")
        dimension, target_factor = _unit_info(criterion.unit)
    except ValueError as exc:
        return Result(criterion, None, "SPEC ERROR", str(exc))

    if measurement is None:
        return Result(criterion, None, "INCONCLUSIVE", "No measurement available.")

    try:
        if (
            isinstance(measurement.samples, bool)
            or not isinstance(measurement.samples, int)
            or measurement.samples <= 0
        ):
            raise ValueError("No valid samples; sample count must be a positive integer.")
        source_dimension, source_factor = _unit_info(measurement.unit)
        if source_dimension != dimension:
            raise ValueError(
                f"Incompatible units: {measurement.unit!r} and {criterion.unit!r}."
            )
        minimum = _number(measurement.minimum, "Measured Min")
        maximum = _number(measurement.maximum, "Measured Max")
        if minimum is None and maximum is None:
            raise ValueError("No measurement values available.")
        if minimum is not None and maximum is not None and minimum > maximum:
            raise ValueError("Measured Min is greater than Measured Max.")
        factor = source_factor / target_factor
        minimum = minimum * factor if minimum is not None else None
        maximum = maximum * factor if maximum is not None else None
        converted = Measurement(
            _as_float(minimum), _as_float(maximum), criterion.unit.strip(), measurement.samples
        )
    except (ValueError, OverflowError, InvalidOperation) as exc:
        return Result(criterion, None, "INCONCLUSIVE", str(exc))

    violations: list[str] = []
    missing: list[str] = []
    if lower is not None:
        if minimum is None:
            missing.append("measured minimum")
        elif minimum < lower:
            violations.append("Measured minimum is below Spec Min")
    if upper is not None:
        if maximum is None:
            missing.append("measured maximum")
        elif maximum > upper:
            violations.append("Measured maximum is above Spec Max")
    if violations:
        note = "; ".join(violations) + "."
        if missing:
            note += " Also missing " + " and ".join(missing) + "."
        return Result(criterion, converted, "FAIL", note)
    if missing:
        return Result(
            criterion, converted, "INCONCLUSIVE", "Missing " + " and ".join(missing) + "."
        )
    return Result(criterion, converted, "PASS", "All available extrema meet the limits.")


_PASS_FIXTURES = {
    "GPIO-01": Measurement(3.26, 3.34, "V", 100),
    "GPIO-02": Measurement(0.08, 0.22, "V", 100),
    "SPI-01": Measurement(999000, 1001000, "Hz", 256),
    "SPI-02": Measurement(0.012, 0.018, "us", 256),
    "I2C-01": Measurement(0.000000240, 0.000000280, "s", 128),
    "I2C-02": Measurement(1.35, 1.45, "us", 128),
    "UART-01": Measurement(115180, 115220, "baud", 64),
    "UART-02": Measurement(8.5, 8.8, "us", 64),
}

_FAIL_FIXTURES = {
    "GPIO-01": Measurement(2.2, 2.3, "V", 100),
    "GPIO-02": Measurement(0.45, 0.52, "V", 100),
    "SPI-01": Measurement(1150000, 1200000, "Hz", 256),
    "SPI-02": Measurement(7.8, 9.2, "ns", 256),
    "I2C-01": Measurement(310, 335, "ns", 128),
    "I2C-02": Measurement(1.15, 1.22, "us", 128),
    "UART-01": Measurement(110000, 112000, "baud", 64),
    "UART-02": Measurement(7.2, 7.8, "us", 64),
}

_MIXED_FIXTURES: dict[str, Measurement | None] = {
    **_PASS_FIXTURES,
    "GPIO-02": Measurement(0.08, 0.52, "V", 100),
    "SPI-02": Measurement(7.8, 18, "ns", 256),
    "I2C-01": Measurement(240, 335, "ns", 128),
    "UART-02": None,
}


def simulate(criteria: Sequence[Criterion], scenario: str = "mixed") -> list[Result]:
    """Evaluate deterministic, explicitly simulated fixtures.

    'pass' and 'fail' name fixture sets for the bundled example specification,
    not forced verdicts. Changing a spec changes the evaluation, not the data.
    Unknown Test IDs deliberately have no simulated measurement.
    """
    fixture_sets: dict[str, dict[str, Measurement | None]] = {
        "mixed": _MIXED_FIXTURES,
        "pass": _PASS_FIXTURES,
        "fail": _FAIL_FIXTURES,
        "missing": {},
    }
    if scenario not in fixture_sets:
        raise ValueError(f"Unknown scenario {scenario!r}; choose mixed, pass, fail, or missing.")
    fixtures = fixture_sets[scenario]
    results: list[Result] = []
    for criterion in criteria:
        result = evaluate(criterion, fixtures.get(criterion.test_id))
        reason = result.note
        if criterion.test_id not in _PASS_FIXTURES:
            reason += " No demo fixture exists for this Test ID."
        results.append(replace(result, note=f"SIMULATED: {reason}"))
    return results
