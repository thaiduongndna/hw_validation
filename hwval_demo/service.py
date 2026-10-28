"""Shared scope-to-Excel workflow used by the GUI and CLI."""
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import json
from pathlib import Path
import uuid

from .engine import Result, evaluate
from .scope import NativeMeasurement, ScopeError, TekScope
from .workbook import SpecWorkbook


@dataclass
class Run:
    run_id: str
    results: list[Result]
    metadata: dict
    log_path: Path | None = None

    def as_dict(self):
        return {"run_id": self.run_id, "source": "scope_native", "scope": self.metadata,
                "results": [asdict(r) for r in self.results],
                "log_path": str(self.log_path) if self.log_path else None}


def acquire(document: SpecWorkbook, mapping: dict[str, str], scope: TekScope,
            single=False, acquisition_timeout=15,
            expected: dict[str, NativeMeasurement] | None = None) -> Run:
    by_id = {c.test_id: c for c in document.criteria}
    if not mapping:
        raise ValueError("Assign at least one Test ID to a scope measurement.")
    if set(mapping) - set(by_id):
        raise ValueError("The mapping contains a Test ID that is not present in the workbook.")
    for tid in mapping:
        preflight = evaluate(by_id[tid], None)
        if preflight.status == "SPEC ERROR":
            raise ValueError(f"{tid}: {preflight.note}")
    scope.freeze(single=single, acquisition_timeout=acquisition_timeout)
    definitions = {d.slot: d for d in scope.measurements()}
    if set(mapping.values()) - set(definitions):
        raise ScopeError("An assigned measurement no longer exists on the scope. Refresh the connection and assign it again.")
    if expected:
        for tid, previous in expected.items():
            if tid in mapping and definitions[mapping[tid]] != previous:
                raise ScopeError(f"{tid}: the measurement type, channel or unit has changed. Assign it again before reading.")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ_") + uuid.uuid4().hex[:8]
    results = []
    readings = {}
    for criterion in document.criteria:
        if criterion.test_id not in mapping:
            continue
        definition = definitions[mapping[criterion.test_id]]
        if definition.slot not in readings:
            try:
                readings[definition.slot] = (scope.read(definition), None)
            except ScopeError as exc:
                if scope.sock is None:
                    raise  # Broken transport invalidates the run; do not silently reuse data.
                readings[definition.slot] = (None, str(exc))
        measurement, error = readings[definition.slot]
        result = evaluate(criterion, measurement)
        prefix = f"REAL SCOPE | {definition.slot} {definition.kind} {definition.source} | CURRENTACQ"
        if measurement:
            prefix += f" | n={measurement.samples}"
        results.append(replace(result, note=prefix + " | " + (error or result.note)))
    metadata = {"identity": scope.identity, "host": scope.host, "port": scope.port,
                "acquisition": "new_single" if single else "existing_stopped",
                "measurement_scope": "CURRENTACQ", "spec_sha256": document.fingerprint,
                "workbook": str(document.path), "sheet": document.sheet,
                "mapping": mapping, "definitions": [asdict(definitions[s]) for s in sorted(set(mapping.values()))],
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "limitations": "Threshold/gating configured on scope; numeric criteria only."}
    return Run(run_id, results, metadata)


def save_run_log(run: Run, scope: TekScope, root: Path):
    folder = root / "runs" / run.run_id
    folder.mkdir(parents=True, exist_ok=False)
    run.log_path = folder / "scope_run.json"
    payload = run.as_dict()
    payload["scpi_log"] = scope.log
    run.log_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
