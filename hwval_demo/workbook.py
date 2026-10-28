"""Read a simple XLSX spec and patch only mapped output cells.

Uses the Python standard library. Unchanged ZIP members are copied byte-for-byte;
DOM editing preserves namespace declarations and unrelated worksheet content.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import math
import os
from pathlib import Path
import posixpath
import shutil
import tempfile
from xml.dom import minidom
from xml.etree import ElementTree as ET
from zipfile import ZipFile, BadZipFile

from .engine import Criterion, Result

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
HEADERS = ("Test ID", "Interface", "Signal", "Parameter", "Spec Min", "Spec Max",
           "Unit", "Measured Min", "Measured Max", "Result", "Note", "Run ID")


class WorkbookError(ValueError):
    pass


@dataclass
class SpecWorkbook:
    path: Path
    fingerprint: str
    sheet: str
    sheet_path: str
    columns: dict[str, str]
    criteria: list[Criterion]


def fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _cell_value(cell, shared):
    if cell.find(f"{{{NS}}}f") is not None:
        raise WorkbookError(f"Cell {cell.get('r')} contains a formula. This demo requires specification values entered as numbers.")
    kind = cell.get("t", "n")
    if kind == "inlineStr":
        return "".join(t.text or "" for t in cell.iter(f"{{{NS}}}t"))
    value = cell.find(f"{{{NS}}}v")
    if value is None or value.text is None:
        return None
    if kind == "s":
        return shared[int(value.text)]
    if kind in ("str", "e", "b"):
        return value.text
    try:
        return float(value.text)
    except ValueError:
        return value.text


def load_spec(path: str | Path, sheet_name: str | None = None) -> SpecWorkbook:
    path = Path(path).resolve()
    if path.suffix.lower() != ".xlsx":
        raise WorkbookError("This demo supports .xlsx files, not .xls or .xlsm.")
    original_fingerprint = fingerprint(path)
    try:
        with ZipFile(path) as archive:
            shared = []
            if "xl/sharedStrings.xml" in archive.namelist():
                root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
                shared = ["".join(t.text or "" for t in si.iter(f"{{{NS}}}t")) for si in root]
            relations = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
            targets = {r.get("Id"): r.get("Target") for r in relations}
            book = ET.fromstring(archive.read("xl/workbook.xml"))
            found = None
            for sheet in book.find(f"{{{NS}}}sheets"):
                if sheet_name and sheet.get("name") != sheet_name:
                    continue
                target = targets[sheet.get(f"{{{REL}}}id")]
                sheet_path = posixpath.normpath(target.lstrip("/") if target.startswith("/") else "xl/" + target)
                root = ET.fromstring(archive.read(sheet_path))
                rows = root.find(f"{{{NS}}}sheetData")
                for row in rows:
                    if int(row.get("r")) > 50:
                        break
                    values = {}
                    for cell in row:
                        if cell.find(f"{{{NS}}}f") is None:
                            value = _cell_value(cell, shared)
                            if isinstance(value, str):
                                values.setdefault(value.strip(), []).append(cell.get("r").rstrip("0123456789"))
                    if all(header in values for header in HEADERS):
                        if any(len(values[header]) != 1 for header in HEADERS):
                            raise WorkbookError("Duplicate column names in the specification table.")
                        found = (sheet.get("name"), sheet_path, rows, int(row.get("r")),
                                 {header: values[header][0] for header in HEADERS})
                        break
                if found:
                    break
            if not found:
                raise WorkbookError("Specification table not found. Use the column names from the sample workbook: " + ", ".join(HEADERS))
            sheet, sheet_path, rows, header_row, columns = found
            criteria = []
            used = set()
            for row in rows:
                row_number = int(row.get("r"))
                if row_number <= header_row:
                    continue
                cells = {c.get("r").rstrip("0123456789"): c for c in row}
                def get(header):
                    cell = cells.get(columns[header])
                    return _cell_value(cell, shared) if cell is not None else None
                test_id = get("Test ID")
                if test_id is None or str(test_id).strip() == "":
                    continue
                if not isinstance(test_id, str):
                    raise WorkbookError(f"The Test ID in row {row_number} must be text.")
                test_id = test_id.strip()
                if test_id in used:
                    raise WorkbookError(f"Duplicate Test ID: {test_id}")
                used.add(test_id)
                limits = []
                for header in ("Spec Min", "Spec Max"):
                    value = get(header)
                    if value == "":
                        value = None
                    if value is not None and (not isinstance(value, (int, float)) or not math.isfinite(value)):
                        raise WorkbookError(f"{test_id}: {header} must be a numeric cell or blank.")
                    limits.append(value)
                criteria.append(Criterion(test_id, str(get("Interface") or ""), str(get("Signal") or ""),
                                          str(get("Parameter") or ""), *limits, str(get("Unit") or ""), row_number))
            if not criteria:
                raise WorkbookError("The workbook has no specification rows.")
    except (BadZipFile, ET.ParseError, KeyError, IndexError) as exc:
        raise WorkbookError(f"Unable to read the XLSX structure: {exc}") from exc
    if fingerprint(path) != original_fingerprint:
        raise WorkbookError("The file changed while being read. Please reopen it.")
    return SpecWorkbook(path, original_fingerprint, sheet, sheet_path, columns, criteria)


def _children(node, local):
    return [n for n in node.childNodes if n.nodeType == n.ELEMENT_NODE and n.localName == local]


def _element(doc, name):
    prefix = doc.documentElement.prefix
    return doc.createElementNS(NS, f"{prefix}:{name}" if prefix else name)


def _column_number(address):
    result = 0
    for char in address.rstrip("0123456789"):
        result = result * 26 + ord(char) - 64
    return result


def _write_cell(doc, row, address, value, style=None):
    cell = next((c for c in _children(row, "c") if c.getAttribute("r") == address), None)
    if cell is None:
        cell = _element(doc, "c")
        cell.setAttribute("r", address)
        after = next((c for c in _children(row, "c") if _column_number(c.getAttribute("r")) > _column_number(address)), None)
        row.insertBefore(cell, after) if after else row.appendChild(cell)
    for child in list(cell.childNodes):
        if child.nodeType == child.ELEMENT_NODE and child.localName in ("v", "is", "f"):
            cell.removeChild(child)
    if cell.hasAttribute("t"):
        cell.removeAttribute("t")
    if style is not None:
        cell.setAttribute("s", str(style))
    if value is None:
        return
    if isinstance(value, (int, float)):
        v = _element(doc, "v")
        v.appendChild(doc.createTextNode(repr(value)))
        cell.appendChild(v)
    else:
        cell.setAttribute("t", "inlineStr")
        inline = _element(doc, "is")
        text = _element(doc, "t")
        text.setAttribute("xml:space", "preserve")
        text.appendChild(doc.createTextNode(str(value)))
        inline.appendChild(text)
        cell.appendChild(inline)


def _status_style(styles, base_id, status, cache):
    key = (base_id, status)
    if key in cache:
        return cache[key]
    fills = styles.getElementsByTagNameNS(NS, "fills")[0]
    xfs = styles.getElementsByTagNameNS(NS, "cellXfs")[0]
    color = {"PASS": "FFDCFCE7", "FAIL": "FFFEE2E2"}.get(status, "FFFEF3C7")
    fill = _element(styles, "fill")
    pattern = _element(styles, "patternFill")
    pattern.setAttribute("patternType", "solid")
    fg = _element(styles, "fgColor")
    fg.setAttribute("rgb", color)
    pattern.appendChild(fg)
    fill.appendChild(pattern)
    fill_id = len(_children(fills, "fill"))
    fills.appendChild(fill)
    fills.setAttribute("count", str(fill_id + 1))
    base = _children(xfs, "xf")[base_id].cloneNode(True)
    base.setAttribute("fillId", str(fill_id))
    base.setAttribute("applyFill", "1")
    style_id = len(_children(xfs, "xf"))
    xfs.appendChild(base)
    xfs.setAttribute("count", str(style_id + 1))
    cache[key] = style_id
    return style_id


def save_results(document: SpecWorkbook, results: list[Result], run_id: str,
                 output: str | Path | None = None) -> Path:
    """Write only results, backing up in-place edits and rejecting changed specs."""
    if fingerprint(document.path) != document.fingerprint:
        raise WorkbookError("The workbook changed after the specification was loaded. Reopen it and measure again before saving.")
    destination = Path(output).resolve() if output else document.path
    if destination.suffix.lower() != ".xlsx":
        raise WorkbookError("The results file must have an .xlsx extension.")
    if destination != document.path and destination.exists():
        raise WorkbookError("The destination file already exists. Choose a new name to avoid overwriting it.")
    criteria = {c.test_id: c for c in document.criteria}
    if len({r.criterion.test_id for r in results}) != len(results):
        raise WorkbookError("The results contain duplicate Test IDs.")
    for result in results:
        if criteria.get(result.criterion.test_id) != result.criterion:
            raise WorkbookError("The results do not match the loaded specification.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(document.path) as source:
        sheet = minidom.parseString(source.read(document.sheet_path))
        styles = minidom.parseString(source.read("xl/styles.xml"))
        rows = {int(r.getAttribute("r")): r for r in sheet.getElementsByTagNameNS(NS, "row")}
        cache = {}
        for result in results:
            row = rows[result.criterion.row]
            measurement = result.measurement
            values = {
                "Measured Min": measurement.minimum if measurement else None,
                "Measured Max": measurement.maximum if measurement else None,
                "Result": result.status, "Note": result.note, "Run ID": run_id,
            }
            for header, value in values.items():
                address = f"{document.columns[header]}{result.criterion.row}"
                style = None
                if header == "Result":
                    existing = next((c for c in _children(row, "c") if c.getAttribute("r") == address), None)
                    base_id = int(existing.getAttribute("s") or 0) if existing else 0
                    style = _status_style(styles, base_id, result.status, cache)
                _write_cell(sheet, row, address, value, style)
        replacements = {document.sheet_path: sheet.toxml(encoding="UTF-8"),
                        "xl/styles.xml": styles.toxml(encoding="UTF-8")}
        fd, temp_name = tempfile.mkstemp(prefix=".hwval-", suffix=".xlsx", dir=destination.parent)
        os.close(fd)
        temporary = Path(temp_name)
        try:
            with ZipFile(temporary, "w") as target:
                for info in source.infolist():
                    target.writestr(info, replacements.get(info.filename, source.read(info.filename)))
            with ZipFile(temporary) as check:
                if check.testzip():
                    raise WorkbookError("The saved XLSX file failed validation.")
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
    try:
        if fingerprint(document.path) != document.fingerprint:
            raise WorkbookError("The workbook was modified. Saving has stopped to protect your data.")
        if destination == document.path:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            backup_dir = destination.parent / "backups"
            backup_dir.mkdir(exist_ok=True)
            shutil.copy2(destination, backup_dir / f"{destination.stem}_{stamp}.xlsx")
        os.replace(temporary, destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    document.fingerprint = fingerprint(document.path)
    return destination
