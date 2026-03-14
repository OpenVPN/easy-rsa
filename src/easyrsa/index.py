"""Easy-RSA PKI index.txt parser and writer.

Tab-delimited format:
  V  <expiry>  <serial>  unknown  <subject>
  R  <expiry>  <revoke_date>[,reason]  <serial>  unknown  <subject>
  E  <expiry>  <serial>  unknown  <subject>
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class IndexRecord:
    """Represents one record in index.txt."""

    status: str          # 'V', 'R', 'E'
    expiry: str          # ASN1 date YYMMDDHHMMSSZ or YYYYMMDDHHMMSSZ
    revoke_info: str     # For R records: "date[,reason]", else ""
    serial: str          # Uppercase hex serial
    unknown: str         # Always "unknown"
    subject: str         # DN string e.g. "/CN=foo"

    def to_line(self) -> str:
        """Serialize to a tab-delimited index.txt line."""
        if self.status == "R":
            return "\t".join([
                self.status,
                self.expiry,
                self.revoke_info,
                self.serial,
                self.unknown,
                self.subject,
            ])
        else:
            return "\t".join([
                self.status,
                self.expiry,
                self.serial,
                self.unknown,
                self.subject,
            ])


def _parse_line(line: str) -> Optional[IndexRecord]:
    """Parse one line of index.txt. Returns None for blank/comment lines."""
    line = line.rstrip("\n\r")
    if not line or line.startswith("#"):
        return None
    fields = line.split("\t")
    status = fields[0] if fields else ""
    if status == "R":
        # R  expiry  revoke_info  serial  unknown  subject
        if len(fields) < 6:
            return None
        return IndexRecord(
            status=fields[0],
            expiry=fields[1],
            revoke_info=fields[2],
            serial=fields[3],
            unknown=fields[4],
            subject=fields[5],
        )
    elif status in ("V", "E"):
        # V  expiry  serial  unknown  subject
        if len(fields) < 5:
            return None
        return IndexRecord(
            status=fields[0],
            expiry=fields[1],
            revoke_info="",
            serial=fields[2],
            unknown=fields[3],
            subject=fields[4],
        )
    return None


def parse_index(path: Path) -> List[IndexRecord]:
    """Parse pki/index.txt and return list of IndexRecord."""
    if not path.exists():
        return []
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            rec = _parse_line(line)
            if rec is not None:
                records.append(rec)
    return records


def write_index(records: List[IndexRecord], path: Path) -> None:
    """Write all records to index.txt atomically."""
    tmp = path.parent / (path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(rec.to_line() + "\n")
    os.replace(str(tmp), str(path))


def add_record(records: List[IndexRecord], record: IndexRecord) -> List[IndexRecord]:
    """Return a new list with record appended."""
    return list(records) + [record]


def find_by_serial(records: List[IndexRecord], serial: str) -> Optional[IndexRecord]:
    """Find a record by serial (case-insensitive)."""
    serial_upper = serial.upper()
    for rec in records:
        if rec.serial.upper() == serial_upper:
            return rec
    return None


def append_record(path: Path, record: IndexRecord) -> None:
    """Atomically append one record to index.txt."""
    with open(path, "a", encoding="utf-8") as f:
        f.write(record.to_line() + "\n")


def asn1_now() -> str:
    """Return current UTC time in ASN1 UTC format YYMMDDHHMMSSZ."""
    import datetime
    now = datetime.datetime.utcnow()
    return now.strftime("%y%m%d%H%M%SZ")


def asn1_from_datetime(dt) -> str:
    """Convert a datetime to ASN1 UTC format."""
    return dt.strftime("%y%m%d%H%M%SZ")


def datetime_from_asn1(s: str):
    """Parse ASN1 date string (YYMMDDHHMMSSZ or YYYYMMDDHHMMSSZ) to datetime."""
    import datetime
    s = s.rstrip("Z")
    if len(s) == 12:
        # YYMMDDHHMMSS
        yy = int(s[0:2])
        if yy < 70:
            year = 2000 + yy
        else:
            year = 1900 + yy
        month = int(s[2:4])
        day = int(s[4:6])
        hour = int(s[6:8])
        minute = int(s[8:10])
        second = int(s[10:12])
    elif len(s) == 14:
        # YYYYMMDDHHMMSS
        year = int(s[0:4])
        month = int(s[4:6])
        day = int(s[6:8])
        hour = int(s[8:10])
        minute = int(s[10:12])
        second = int(s[12:14])
    else:
        raise ValueError(f"Unrecognised ASN1 date: '{s}Z'")
    return datetime.datetime(year, month, day, hour, minute, second)
