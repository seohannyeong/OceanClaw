# OceanClaw

선박 정비 매뉴얼과 선박 추진 센서 이벤트를 검색하는 Offline-First AI Agent 프로젝트입니다.

프로젝트 폴더 구조와 파일별 역할은 [docs/project_structure.md](docs/project_structure.md)를 참고하세요.

## 빠른 실행

### 1. PDF RAG

```powershell
python scripts/extract_pdf.py
python scripts/chunk_pdf.py
python scripts/build_index.py
python scripts/search.py "engine oil level check" --top-k 3
python scripts/ask.py "엔진 오일 점검 방법 알려줘" --top-k 3
```

### 2. Sensor Event 검색

```powershell
python scripts/convert_sensor_events.py
python scripts/build_sensor_index.py
python scripts/search_sensor.py "GT compressor decay warning" --top-k 3
```

## 주요 산출물

```text
data/interim/pdf_pages.jsonl
data/processed/pdf_chunks.jsonl
data/processed/sensor_events.csv
index/pdf.faiss
index/pdf_docs.json
index/sensor.faiss
index/sensor_docs.json
```

## 현재 상태

- PDF 기반 RAG v1 구현 완료
- Ollama embedding + FAISS 검색 구현 완료
- 한국어 query expansion 구현 완료
- Ollama chat 기반 답변 생성 구현 완료
- sensor event CSV 변환 및 검색 구현 완료

## 다음 작업

- PDF 검색과 sensor 검색 통합
- 질문 의도 기반 라우팅
- sensor event 기반 답변 생성
- 검색/답변 평가 자동화
