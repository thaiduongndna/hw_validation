"""A small native Tkinter GUI. Hardware work runs off the UI thread."""
from collections import Counter
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .scope import TekScope
from .service import acquire, save_run_log
from .workbook import load_spec, save_results

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "outputs" / "demo" / "spec_demo.xlsx"


def fmt(value):
    return "—" if value is None else f"{value:.9g}"


class DemoApp:
    def __init__(self, root):
        self.root = root
        root.title("TekScope → Excel | MSO6B demo")
        root.geometry("1260x820")
        root.minsize(1060, 700)
        root.configure(bg="#f3f6fb")
        self.scope = None
        self.document = None
        self.definitions = []
        self.mapping = {}
        self.run = None
        self.busy = False
        self.tasks = queue.Queue()
        self.controls = []
        self.host = tk.StringVar()
        self.port = tk.StringVar(value="4000")
        self.connection = tk.StringVar(value="Not connected · Enter the scope IP")
        self.file_path = tk.StringVar()
        self.choice = tk.StringVar()
        self.single = tk.BooleanVar(value=False)
        self.autosave = tk.BooleanVar(value=True)
        self.summary = tk.StringVar(value="Open a specification → connect the scope → assign measurements → read & evaluate")
        self._style()
        self._layout()
        if SAMPLE.exists():
            self.load_file(SAMPLE)
        root.after(80, self._poll)
        root.protocol("WM_DELETE_WINDOW", self.close)

    def _style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#f3f6fb")
        style.configure("TLabel", background="#f3f6fb", foreground="#1e293b", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10), padding=(12, 7))
        style.configure("Accent.TButton", background="#2563eb", foreground="white")
        style.map("Accent.TButton", background=[("active", "#1d4ed8"), ("disabled", "#94a3b8")])
        style.configure("TCheckbutton", background="#f3f6fb", font=("Segoe UI", 10))
        style.configure("Treeview", rowheight=33, font=("Segoe UI", 10), background="white", fieldbackground="white")
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), background="#e2e8f0", padding=(4, 8))

    def button(self, parent, text, command, **kwargs):
        button = ttk.Button(parent, text=text, command=command, **kwargs)
        self.controls.append(button)
        return button

    def _layout(self):
        header = tk.Frame(self.root, bg="#10243a", padx=24, pady=18)
        header.pack(fill="x")
        tk.Label(header, text="TekScope  →  Excel", font=("Segoe UI", 23, "bold"), bg="#10243a", fg="white").pack(anchor="w")
        tk.Label(header, text="MSO64B / MSO66B  •  Native measurements  •  Specification → PASS / FAIL",
                 font=("Segoe UI", 10), bg="#10243a", fg="#b8d0e7").pack(anchor="w", pady=(4, 0))
        body = ttk.Frame(self.root, padding=(20, 14))
        body.pack(fill="both", expand=True)
        connect = ttk.Frame(body)
        connect.pack(fill="x")
        ttk.Label(connect, text="Scope IP / hostname").pack(side="left")
        host = ttk.Entry(connect, textvariable=self.host, width=24)
        host.pack(side="left", padx=(10, 16))
        ttk.Label(connect, text="Port").pack(side="left")
        port = ttk.Entry(connect, textvariable=self.port, width=7)
        port.pack(side="left", padx=(8, 16))
        self.controls.extend([host, port])
        self.button(connect, "Connect / refresh", self.connect).pack(side="left")
        ttk.Label(connect, textvariable=self.connection, foreground="#52647a").pack(side="left", padx=14)
        ttk.Label(body, text="LAN SCPI: enable Socket Server with protocol None. Configure channels, thresholds and measurements on the scope.",
                  foreground="#64748b").pack(anchor="w", pady=(6, 12))
        files = ttk.Frame(body)
        files.pack(fill="x")
        ttk.Label(files, text="Excel specification").pack(side="left")
        ttk.Entry(files, textvariable=self.file_path, state="readonly").pack(side="left", fill="x", expand=True, padx=10)
        self.button(files, "Open Excel…", self.browse).pack(side="left")
        self.button(files, "Load sample", lambda: self.load_file(SAMPLE)).pack(side="left", padx=(8, 0))
        ttk.Label(body, text="Sample limits are illustrative. Replace them with your component specifications before evaluating hardware.",
                  foreground="#996018").pack(anchor="w", pady=(7, 12))
        columns = ("id", "signal", "parameter", "min", "max", "unit", "slot", "measured_min", "measured_max", "status")
        area = ttk.Frame(body)
        area.pack(fill="both", expand=True)
        self.table = ttk.Treeview(area, columns=columns, show="headings", selectmode="browse", height=9)
        headings = ("Test ID", "Signal", "Parameter", "Spec Min", "Spec Max", "Unit", "Scope", "Measured Min", "Measured Max", "Result")
        widths = (95, 70, 160, 85, 85, 60, 75, 115, 115, 125)
        for column, title, width in zip(columns, headings, widths):
            self.table.heading(column, text=title)
            self.table.column(column, width=width, minwidth=50, anchor="w" if column in ("id", "signal", "parameter", "status") else "center")
        scroll = ttk.Scrollbar(area, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scroll.set)
        self.table.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        for status, bg, fg in [("PASS", "#e9f8ed", "#166534"), ("FAIL", "#ffeded", "#991b1b"),
                               ("INCONCLUSIVE", "#fff7df", "#92400e"), ("SPEC ERROR", "#fff7df", "#92400e")]:
            self.table.tag_configure(status, background=bg, foreground=fg)
        self.table.bind("<<TreeviewSelect>>", self.row_selected)
        mapping = ttk.Frame(body)
        mapping.pack(fill="x", pady=12)
        ttk.Label(mapping, text="Scope measurement").pack(side="left")
        self.combo = ttk.Combobox(mapping, textvariable=self.choice, state="readonly", width=44)
        self.combo.pack(side="left", padx=10)
        self.button(mapping, "Assign to selected row", self.assign).pack(side="left")
        self.button(mapping, "Unassign", self.unassign).pack(side="left", padx=8)
        actions = ttk.Frame(body)
        actions.pack(fill="x", pady=(0, 10))
        single = ttk.Checkbutton(actions, text="New single capture (trigger timeout: 15 s)", variable=self.single)
        single.pack(side="left")
        autosave = ttk.Checkbutton(actions, text="Auto-save results to Excel", variable=self.autosave)
        autosave.pack(side="left", padx=15)
        self.controls.extend([single, autosave])
        self.button(actions, "Read & evaluate", self.read, style="Accent.TButton").pack(side="right")
        self.button(actions, "Save Excel…", self.save_as).pack(side="right", padx=8)
        ttk.Label(body, textvariable=self.summary, font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 8))
        self.logbox = tk.Text(body, height=6, font=("Consolas", 9), bg="#10243a", fg="#d9e6f2",
                              relief="flat", padx=12, pady=8, wrap="word", state="disabled")
        self.logbox.pack(fill="x")
        self.log("Reading stops the scope so all measurements use the same acquisition.")

    def log(self, text):
        self.logbox.configure(state="normal")
        self.logbox.insert("end", str(text) + "\n")
        self.logbox.see("end")
        self.logbox.configure(state="disabled")

    def work(self, operation, done):
        if self.busy:
            return
        self.busy = True
        for item in self.controls:
            item.configure(state="disabled")
        self.combo.configure(state="disabled")
        def worker():
            try:
                self.tasks.put((done, operation(), None))
            except Exception as exc:
                self.tasks.put((done, None, exc))
        threading.Thread(target=worker, daemon=True).start()

    def _poll(self):
        try:
            done, value, error = self.tasks.get_nowait()
        except queue.Empty:
            pass
        else:
            self.busy = False
            for item in self.controls:
                item.configure(state="normal")
            self.combo.configure(state="readonly")
            if error:
                self.log("ERROR: " + str(error))
                self.summary.set("Operation failed — see the details below.")
                messagebox.showerror("Operation failed", str(error), parent=self.root)
            else:
                done(value)
            if self.scope and not self.scope.sock:
                self.connection.set("Connection lost — reconnect before reading")
        self.root.after(80, self._poll)

    def load_file(self, path):
        if self.busy:
            return
        try:
            document = load_spec(path)
        except Exception as exc:
            messagebox.showerror("Unable to open Excel", str(exc), parent=self.root)
            return
        self.document, self.mapping, self.run = document, {}, None
        self.file_path.set(str(document.path))
        self.refresh()
        self.summary.set(f"Loaded {len(document.criteria)} specification rows · Select a row and assign a scope measurement")
        self.log(f"Excel: {document.sheet} | {document.path}")

    def browse(self):
        filename = filedialog.askopenfilename(title="Open Excel specification", filetypes=[("Excel workbook", "*.xlsx")], parent=self.root)
        if filename:
            self.load_file(filename)

    def refresh(self):
        selected = self.table.selection()
        self.table.delete(*self.table.get_children())
        results = {r.criterion.test_id: r for r in self.run.results} if self.run else {}
        for c in self.document.criteria:
            result = results.get(c.test_id)
            m = result.measurement if result else None
            status = result.status if result else "NOT RUN"
            definition = self.mapping.get(c.test_id)
            self.table.insert("", "end", iid=c.test_id,
                              values=(c.test_id, c.signal, c.parameter, fmt(c.spec_min), fmt(c.spec_max), c.unit,
                                      definition.slot if definition else "—", fmt(m.minimum) if m else "—",
                                      fmt(m.maximum) if m else "—", status), tags=(status,))
        if selected and self.table.exists(selected[0]):
            self.table.selection_set(selected[0])

    def connect(self):
        try:
            host, port = self.host.get(), int(self.port.get())
            candidate = TekScope(host, port)
        except Exception as exc:
            messagebox.showerror("Scope address", str(exc), parent=self.root)
            return
        self.connection.set("Connecting…")
        self.log(f"Connecting to {host}:{port}")
        def operation():
            if self.scope:
                self.scope.close()
            try:
                candidate.connect()
                definitions = candidate.measurements()
                return candidate, definitions
            except Exception:
                candidate.close()
                raise
        def done(value):
            self.scope, self.definitions = value
            self.mapping, self.run = {}, None
            self.connection.set(self.scope.identity)
            labels = [f"{d.slot}  ·  {d.kind}  ·  {d.source}  ·  {d.unit}" for d in self.definitions]
            self.combo.configure(values=labels)
            self.choice.set(labels[0] if labels else "")
            if self.document:
                self.refresh()
            self.log(f"Connected: {self.scope.identity}; {len(labels)} measurements.")
            if not labels:
                self.log("No measurements found. Add measurements on the scope, then click Connect / refresh.")
        self.work(operation, done)

    def row_selected(self, _event=None):
        selected = self.table.selection()
        if selected and self.run:
            result = next((r for r in self.run.results if r.criterion.test_id == selected[0]), None)
            if result:
                self.log(f"{selected[0]}: {result.note}")

    def assign(self):
        selected = self.table.selection()
        index = self.combo.current()
        if not selected or index < 0:
            messagebox.showinfo("Assign measurement", "Select a specification row and a scope measurement.", parent=self.root)
            return
        self.mapping[selected[0]] = self.definitions[index]
        self.run = None
        self.refresh()
        self.log(f"{selected[0]} ← {self.definitions[index].slot}")

    def unassign(self):
        selected = self.table.selection()
        if selected:
            self.mapping.pop(selected[0], None)
            self.run = None
            self.refresh()

    def read(self):
        if not self.document or not self.scope or not self.scope.sock or not self.mapping:
            messagebox.showinfo("Setup incomplete", "Open an Excel file, connect the scope and assign at least one measurement.", parent=self.root)
            return
        document, scope, mapping = self.document, self.scope, dict(self.mapping)
        single, autosave = self.single.get(), self.autosave.get()
        self.run = None
        self.refresh()
        self.summary.set("Reading scope measurements…")
        def operation():
            run = acquire(document, {tid: d.slot for tid, d in mapping.items()}, scope,
                          single=single, expected=mapping)
            save_run_log(run, scope, document.path.parent)
            saved, error = None, None
            if autosave:
                try:
                    saved = save_results(document, run.results, run.run_id)
                except Exception as exc:
                    error = str(exc)
            return run, saved, error
        def done(value):
            self.run, saved, error = value
            self.refresh()
            counts = Counter(r.status for r in self.run.results)
            detail = " · ".join(f"{count} {status}" for status, count in counts.items())
            self.summary.set(detail + (" · SAVED TO EXCEL" if saved else " · NOT SAVED TO EXCEL"))
            self.log("Run: " + self.run.run_id + " | " + detail)
            self.log("SCPI log: " + str(self.run.log_path))
            if saved:
                self.log("Updated the assigned rows in: " + str(saved))
                self.log("The previous workbook is saved in the backups/ folder.")
            if error:
                self.log("Save error: " + error)
                messagebox.showwarning("Measurements read, but Excel was not saved", error + "\nClose Excel or choose Save Excel… to save a new copy.", parent=self.root)
        self.work(operation, done)

    def save_as(self):
        if not self.run:
            messagebox.showinfo("No results yet", "Read scope measurements before saving.", parent=self.root)
            return
        path = filedialog.asksaveasfilename(parent=self.root, title="Save Excel results", defaultextension=".xlsx", filetypes=[("Excel workbook", "*.xlsx")],
                                          initialfile=f"validation_{self.run.run_id}.xlsx")
        if path:
            self.work(lambda: save_results(self.document, self.run.results, self.run.run_id, path),
                      lambda saved: (self.log("Saved: " + str(saved)), self.summary.set("SAVED TO EXCEL: " + str(saved))))

    def close(self):
        if self.busy:
            messagebox.showinfo("Communication in progress", "Wait for the operation to finish or time out before closing this window.", parent=self.root)
            return
        if self.scope:
            self.scope.close()
        self.root.destroy()


def launch():
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass
    root = tk.Tk()
    DemoApp(root)
    root.mainloop()
