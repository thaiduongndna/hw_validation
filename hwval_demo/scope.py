"""Tektronix MSO6B native measurements over a raw SCPI socket (port 4000).

The instrument Socket Server must be enabled, protocol None (not Terminal).
No VISA installation is needed for this small LAN-only demo.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import re
import socket
import time

from .engine import Measurement


class ScopeError(RuntimeError):
    pass


@dataclass(frozen=True)
class NativeMeasurement:
    slot: str
    kind: str
    source: str
    unit: str


def number(raw: str) -> float:
    try:
        value = float(raw.strip().strip('"'))
    except ValueError as exc:
        raise ScopeError(f"Non-numeric response: {raw!r}") from exc
    if not math.isfinite(value) or abs(value) >= 9e37:
        raise ScopeError("The scope returned an invalid/NaN value; no valid measurement is available.")
    return value


class TekScope:
    def __init__(self, host: str, port: int = 4000, timeout: float = 5):
        if not host.strip():
            raise ScopeError("Enter the oscilloscope IP address or hostname.")
        if not 1 <= int(port) <= 65535 or not math.isfinite(timeout) or timeout <= 0:
            raise ScopeError("Invalid port or timeout.")
        self.host, self.port, self.timeout = host.strip(), int(port), timeout
        self.sock = None
        self.buffer = b""
        self.identity = ""
        self.log = []
        self.old_header = None

    def connect(self):
        try:
            self.sock = socket.create_connection((self.host, self.port), self.timeout)
            self.identity = self.query("*IDN?")
            parts = self.identity.upper().split(",")
            if len(parts) < 2 or "TEKTRONIX" not in parts[0] or parts[1].strip() not in ("MSO64B", "MSO66B", "MSO68B"):
                raise ScopeError(f"The instrument is not a supported MSO6B model: {self.identity}")
            raw = self.query("HEADER?")
            previous_header = raw.strip().split()[-1].strip('"') if raw.strip() else ""
            if previous_header not in ("0", "1", "ON", "OFF"):
                raise ScopeError("Unable to read HEADER. Check that Socket Server uses protocol None.")
            self.old_header = previous_header
            self.write("HEADER OFF")
            return self.identity
        except Exception:
            self.close()
            raise

    def write(self, command: str):
        if not self.sock:
            raise ScopeError("The scope is not connected.")
        if "\n" in command or "\r" in command:
            raise ScopeError("Invalid SCPI command.")
        try:
            self.sock.sendall((command + "\n").encode("ascii"))
            self.log.append({"time": time.time(), "command": command})
        except OSError as exc:
            self._drop()
            raise ScopeError(f"Scope connection lost: {exc}") from exc

    def query(self, command: str) -> str:
        self.write(command)
        try:
            while b"\n" not in self.buffer:
                chunk = self.sock.recv(65536)
                if not chunk:
                    raise ScopeError("The scope closed the connection.")
                self.buffer += chunk
                if len(self.buffer) > 1024 * 1024:
                    raise ScopeError("The response is too long, or Socket Server is not using protocol None.")
            line, self.buffer = self.buffer.split(b"\n", 1)
            response = line.decode("utf-8", errors="replace").strip()
            self.log[-1]["response"] = response
            return response
        except (OSError, ScopeError) as exc:
            self._drop()  # A late reply must never be mistaken for a later query.
            raise ScopeError(f"Unable to read the SCPI response: {exc}") from exc

    def measurements(self) -> list[NativeMeasurement]:
        raw = self.query("MEASUREMENT:LIST?").strip().strip('"')
        if not raw or raw.upper() in ("NONE", "0"):
            return []
        slots = [s.strip().strip('"').upper() for s in raw.split(",")]
        found = []
        for slot in slots:
            if not re.fullmatch(r"MEAS[1-9][0-9]*", slot):
                raise ScopeError(f"Invalid measurement ID: {slot!r}")
            prefix = f"MEASUREMENT:{slot}"
            kind = self.query(prefix + ":TYPE?").strip('"').upper()
            source = self.query(prefix + ":SOURCE1?").strip('"')
            unit = self.query(prefix + ":YUNIT?").strip('"')
            found.append(NativeMeasurement(slot, kind, source, unit))
        return found

    def freeze(self, single: bool = False, acquisition_timeout: float = 15):
        """Leave the instrument stopped so all queries share an acquisition."""
        if not math.isfinite(acquisition_timeout) or acquisition_timeout <= 0:
            raise ScopeError("Acquisition timeout must be greater than zero.")
        if single:
            previous = self.query("ACQUIRE:STOPAFTER?").strip('"').upper()
            if previous not in ("RUNSTOP", "SEQUENCE"):
                raise ScopeError(f"Unsupported STOPAFTER value: {previous!r}")
            try:
                self.write("ACQUIRE:STOPAFTER SEQUENCE")
                self.write("ACQUIRE:STATE ON")
                deadline = time.monotonic() + acquisition_timeout
                while number(self.query("ACQUIRE:STATE?")) != 0:
                    if time.monotonic() >= deadline:
                        self.write("ACQUIRE:STATE OFF")
                        raise ScopeError("Single acquisition timeout: no trigger received. Previous data was not read.")
                    time.sleep(0.1)
            finally:
                if self.sock:
                    self.write("ACQUIRE:STOPAFTER " + previous)
        else:
            self.write("ACQUIRE:STATE OFF")
        if number(self.query("*OPC?")) != 1:
            raise ScopeError("The scope has not completed the acquisition.")

    def read(self, definition: NativeMeasurement) -> Measurement:
        prefix = f"MEASUREMENT:{definition.slot}:RESULTS:CURRENTACQ"
        population = number(self.query(prefix + ":POPULATION?"))
        if population < 1 or not population.is_integer():
            raise ScopeError(f"{definition.slot}: no valid samples in the current acquisition.")
        minimum = number(self.query(prefix + ":MINIMUM?"))
        maximum = number(self.query(prefix + ":MAXIMUM?"))
        after = number(self.query(prefix + ":POPULATION?"))
        if after != population:
            raise ScopeError("The measurement is not stable; its sample count changed while reading.")
        if minimum > maximum:
            raise ScopeError("The scope returned a minimum greater than the maximum.")
        aliases = {"Volts": "V", "VOLTS": "V", "Seconds": "s", "SECONDS": "s", "sec": "s", "HZ": "Hz"}
        unit = aliases.get(definition.unit, definition.unit)
        return Measurement(minimum, maximum, unit, int(population))

    def _drop(self):
        if self.sock:
            self.sock.close()
        self.sock = None
        self.buffer = b""

    def close(self):
        if self.sock and self.old_header is not None:
            try:
                self.write("HEADER " + self.old_header)
            except ScopeError:
                pass
        self._drop()
