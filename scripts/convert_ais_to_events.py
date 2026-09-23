#!/usr/bin/env python3
"""Convert unsorted AIS position reports into searchable voyage events."""

from __future__ import annotations

import argparse
import csv
import math
import sqlite3
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from oceanclaw import config


DEFAULT_INPUT_PATH = config.project_path("data/raw/ais/guam_2025.csv")
DEFAULT_OUTPUT_PATH = config.project_path("data/processed/ais_voyage_events.csv")

OUTPUT_COLUMNS = [
    "event_id",
    "source",
    "source_row_start",
    "source_row_end",
    "mmsi",
    "imo",
    "call_sign",
    "vessel_name",
    "vessel_type",
    "event_type",
    "navigation_status",
    "start_time",
    "end_time",
    "duration_minutes",
    "report_count",
    "average_sog_knots",
    "maximum_sog_knots",
    "distance_nm",
    "start_longitude",
    "start_latitude",
    "end_longitude",
    "end_latitude",
    "length_m",
    "width_m",
    "draft_m",
    "cargo",
    "transceiver",
    "text",
]

NAVIGATION_STATUS = {
    "0": "under way using engine",
    "1": "at anchor",
    "2": "not under command",
    "3": "restricted manoeuvrability",
    "4": "constrained by draught",
    "5": "moored",
    "6": "aground",
    "7": "engaged in fishing",
    "8": "under way sailing",
    "9": "reserved for high-speed craft",
    "10": "reserved for wing-in-ground craft",
    "11": "power-driven vessel towing astern",
    "12": "power-driven vessel pushing or towing alongside",
    "13": "reserved",
    "14": "AIS-SART or special manoeuvre",
    "15": "undefined",
}

SQL_COLUMNS = [
    "source_row",
    "mmsi",
    "base_date_time",
    "sog",
    "cog",
    "heading",
    "vessel_name",
    "imo",
    "call_sign",
    "vessel_type",
    "status",
    "length",
    "width",
    "draft",
    "cargo",
    "transceiver",
    "longitude",
    "latitude",
]


def parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    try:
        number = float(cleaned)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def parse_geometry(value: str) -> tuple[float | None, float | None]:
    cleaned = value.strip()
    if not cleaned.upper().startswith("POINT (") or not cleaned.endswith(")"):
        return None, None
    coordinates = cleaned[7:-1].split()
    if len(coordinates) != 2:
        return None, None
    return parse_float(coordinates[0]), parse_float(coordinates[1])


def format_number(value: float | None, digits: int = 4) -> str:
    if value is None:
        return ""
    return f"{value:.{digits}f}".rstrip("0").rstrip(".")


def navigation_status_name(value: str | None) -> str:
    cleaned = (value or "").strip()
    return NAVIGATION_STATUS.get(cleaned, f"status {cleaned}" if cleaned else "unknown")


def classify_event(status: str | None, sog: float | None, stop_speed: float, low_speed: float) -> str:
    cleaned_status = (status or "").strip()
    if cleaned_status == "5":
        return "moored"
    if cleaned_status == "1":
        return "anchored"
    if cleaned_status == "6":
        return "aground"
    if cleaned_status == "7":
        return "fishing"
    if cleaned_status == "8":
        return "sailing"
    if sog is None or sog <= stop_speed:
        return "stationary"
    if sog <= low_speed:
        return "low-speed movement"
    return "underway"


def haversine_nm(
    first_longitude: float | None,
    first_latitude: float | None,
    second_longitude: float | None,
    second_latitude: float | None,
) -> float:
    if None in (first_longitude, first_latitude, second_longitude, second_latitude):
        return 0.0
    lon1, lat1, lon2, lat2 = map(
        math.radians,
        (first_longitude, first_latitude, second_longitude, second_latitude),
    )
    delta_lon = lon2 - lon1
    delta_lat = lat2 - lat1
    haversine = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    central_angle = 2 * math.asin(min(1.0, math.sqrt(haversine)))
    return 3440.065 * central_angle


def first_value(*values: object) -> str:
    for value in values:
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


@dataclass
class VoyageEvent:
    sequence: int
    source_row_start: int
    source_row_end: int
    mmsi: str
    event_type: str
    navigation_status: str
    start_time: datetime
    end_time: datetime
    vessel_name: str
    imo: str
    call_sign: str
    vessel_type: str
    length: str
    width: str
    draft: str
    cargo: str
    transceiver: str
    start_longitude: float | None
    start_latitude: float | None
    end_longitude: float | None
    end_latitude: float | None
    previous_longitude: float | None
    previous_latitude: float | None
    report_count: int = 0
    sog_sum: float = 0.0
    sog_count: int = 0
    maximum_sog: float | None = None
    distance_nm: float = 0.0

    @classmethod
    def from_row(cls, row: sqlite3.Row, sequence: int, event_type: str) -> "VoyageEvent":
        timestamp = datetime.fromisoformat(row["base_date_time"])
        event = cls(
            sequence=sequence,
            source_row_start=row["source_row"],
            source_row_end=row["source_row"],
            mmsi=row["mmsi"],
            event_type=event_type,
            navigation_status=navigation_status_name(row["status"]),
            start_time=timestamp,
            end_time=timestamp,
            vessel_name=first_value(row["vessel_name"]),
            imo=first_value(row["imo"]),
            call_sign=first_value(row["call_sign"]),
            vessel_type=first_value(row["vessel_type"]),
            length=first_value(row["length"]),
            width=first_value(row["width"]),
            draft=first_value(row["draft"]),
            cargo=first_value(row["cargo"]),
            transceiver=first_value(row["transceiver"]),
            start_longitude=row["longitude"],
            start_latitude=row["latitude"],
            end_longitude=row["longitude"],
            end_latitude=row["latitude"],
            previous_longitude=row["longitude"],
            previous_latitude=row["latitude"],
        )
        event.add(row)
        return event

    def add(self, row: sqlite3.Row) -> None:
        timestamp = datetime.fromisoformat(row["base_date_time"])
        longitude = row["longitude"]
        latitude = row["latitude"]
        self.distance_nm += haversine_nm(
            self.previous_longitude,
            self.previous_latitude,
            longitude,
            latitude,
        )
        self.previous_longitude = longitude
        self.previous_latitude = latitude
        self.end_longitude = longitude
        self.end_latitude = latitude
        self.end_time = timestamp
        self.source_row_end = row["source_row"]
        self.report_count += 1

        sog = row["sog"]
        if sog is not None:
            self.sog_sum += sog
            self.sog_count += 1
            self.maximum_sog = sog if self.maximum_sog is None else max(self.maximum_sog, sog)

        self.vessel_name = first_value(self.vessel_name, row["vessel_name"])
        self.imo = first_value(self.imo, row["imo"])
        self.call_sign = first_value(self.call_sign, row["call_sign"])


def create_database(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA journal_mode=OFF")
    connection.execute("PRAGMA synchronous=OFF")
    connection.execute("PRAGMA temp_store=FILE")
    connection.execute(
        """
        CREATE TABLE ais (
            source_row INTEGER,
            mmsi TEXT,
            base_date_time TEXT,
            sog REAL,
            cog REAL,
            heading REAL,
            vessel_name TEXT,
            imo TEXT,
            call_sign TEXT,
            vessel_type TEXT,
            status TEXT,
            length TEXT,
            width TEXT,
            draft TEXT,
            cargo TEXT,
            transceiver TEXT,
            longitude REAL,
            latitude REAL
        )
        """
    )


def load_csv_to_database(
    input_path: Path,
    connection: sqlite3.Connection,
    batch_size: int,
    limit_rows: int | None,
) -> tuple[int, int]:
    insert_sql = f"INSERT INTO ais VALUES ({','.join('?' for _ in SQL_COLUMNS)})"
    batch: list[tuple[object, ...]] = []
    imported = 0
    skipped = 0

    with input_path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        for source_row, row in enumerate(reader, start=2):
            if limit_rows is not None and imported + skipped >= limit_rows:
                break
            mmsi = (row.get("mmsi") or "").strip()
            timestamp = (row.get("base_date_time") or "").strip()
            longitude, latitude = parse_geometry(row.get("geometry") or "")
            if not mmsi or not timestamp:
                skipped += 1
                continue
            try:
                datetime.fromisoformat(timestamp)
            except ValueError:
                skipped += 1
                continue

            batch.append(
                (
                    source_row,
                    mmsi,
                    timestamp,
                    parse_float(row.get("sog")),
                    parse_float(row.get("cog")),
                    parse_float(row.get("heading")),
                    row.get("vessel_name", "").strip(),
                    row.get("imo", "").strip(),
                    row.get("call_sign", "").strip(),
                    row.get("vessel_type", "").strip(),
                    row.get("status", "").strip(),
                    row.get("length", "").strip(),
                    row.get("width", "").strip(),
                    row.get("draft", "").strip(),
                    row.get("cargo", "").strip(),
                    row.get("transceiver", "").strip(),
                    longitude,
                    latitude,
                )
            )
            imported += 1
            if len(batch) >= batch_size:
                connection.executemany(insert_sql, batch)
                connection.commit()
                batch.clear()
                if imported % 500_000 < batch_size:
                    print(f"Imported {imported:,} AIS reports...")

    if batch:
        connection.executemany(insert_sql, batch)
        connection.commit()

    connection.execute("CREATE INDEX ais_mmsi_time ON ais (mmsi, base_date_time, source_row)")
    connection.commit()
    return imported, skipped


def ordered_rows(connection: sqlite3.Connection) -> Iterable[sqlite3.Row]:
    connection.row_factory = sqlite3.Row
    return connection.execute("SELECT * FROM ais ORDER BY mmsi, base_date_time, source_row")


def event_to_row(event: VoyageEvent, source_name: str) -> dict[str, object]:
    duration_minutes = max(0.0, (event.end_time - event.start_time).total_seconds() / 60)
    average_sog = event.sog_sum / event.sog_count if event.sog_count else None
    vessel_label = event.vessel_name or f"MMSI {event.mmsi}"
    event_id = f"ais-{event.mmsi}-{event.sequence:05d}"
    text = (
        f"AIS vessel movement event near Guam. Vessel: {vessel_label}. MMSI: {event.mmsi}. "
        f"IMO: {event.imo or 'unknown'}. Event type: {event.event_type}. "
        f"Navigation status: {event.navigation_status}. "
        f"Period: {event.start_time.isoformat(sep=' ')} to {event.end_time.isoformat(sep=' ')}. "
        f"Duration: {format_number(duration_minutes, 1)} minutes. "
        f"Average speed over ground: {format_number(average_sog, 2)} knots; "
        f"maximum speed: {format_number(event.maximum_sog, 2)} knots; "
        f"estimated travelled distance: {format_number(event.distance_nm, 2)} nautical miles. "
        f"Start position: {format_number(event.start_latitude, 5)}, {format_number(event.start_longitude, 5)}. "
        f"End position: {format_number(event.end_latitude, 5)}, {format_number(event.end_longitude, 5)}."
    )
    return {
        "event_id": event_id,
        "source": source_name,
        "source_row_start": event.source_row_start,
        "source_row_end": event.source_row_end,
        "mmsi": event.mmsi,
        "imo": event.imo,
        "call_sign": event.call_sign,
        "vessel_name": event.vessel_name,
        "vessel_type": event.vessel_type,
        "event_type": event.event_type,
        "navigation_status": event.navigation_status,
        "start_time": event.start_time.isoformat(sep=" "),
        "end_time": event.end_time.isoformat(sep=" "),
        "duration_minutes": format_number(duration_minutes, 1),
        "report_count": event.report_count,
        "average_sog_knots": format_number(average_sog, 2),
        "maximum_sog_knots": format_number(event.maximum_sog, 2),
        "distance_nm": format_number(event.distance_nm, 2),
        "start_longitude": format_number(event.start_longitude, 5),
        "start_latitude": format_number(event.start_latitude, 5),
        "end_longitude": format_number(event.end_longitude, 5),
        "end_latitude": format_number(event.end_latitude, 5),
        "length_m": event.length,
        "width_m": event.width,
        "draft_m": event.draft,
        "cargo": event.cargo,
        "transceiver": event.transceiver,
        "text": text,
    }


def build_events(
    connection: sqlite3.Connection,
    output_path: Path,
    source_name: str,
    stop_speed: float,
    low_speed: float,
    gap_minutes: float,
    minimum_reports: int,
) -> tuple[int, int]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    event_count = 0
    vessel_count = 0
    current: VoyageEvent | None = None
    current_mmsi = ""
    sequence = 0

    def write_event(writer: csv.DictWriter, event: VoyageEvent | None) -> int:
        if event is None or event.report_count < minimum_reports:
            return 0
        writer.writerow(event_to_row(event, source_name))
        return 1

    with output_path.open("w", newline="", encoding="utf-8-sig") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()

        for row in ordered_rows(connection):
            timestamp = datetime.fromisoformat(row["base_date_time"])
            event_type = classify_event(row["status"], row["sog"], stop_speed, low_speed)
            new_vessel = row["mmsi"] != current_mmsi
            gap = (
                (timestamp - current.end_time).total_seconds() / 60
                if current is not None and not new_vessel
                else 0.0
            )
            split_event = (
                current is None
                or new_vessel
                or event_type != current.event_type
                or gap < 0
                or gap > gap_minutes
            )

            if split_event:
                event_count += write_event(writer, current)
                if new_vessel:
                    vessel_count += 1
                    current_mmsi = row["mmsi"]
                    sequence = 1
                else:
                    sequence += 1
                current = VoyageEvent.from_row(row, sequence, event_type)
            else:
                current.add(row)

        event_count += write_event(writer, current)

    return vessel_count, event_count


def convert(
    input_path: Path,
    output_path: Path,
    stop_speed: float,
    low_speed: float,
    gap_minutes: float,
    minimum_reports: int,
    batch_size: int,
    limit_rows: int | None,
) -> tuple[int, int, int, int]:
    if not input_path.exists():
        raise FileNotFoundError(f"AIS CSV not found: {input_path}")
    if not 0 <= stop_speed < low_speed:
        raise ValueError("Speed thresholds must satisfy 0 <= stop-speed < low-speed")
    if gap_minutes <= 0 or minimum_reports <= 0 or batch_size <= 0:
        raise ValueError("Gap, minimum reports, and batch size must be positive")

    with tempfile.TemporaryDirectory(prefix="oceanclaw-ais-") as temp_dir:
        database_path = Path(temp_dir) / "ais.sqlite3"
        connection = sqlite3.connect(database_path)
        try:
            create_database(connection)
            imported, skipped = load_csv_to_database(
                input_path,
                connection,
                batch_size=batch_size,
                limit_rows=limit_rows,
            )
            vessels, events = build_events(
                connection,
                output_path,
                source_name=input_path.name,
                stop_speed=stop_speed,
                low_speed=low_speed,
                gap_minutes=gap_minutes,
                minimum_reports=minimum_reports,
            )
        finally:
            connection.close()

    return imported, skipped, vessels, events


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert AIS reports into voyage events.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--stop-speed", type=float, default=0.5, help="Stationary threshold in knots.")
    parser.add_argument("--low-speed", type=float, default=3.0, help="Low-speed threshold in knots.")
    parser.add_argument("--gap-minutes", type=float, default=360.0, help="Start a new event after this reporting gap.")
    parser.add_argument("--minimum-reports", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=10_000)
    parser.add_argument("--limit-rows", type=int, help="Process only the first N rows for a quick test.")
    args = parser.parse_args()

    imported, skipped, vessels, events = convert(
        input_path=config.project_path(str(args.input)),
        output_path=config.project_path(str(args.out)),
        stop_speed=args.stop_speed,
        low_speed=args.low_speed,
        gap_minutes=args.gap_minutes,
        minimum_reports=args.minimum_reports,
        batch_size=args.batch_size,
        limit_rows=args.limit_rows,
    )
    print(f"[OK] imported {imported:,} AIS reports; skipped {skipped:,}")
    print(f"[OK] processed {vessels:,} vessels")
    print(f"[OK] created {events:,} voyage events")
    print(f"Saved to: {config.project_path(str(args.out))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
