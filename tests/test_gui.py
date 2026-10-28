"""Exercise our own Tk widgets and background workflow against a test server."""
from pathlib import Path
import shutil
import tempfile
import time
import tkinter as tk
import unittest

from hwval_demo.gui import DemoApp
from test_scope_workbook import SAMPLE, scpi_server


class GuiTests(unittest.TestCase):
    def test_connect_map_read_save(self):
        with tempfile.TemporaryDirectory(prefix="hwval-gui-") as folder:
            spec = Path(folder) / "gui.xlsx"
            shutil.copy2(SAMPLE, spec)
            root = tk.Tk()
            root.withdraw()
            app = DemoApp(root)
            app.load_file(spec)
            def wait_for_job():
                deadline = time.monotonic() + 8
                while app.busy and time.monotonic() < deadline:
                    root.update()
                    time.sleep(0.01)
                self.assertFalse(app.busy, "GUI worker did not finish")
            try:
                with scpi_server() as server:
                    app.host.set("127.0.0.1")
                    app.port.set(str(server.server_address[1]))
                    app.connect()
                    wait_for_job()
                    self.assertEqual(len(app.definitions), 4)
                    app.table.selection_set("GPIO-01")
                    app.combo.current(0)
                    app.assign()
                    app.read()
                    wait_for_job()
                    self.assertEqual(app.run.results[0].status, "PASS")
                    self.assertIn("SAVED TO EXCEL", app.summary.get())
                    self.assertTrue(list((Path(folder) / "backups").glob("*.xlsx")))
            finally:
                app.close()


if __name__ == "__main__":
    unittest.main()
