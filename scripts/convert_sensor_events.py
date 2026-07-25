#!/usr/bin/env python3
"""Convert raw naval propulsion sensor rows into OceanClaw sensor events."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from oceanclaw import config


OUTPUT_COLUMNS = [
    "event_id",
    "source",
    "source_row",
    "equipment",
    "component",
    "event_type",
    "severity",
    "symptom",
    "recommended_action",
    "status",
    "running_hours",
    "ship_speed",
    "lever_position",
    "gt_shaft_torque_knm",
    "gt_rpm",
    "gas_generator_rpm",
    "hp_turbine_exit_temp_c",
    "compressor_outlet_temp_c",
    "hp_turbine_exit_pressure_bar",
    "compressor_outlet_pressure_bar",
    "gt_exhaust_pressure_bar",
    "fuel_flow_kg_s",
    "compressor_decay",
    "turbine_decay",
    "text",
]


def clean_column(name: str) -> str:
    return " ".join(name.replace("\xa0", " ").split())


def parse_float(row: dict[str, str], columns: dict[str, str], logical_name: str) -> float:
    value = row[columns[logical_name]].strip()
    return float(value) if value else 0.0


def severity_for_compressor(decay: float) -> str:
    if decay <= 0.95:
        return "warning"
    if decay <= 0.97:
        return "watch"
    return "normal"


def severity_for_turbine(decay: float) -> str:
    if decay <= 0.975:
        return "watch"
    return "normal"


def make_text(event: dict[str, object]) -> str:
    return (
        f"{event['equipment']} {event['component']} {event['event_type']}. "
        f"Severity: {event['severity']}. "
        f"Symptom: {event['symptom']}. "
        f"Recommended action: {event['recommended_action']}. "
        f"Running hours: {event['running_hours']}. "
        f"Ship speed: {event['ship_speed']} knots. "
        f"GT RPM: {event['gt_rpm']}. "
        f"Fuel flow: {event['fuel_flow_kg_s']} kg/s. "
        f"Compressor decay: {event['compressor_decay']}. "
        f"Turbine decay: {event['turbine_decay']}."
    )


def row_to_events(
    row: dict[str, str],
    columns: dict[str, str],
    source_name: str,
) -> list[dict[str, object]]:
    source_row = int(float(row[columns["index"]]))
    running_hours = source_row + 1
    ship_speed = parse_float(row, columns, "Ship speed (v)")
    lever_position = parse_float(row, columns, "Lever position")
    gt_shaft_torque = parse_float(row, columns, "Gas Turbine (GT) shaft torque (GTT) [kN m]")
    gt_rpm = parse_float(row, columns, "GT rate of revolutions (GTn) [rpm]")
    gas_generator_rpm = parse_float(row, columns, "Gas Generator rate of revolutions (GGn) [rpm]")
    hp_temp = parse_float(row, columns, "Hight Pressure (HP) Turbine exit temperature (T48) [C]")
    compressor_outlet_temp = parse_float(row, columns, "GT Compressor outlet air temperature (T2) [C]")
    hp_pressure = parse_float(row, columns, "HP Turbine exit pressure (P48) [bar]")
    compressor_outlet_pressure = parse_float(row, columns, "GT Compressor outlet air pressure (P2) [bar]")
    exhaust_pressure = parse_float(row, columns, "GT exhaust gas pressure (Pexh) [bar]")
    fuel_flow = parse_float(row, columns, "Fuel flow (mf) [kg/s]")
    compressor_decay = parse_float(row, columns, "GT Compressor decay state coefficient")
    turbine_decay = parse_float(row, columns, "GT Turbine decay state coefficient")

    common = {
        "source": source_name,
        "source_row": source_row,
        "equipment": "Naval Propulsion Plant",
        "running_hours": running_hours,
        "ship_speed": ship_speed,
        "lever_position": lever_position,
        "gt_shaft_torque_knm": gt_shaft_torque,
        "gt_rpm": gt_rpm,
        "gas_generator_rpm": gas_generator_rpm,
        "hp_turbine_exit_temp_c": hp_temp,
        "compressor_outlet_temp_c": compressor_outlet_temp,
        "hp_turbine_exit_pressure_bar": hp_pressure,
        "compressor_outlet_pressure_bar": compressor_outlet_pressure,
        "gt_exhaust_pressure_bar": exhaust_pressure,
        "fuel_flow_kg_s": fuel_flow,
        "compressor_decay": compressor_decay,
        "turbine_decay": turbine_decay,
    }

    events: list[dict[str, object]] = []

    compressor_severity = severity_for_compressor(compressor_decay)
    if compressor_severity != "normal":
        event = {
            **common,
            "event_id": f"sensor-{source_row}-compressor",
            "component": "GT Compressor",
            "event_type": "Compressor decay detected",
            "severity": compressor_severity,
            "symptom": f"GT compressor decay coefficient is {compressor_decay:.3f}.",
            "recommended_action": "Inspect GT compressor efficiency, outlet pressure, outlet temperature, and fouling condition.",
            "status": "needs_inspection",
        }
        event["text"] = make_text(event)
        events.append(event)

    turbine_severity = severity_for_turbine(turbine_decay)
    if turbine_severity != "normal":
        event = {
            **common,
            "event_id": f"sensor-{source_row}-turbine",
            "component": "GT Turbine",
            "event_type": "Turbine decay detected",
            "severity": turbine_severity,
            "symptom": f"GT turbine decay coefficient is {turbine_decay:.3f}.",
            "recommended_action": "Monitor turbine condition and compare exhaust temperature, shaft torque, and fuel flow trends.",
            "status": "monitor",
        }
        event["text"] = make_text(event)
        events.append(event)

    return events


def convert(input_path: Path, output_path: Path) -> int:
    if not input_path.exists():
        raise FileNotFoundError(f"CSV not found: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0

    with input_path.open(newline="", encoding="utf-8-sig") as in_file:
        reader = csv.DictReader(in_file)
        columns = {clean_column(column): column for column in reader.fieldnames or []}

        with output_path.open("w", newline="", encoding="utf-8") as out_file:
            writer = csv.DictWriter(out_file, fieldnames=OUTPUT_COLUMNS)
            writer.writeheader()
            for row in reader:
                for event in row_to_events(row, columns, input_path.name):
                    writer.writerow(event)
                    count += 1

    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert sensor CSV to OceanClaw events.")
    parser.add_argument("--input", type=Path, default=config.project_path("data/raw/data.csv"))
    parser.add_argument("--out", type=Path, default=config.project_path("data/processed/sensor_events.csv"))
    args = parser.parse_args()

    count = convert(
        input_path=config.project_path(str(args.input)),
        output_path=config.project_path(str(args.out)),
    )
    print(f"[OK] created {count} sensor events")
    print(f"Saved to: {config.project_path(str(args.out))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
