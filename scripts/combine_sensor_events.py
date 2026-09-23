#!/usr/bin/env python3
"""Combine legacy and Zenodo marine fault events into one sensor corpus."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from oceanclaw import config


DEFAULT_INPUTS = [
    config.project_path("data/processed/sensor_events.csv"),
    config.project_path("data/processed/marine_sensor_events.csv"),
]


def read_rows(path: Path, dataset_kind: str) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        raise FileNotFoundError(f"Sensor event CSV not found: {path}")
    with path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        fieldnames = list(reader.fieldnames or [])
        rows = []
        for row in reader:
            row["dataset_kind"] = dataset_kind
            rows.append(row)
    return fieldnames, rows


def combine(input_paths: list[Path], output_path: Path) -> tuple[int, list[tuple[str, int]]]:
    fieldnames = ["dataset_kind"]
    all_rows: list[dict[str, str]] = []
    counts: list[tuple[str, int]] = []
    seen_ids: set[str] = set()

    for path in input_paths:
        dataset_kind = "marine_fault" if "marine" in path.stem else "legacy_sensor"
        columns, rows = read_rows(path, dataset_kind)
        for column in columns:
            if column not in fieldnames:
                fieldnames.append(column)
        for row in rows:
            event_id = (row.get("event_id") or "").strip()
            if not event_id:
                raise ValueError(f"Missing event_id in {path}")
            if event_id in seen_ids:
                raise ValueError(f"Duplicate event_id across sensor datasets: {event_id}")
            seen_ids.add(event_id)
        all_rows.extend(rows)
        counts.append((path.name, len(rows)))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_rows)
    return len(all_rows), counts


def main() -> int:
    parser = argparse.ArgumentParser(description="Combine OceanClaw sensor event CSV files.")
    parser.add_argument("--inputs", nargs="+", type=Path, default=DEFAULT_INPUTS)
    parser.add_argument("--out", type=Path, default=config.SENSOR_EVENTS_PATH)
    args = parser.parse_args()

    paths = [config.project_path(str(path)) for path in args.inputs]
    output_path = config.project_path(str(args.out))
    total, counts = combine(paths, output_path)
    for name, count in counts:
        print(f"[OK] {name}: {count:,} events")
    print(f"[OK] combined {total:,} sensor events")
    print(f"Saved to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
