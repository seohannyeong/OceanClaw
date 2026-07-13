#!/usr/bin/env python3
"""샘플 데이터 생성: 선박 엔진 영문 매뉴얼 PDF 1개 + 정비 이력 CSV 1개.

실제 정비 환경을 모사하되, 계획서의 시나리오(메인 베어링 토크 150 Nm,
4번 실린더 피스톤 링 교체 등)와 맞춰 데모가 잘 되도록 구성했다.

사용법:
    python scripts/make_sample_data.py
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"


# ----- 매뉴얼 본문 (페이지 단위) -----------------------------------------
# 각 항목이 PDF 한 페이지가 된다. (출처 페이지 인용 데모용)
MANUAL_PAGES = [
    # p.1
    ("MAN B&W S60MC-C Main Engine - Maintenance Manual",
     "This manual covers operation and maintenance of the MAN B&W S60MC-C "
     "two-stroke low-speed marine diesel engine. It contains torque values, "
     "clearances and recommended maintenance intervals for the main running "
     "gear. Always follow the safety procedures in Section 1 before any work."),
    # p.2
    ("Section 1 - Safety Procedures",
     "Before maintenance, stop the engine, engage the turning gear and lock "
     "the starting air supply. Confirm the lubricating oil pump is stopped. "
     "Wear appropriate PPE. Never enter the crankcase until the temperature "
     "is below 40 degrees Celsius and ventilation has run for at least 20 minutes."),
    # p.3
    ("Section 2 - Main Bearings: Tightening Torque",
     "The main bearing studs must be tightened in two stages. "
     "Initial tightening torque of the main bearing bolt is 150 Nm. "
     "After initial tightening, apply a final angle tightening of 90 degrees "
     "using the hydraulic tool set. Always tighten studs in diagonal sequence. "
     "Recommended lubricating oil on threads: Molykote 1000."),
    # p.4
    ("Section 2 - Main Bearings: Clearance",
     "The main bearing running clearance (oil clearance) when new is between "
     "0.35 mm and 0.50 mm. The maximum permissible worn clearance is 0.85 mm; "
     "replace the bearing shell if exceeded. Check the clearance with a "
     "feeler gauge at every major overhaul."),
    # p.5
    ("Section 3 - Cylinder Unit",
     "The cylinder liner bore is 600 mm. The cylinder cover stud initial "
     "tightening torque is 280 Nm, followed by a final hydraulic tensioning "
     "to 1,250 bar. Inspect the cooling water spaces for scale and corrosion "
     "during each cylinder overhaul."),
    # p.6
    ("Section 4 - Piston and Piston Rings",
     "Each piston is fitted with 4 piston rings. The piston ring gap clearance "
     "when new is 1.2 mm to 1.6 mm for the top ring. Replace piston rings when "
     "the ring gap exceeds 4.0 mm. The piston ring groove wear limit is 0.3 mm. "
     "Always renew all rings of a cylinder as a set."),
    # p.7
    ("Section 5 - Recommended Maintenance Intervals",
     "Main bearing inspection: every 5 years or 60,000 running hours. "
     "Piston ring inspection: every 8,000 running hours. "
     "Piston ring renewal: every 16,000 running hours or when wear limit reached. "
     "Cylinder liner inspection: every 8,000 running hours. "
     "Fuel injection valve overhaul: every 4,000 running hours."),
    # p.8
    ("Section 6 - Lubrication",
     "Use SAE 30 system oil with a base number suitable for the fuel sulphur "
     "content. Maintain the cylinder oil feed rate at 0.8 to 1.0 g/kWh. "
     "Check the lubricating oil pressure: normal range is 1.8 to 2.2 bar at "
     "the bearing inlet during full load operation."),
]


# ----- 정비 이력 CSV ----------------------------------------------------
CSV_HEADER = [
    "date", "equipment", "component", "work_type",
    "running_hours", "engineer", "remarks",
]
CSV_ROWS = [
    ["2024-03-12", "Main Engine", "Cylinder 1", "Overhaul", "41200", "C/E Park", "피스톤 발출 점검, 링 상태 양호"],
    ["2024-04-05", "Main Engine", "Fuel Injection Valve", "Overhaul", "41800", "2/E Lee", "4번 연료밸브 분사압력 재조정"],
    ["2024-06-20", "Main Engine", "Main Bearing #3", "Inspection", "43100", "C/E Park", "오일 간격 0.42mm, 정상"],
    ["2024-08-10", "Main Engine", "Main Bearing", "Inspection", "44050", "C/E Kim", "진동 증가 감지, 추가 모니터링 필요"],
    ["2024-09-02", "Main Engine", "Cylinder 4", "Inspection", "44600", "2/E Lee", "실린더 라이너 마모 측정"],
    ["2024-11-15", "Main Engine", "Cylinder 4 Piston Rings", "Replacement", "45200", "C/E Kim", "4번 실린더 피스톤 링 4개 전량 교체"],
    ["2025-01-08", "Main Engine", "Lubricating Oil", "Sampling", "46100", "3/E Choi", "시스템 오일 샘플 채취, BN 양호"],
    ["2025-02-19", "Main Engine", "Cylinder 2", "Overhaul", "46900", "C/E Kim", "피스톤 링 교체, 라이너 호닝"],
    ["2025-04-30", "Main Engine", "Main Bearing #3", "Inspection", "48200", "C/E Kim", "오일 간격 0.55mm, 마모 진행 관찰"],
    ["2025-05-22", "Main Engine", "Fuel Injection Valve", "Overhaul", "48800", "2/E Lee", "전 실린더 연료밸브 정비"],
    ["2025-07-14", "Main Engine", "Cylinder 6", "Inspection", "49900", "3/E Choi", "냉각수 공간 스케일 점검"],
    ["2025-09-03", "Main Engine", "Turbocharger", "Cleaning", "50800", "2/E Lee", "T/C 워터 워싱 실시"],
    ["2025-10-27", "Main Engine", "Cylinder 1 Piston Rings", "Replacement", "51600", "C/E Kim", "1번 실린더 피스톤 링 교체"],
    ["2026-01-15", "Main Engine", "Main Bearing #3", "Inspection", "52900", "C/E Kim", "오일 간격 0.68mm, 차기 입거시 교체 검토"],
    ["2026-03-08", "Main Engine", "Cylinder 4", "Inspection", "53700", "2/E Lee", "피스톤 링 갭 3.2mm, 한도 근접"],
    ["2026-05-19", "Main Engine", "Lubricating Oil Pump", "Maintenance", "54600", "3/E Choi", "윤활유 펌프 압력 2.0bar 확인"],
]


def make_pdf(path: Path) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(
        str(path), pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm,
        leftMargin=2 * cm, rightMargin=2 * cm,
    )
    flow = []
    for i, (title, body) in enumerate(MANUAL_PAGES):
        flow.append(Paragraph(title, styles["Title"] if i == 0 else styles["Heading2"]))
        flow.append(Spacer(1, 0.5 * cm))
        flow.append(Paragraph(body, styles["BodyText"]))
        if i != len(MANUAL_PAGES) - 1:
            flow.append(PageBreak())
    doc.build(flow)


def make_csv(path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)
        writer.writerows(CSV_ROWS)


if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = DATA_DIR / "manual.pdf"
    csv_path = DATA_DIR / "maintenance_logs.csv"
    make_pdf(pdf_path)
    make_csv(csv_path)
    print(f"[OK] 샘플 PDF 생성: {pdf_path} ({len(MANUAL_PAGES)} 페이지)")
    print(f"[OK] 샘플 CSV 생성: {csv_path} ({len(CSV_ROWS)} 행)")
