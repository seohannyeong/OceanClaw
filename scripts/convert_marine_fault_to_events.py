#!/usr/bin/env python3
"""Convert the Zenodo marine engine fault dataset into searchable events."""

from __future__ import annotations

import argparse
import csv
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from oceanclaw import config


DEFAULT_INPUT_DIR = config.project_path("data/raw/marine_engine_fault")
DEFAULT_OUTPUT_PATH = config.project_path("data/processed/marine_sensor_events.csv")

METRICS = {
    "Engine Speed": "engine_speed_rpm",
    "Fuel Flow": "fuel_flow_m3_h",
    "Compressor Filter Loss": "compressor_filter_loss_pa",
    "Turbine Back Pressure": "turbine_back_pressure_pa",
    "Charge Air Press.": "charge_air_pressure_kgf_cm2",
    "Exh.Gas Temp. Turbine In": "exhaust_temp_turbine_in_c",
    "Exh.Gas Temp. Turbine Out": "exhaust_temp_turbine_out_c",
    "Cooling Water Temp. Engine In": "cooling_water_engine_in_c",
    "Cooling Water Temp. Engine Out I": "cooling_water_engine_out_c",
    "LO Temp. Engine In": "oil_temp_engine_in_c",
    "LO Temp. Engine Out": "oil_temp_engine_out_c",
    "Mechanical Efficiency": "mechanical_efficiency_pct",
    "Effective Efficiency": "effective_efficiency_pct",
}

OUTPUT_COLUMNS = [
    "event_id",
    "source",
    "source_row",
    "equipment",
    "component",
    "event_type",
    "scenario",
    "load",
    "severity",
    "symptom",
    "recommended_action",
    "status",
    "start_time_s",
    "end_time_s",
    "row_count",
]
for metric_name in METRICS.values():
    OUTPUT_COLUMNS.extend((f"{metric_name}_avg", f"{metric_name}_min", f"{metric_name}_max"))
OUTPUT_COLUMNS.append("text")

SCENARIO_DETAILS = {
    "Air-cooler fouling": {
        "slug": "air-cooler-fouling",
        "component": "Charge air cooler",
        "event_type": "Air-cooler fouling anomaly",
        "symptom": "The measured engine signals correspond to an air-cooler fouling experiment.",
        "action": "Inspect and clean the charge-air cooler; compare charge-air pressure, cooling-water flow, and inlet/outlet temperatures.",
    },
    "Air-filter clogging (compressor)": {
        "slug": "air-filter-clogging",
        "component": "Compressor air filter",
        "event_type": "Compressor air-filter clogging anomaly",
        "symptom": "The measured engine signals correspond to a compressor air-filter clogging experiment.",
        "action": "Inspect and clean or replace the compressor air filter; check filter pressure loss and charge-air pressure.",
    },
    "Injection-valve nozzle clogging": {
        "slug": "injector-nozzle-clogging",
        "component": "Fuel injector nozzle",
        "event_type": "Fuel-injector nozzle clogging anomaly",
        "symptom": "The measured engine signals correspond to an injection-valve nozzle clogging experiment.",
        "action": "Inspect the injector nozzle and compare cylinder pressure, cylinder exhaust temperatures, and fuel flow for imbalance.",
    },
    "Cooling-water pump cavitation": {
        "slug": "cooling-water-pump-cavitation",
        "component": "Cooling water pump",
        "event_type": "Cooling-water pump cavitation anomaly",
        "symptom": "The measured engine signals correspond to a cooling-water pump cavitation experiment.",
        "action": "Inspect pump suction conditions and cavitation; check cooling-water pressure, flow, and engine inlet/outlet temperatures.",
    },
    "Turbine degradation": {
        "slug": "turbine-degradation",
        "component": "Turbocharger turbine",
        "event_type": "Turbocharger turbine degradation anomaly",
        "symptom": "The measured engine signals correspond to a turbine degradation experiment.",
        "action": "Inspect the turbocharger turbine; compare turbine back pressure, exhaust temperatures, shaft power, and efficiency trends.",
    },
}


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


def format_number(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.4f}".rstrip("0").rstrip(".")


def read_dataset_index(index_path: Path) -> list[dict[str, str]]:
    with index_path.open(newline="", encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))
    return [row for row in rows if row.get("schema_type", "").strip() == "scenario"]


def read_scenario_rows(path: Path, all_anomaly: bool) -> Iterable[tuple[int, dict[str, str]]]:
    with path.open(newline="", encoding="utf-8-sig") as file:
        reader = csv.reader(file)
        try:
            headers = next(reader)
            next(reader)  # symbols
            next(reader)  # units
        except StopIteration as error:
            raise ValueError(f"Invalid three-row header: {path}") from error

        for source_row, values in enumerate(reader, start=4):
            if not values or not any(value.strip() for value in values):
                continue
            row = dict(zip(headers, values))
            anomaly_state = parse_float(row.get("Anomaly State"))
            if all_anomaly or anomaly_state == 1.0:
                yield source_row, row


def summarize(values: Iterable[float | None]) -> tuple[float | None, float | None, float | None]:
    valid = [value for value in values if value is not None]
    if not valid:
        return None, None, None
    return statistics.fmean(valid), min(valid), max(valid)


def build_event_text(event: dict[str, object]) -> str:
    measurements: list[str] = []
    display_metrics = (
        ("engine_speed_rpm_avg", "engine speed", "rpm"),
        ("fuel_flow_m3_h_avg", "fuel flow", "m3/h"),
        ("compressor_filter_loss_pa_avg", "compressor filter loss", "Pa"),
        ("turbine_back_pressure_pa_avg", "turbine back pressure", "Pa"),
        ("charge_air_pressure_kgf_cm2_avg", "charge-air pressure", "kgf/cm2"),
        ("exhaust_temp_turbine_in_c_avg", "turbine-in exhaust temperature", "C"),
        ("exhaust_temp_turbine_out_c_avg", "turbine-out exhaust temperature", "C"),
        ("cooling_water_engine_in_c_avg", "engine-in cooling-water temperature", "C"),
        ("cooling_water_engine_out_c_avg", "engine-out cooling-water temperature", "C"),
        ("mechanical_efficiency_pct_avg", "mechanical efficiency", "%"),
        ("effective_efficiency_pct_avg", "effective efficiency", "%"),
    )
    for key, label, unit in display_metrics:
        value = str(event.get(key, ""))
        if value:
            measurements.append(f"{label}: {value} {unit}")

    measurement_text = "; ".join(measurements) or "No selected measurement was recorded."
    return (
        f"Marine diesel engine fault event. Scenario: {event['scenario']}. "
        f"Load condition: {event['load']}. Component: {event['component']}. "
        f"Event: {event['event_type']}. Severity: {event['severity']}. "
        f"Time window: {event['start_time_s']} to {event['end_time_s']} seconds. "
        f"Symptom: {event['symptom']} Measurements: {measurement_text}. "
        f"Recommended action: {event['recommended_action']}"
    )


def convert_file(
    input_path: Path,
    index_row: dict[str, str],
    window_seconds: float,
) -> list[dict[str, object]]:
    scenario = index_row["scenario"].strip()
    details = SCENARIO_DETAILS.get(scenario)
    if details is None:
        raise ValueError(f"Unsupported scenario in dataset_index.csv: {scenario}")

    all_anomaly = "all-anomaly" in index_row.get("anomaly_state", "").lower()
    windows: dict[int, list[tuple[int, dict[str, str], float]]] = defaultdict(list)
    fallback_time = 0.0

    for source_row, row in read_scenario_rows(input_path, all_anomaly=all_anomaly):
        time_value = parse_float(row.get("Time_rel"))
        if time_value is None:
            time_value = fallback_time
        fallback_time = time_value + 1.0
        window_number = int(max(time_value, 0.0) // window_seconds)
        windows[window_number].append((source_row, row, time_value))

    events: list[dict[str, object]] = []
    source_stem = input_path.stem.lower().replace("_", "-")
    for event_number, window_rows in enumerate(windows.values(), start=1):
        first_source_row = window_rows[0][0]
        times = [entry[2] for entry in window_rows]
        event: dict[str, object] = {
            "event_id": f"marine-{details['slug']}-{source_stem}-{event_number:04d}",
            "source": input_path.name,
            "source_row": first_source_row,
            "equipment": "Matsui MU323DGSC marine diesel engine",
            "component": details["component"],
            "event_type": details["event_type"],
            "scenario": scenario,
            "load": index_row.get("nominal_load", "").strip(),
            "severity": "warning",
            "symptom": details["symptom"],
            "recommended_action": details["action"],
            "status": "needs_inspection",
            "start_time_s": format_number(min(times)),
            "end_time_s": format_number(max(times)),
            "row_count": len(window_rows),
        }

        for source_column, output_name in METRICS.items():
            average, minimum, maximum = summarize(
                parse_float(row.get(source_column)) for _, row, _ in window_rows
            )
            event[f"{output_name}_avg"] = format_number(average)
            event[f"{output_name}_min"] = format_number(minimum)
            event[f"{output_name}_max"] = format_number(maximum)

        event["text"] = build_event_text(event)
        events.append(event)

    return events


def convert(input_dir: Path, output_path: Path, window_seconds: float) -> tuple[int, int]:
    if window_seconds <= 0:
        raise ValueError("--window-seconds must be greater than zero")

    index_path = input_dir / "dataset_index.csv"
    if not index_path.exists():
        raise FileNotFoundError(f"Dataset index not found: {index_path}")

    all_events: list[dict[str, object]] = []
    scenario_rows = read_dataset_index(index_path)
    for index_row in scenario_rows:
        relative_path = Path(index_row["file_name"])
        input_path = input_dir / relative_path
        if not input_path.exists():
            raise FileNotFoundError(f"Scenario CSV not found: {input_path}")
        events = convert_file(input_path, index_row, window_seconds)
        all_events.extend(events)
        print(f"[OK] {relative_path}: {len(events)} events")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(all_events)

    return len(scenario_rows), len(all_events)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert the Zenodo marine engine fault dataset to OceanClaw events."
    )
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--window-seconds", type=float, default=60.0)
    args = parser.parse_args()

    input_dir = config.project_path(str(args.input_dir))
    output_path = config.project_path(str(args.out))
    file_count, event_count = convert(input_dir, output_path, args.window_seconds)

    print(f"[OK] processed {file_count} scenario files")
    print(f"[OK] created {event_count} marine sensor events")
    print(f"Saved to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
