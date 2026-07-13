#!/usr/bin/env python3
"""인덱스 빌드 진입점: PDF/CSV를 임베딩해 FAISS 인덱스 생성.

사용법:
    python build_index.py
"""

from oceanclaw.pipeline import build_index

if __name__ == "__main__":
    print("[START] 인덱스 빌드 시작...")
    try:
        stats = build_index()
    except Exception as exc:
        print(f"[ERROR] 인덱스 빌드 실패: {exc}")
        raise SystemExit(1) from exc
    else:
        print(f"[OK] 완료: PDF 청크 {stats['pdf_chunks']}개 / CSV 행 {stats['csv_rows']}개 인덱싱")
        print("   이제 질문하세요:  python ask.py")
