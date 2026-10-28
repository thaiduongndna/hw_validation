"""Transport-level tests use a loopback SCPI fixture, never physical hardware."""
from contextlib import contextmanager
from dataclasses import replace
import json
from pathlib import Path
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import unittest
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from hwval_demo.engine import Measurement, evaluate
from hwval_demo.scope import TekScope, ScopeError, number
from hwval_demo.service import acquire
from hwval_demo.workbook import load_spec, save_results, WorkbookError, NS

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "outputs/demo/spec_demo.xlsx"


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        values = {
            "MEAS1": ("MAXIMUM", "CH1", "V", "3.2", "3.3", "100"),
            "MEAS2": ("MINIMUM", "CH1", "V", "0.05", "0.5", "100"),
            "MEAS3": ("FREQUENCY", "CH2", "Hz", "999000", "1001000", "100"),
            "MEAS4": ("RISETIME", "CH2", "s", "9.91e37", "9.91e37", "100"),
        }
        for raw in self.rfile:
            command = raw.decode().strip()
            self.server.commands.append(command)
            response = None
            if command == "*IDN?":
                response = "TEKTRONIX,MSO64B,TEST_TRANSPORT_ONLY,CF:91.1CT FV:2.0"
            elif command == "HEADER?":
                response = ":HEADER 1"
            elif command == "MEASUREMENT:LIST?":
                response = '"MEAS1,MEAS2,MEAS3,MEAS4"'
            elif command == "ACQUIRE:STOPAFTER?":
                response = "RUNSTOP"
            elif command == "ACQUIRE:STATE?":
                response = "1" if self.server.stalled else "0"
            elif command == "*OPC?":
                response = "1"
            elif command.startswith("MEASUREMENT:"):
                tokens = command.split(":")
                slot = tokens[1]
                query = tokens[-1]
                offsets = {"TYPE?": 0, "SOURCE1?": 1, "YUNIT?": 2,
                           "MINIMUM?": 3, "MAXIMUM?": 4, "POPULATION?": 5}
                response = values[slot][offsets[query]]
            if response is not None:
                data = (response + "\n").encode()
                # Fragment responses so client cannot assume one recv == one reply.
                self.wfile.write(data[:2])
                self.wfile.flush()
                self.wfile.write(data[2:])
                self.wfile.flush()


class TestServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


@contextmanager
def scpi_server(stalled=False):
    server = TestServer(("127.0.0.1", 0), Handler)
    server.commands, server.stalled = [], stalled
    worker = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.02), daemon=True)
    worker.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def raw_cells(path, sheet_path="xl/worksheets/sheet1.xml"):
    with ZipFile(path) as archive:
        sheet = ET.fromstring(archive.read(sheet_path))
        return {cell.get("r"): ET.tostring(cell) for cell in sheet.iter(f"{{{NS}}}c")}


class ScopeWorkbookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="hwval-tests-")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "input.xlsx"
        shutil.copy2(SAMPLE, self.path)

    def test_real_socket_pipeline_and_xlsx_preservation(self):
        document = load_spec(self.path)
        before = raw_cells(self.path, document.sheet_path)
        with ZipFile(self.path) as z:
            before_members = {name: z.read(name) for name in z.namelist()}
        with scpi_server() as server:
            scope = TekScope("127.0.0.1", server.server_address[1], 2)
            scope.connect()
            run = acquire(document, {"GPIO-01": "MEAS1", "GPIO-02": "MEAS2",
                                     "SPI-01": "MEAS3", "I2C-01": "MEAS4"}, scope)
            scope.close()
            self.assertIn("HEADER 1", server.commands)
            first_measure = next(i for i, c in enumerate(server.commands) if ":RESULTS:" in c)
            self.assertLess(server.commands.index("ACQUIRE:STATE OFF"), first_measure)
            self.assertFalse(any("ALLACQ" in c for c in server.commands))
        self.assertEqual([r.status for r in run.results], ["PASS", "FAIL", "PASS", "INCONCLUSIVE"])
        save_results(document, run.results, run.run_id)
        self.assertEqual(load_spec(self.path).criteria, document.criteria)
        after = raw_cells(self.path, document.sheet_path)
        changed = {f"{col}{r.criterion.row}" for r in run.results for col in ("H", "I", "J", "K", "L")}
        for address, value in before.items():
            if address not in changed:
                self.assertEqual(after[address], value, address)
        self.assertIn(b"PASS", after["J7"])
        self.assertIn(b"FAIL", after["J8"])
        self.assertIn(b"0.999", after["H9"])
        self.assertIn(b"INCONCLUSIVE", after["J11"])
        self.assertEqual(len(list((self.path.parent / "backups").glob("*.xlsx"))), 1)
        with ZipFile(self.path) as z:
            for name, value in before_members.items():
                if name not in (document.sheet_path, "xl/styles.xml"):
                    self.assertEqual(z.read(name), value, name)
            self.assertIn(b"FFFEE2E2", z.read("xl/styles.xml"))
            self.assertIn(b"FFDCFCE7", z.read("xl/styles.xml"))

    def test_single_timeout_never_reads_old_results(self):
        with scpi_server(stalled=True) as server:
            scope = TekScope("127.0.0.1", server.server_address[1], 2)
            scope.connect()
            with self.assertRaisesRegex(ScopeError, "timeout"):
                acquire(load_spec(self.path), {"GPIO-01": "MEAS1"}, scope, single=True, acquisition_timeout=0.05)
            scope.close()
            self.assertFalse(any(":RESULTS:" in c for c in server.commands))
            self.assertIn("ACQUIRE:STATE OFF", server.commands)
            self.assertIn("ACQUIRE:STOPAFTER RUNSTOP", server.commands)

    def test_slot_changed_requires_reassignment(self):
        with scpi_server() as server:
            scope = TekScope("127.0.0.1", server.server_address[1], 2)
            scope.connect()
            original = replace(scope.measurements()[0], source="CH4")
            with self.assertRaisesRegex(ScopeError, "has changed"):
                acquire(load_spec(self.path), {"GPIO-01": "MEAS1"}, scope, expected={"GPIO-01": original})
            scope.close()

    def test_external_workbook_changes_are_not_overwritten(self):
        document = load_spec(self.path)
        result = evaluate(document.criteria[0], Measurement(3.2, 3.3, "V"))
        with self.path.open("ab") as stream:
            stream.write(b"external-change")
        changed = self.path.read_bytes()
        with self.assertRaises(WorkbookError):
            save_results(document, [result], "test")
        self.assertEqual(changed, self.path.read_bytes())

    def test_duplicate_or_mismatched_result_is_rejected(self):
        document = load_spec(self.path)
        result = evaluate(document.criteria[0], Measurement(3.2, 3.3, "V"))
        for results in ([result, result], [replace(result, criterion=replace(result.criterion, row=8))]):
            with self.assertRaises(WorkbookError):
                save_results(document, results, "test")

    def test_sentinels_and_nonfinite_are_invalid(self):
        for raw in ("9.91e37", "nan", "inf", "-9.91e37", '"invalid"'):
            with self.subTest(raw=raw), self.assertRaises(ScopeError):
                number(raw)

    def test_cli_reads_and_writes_using_loopback_transport(self):
        output = self.path.parent / "result.xlsx"
        with scpi_server() as server:
            command = [sys.executable, "-m", "hwval_demo", "run", "--host", "127.0.0.1", "--port", str(server.server_address[1]),
                       "--workbook", str(self.path), "--map", "GPIO-01=MEAS1", "--output", str(output)]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["counts"], {"PASS": 1})
        self.assertEqual(Path(payload["saved_workbook"]).resolve(), output.resolve())
        self.assertTrue(output.exists())
        self.assertTrue(Path(payload["log_path"]).exists())


if __name__ == "__main__":
    unittest.main()
