# OceanClaw Project Structure

## 전체 구조

```text
OceanClaw/
  README.md
  PLAN.md
  requirements.txt
  .env.example
  .gitignore

  oceanclaw/
    config.py
    pdf_extract.py
    chunk.py
    ollama_embed.py
    ollama_chat.py
    vectorstore.py
    query_expansion.py
    answer.py

  scripts/
    extract_pdf.py
    chunk_pdf.py
    build_index.py
    search.py
    ask.py
    convert_sensor_events.py
    build_sensor_index.py
    search_sensor.py

  data/
    raw/
      yanmar_6lf_operation_manual.pdf
      data.csv
    interim/
      pdf_pages.jsonl
    processed/
      pdf_chunks.jsonl
      sensor_events.csv

  index/
    pdf.faiss
    pdf_docs.json
    sensor.faiss
    sensor_docs.json

  docs/
    project_structure.md
    search_eval_2026-07-24.md
```

## 폴더 역할

### `oceanclaw/`

실제 기능 코드가 들어있는 폴더입니다. 다른 스크립트, API 서버, Mattermost 봇에서 재사용할 수 있는 핵심 로직입니다.

| 파일 | 역할 |
| --- | --- |
| `config.py` | 프로젝트 경로, Ollama 모델명, index 경로 등 설정 |
| `pdf_extract.py` | PDF를 페이지별 텍스트 JSONL로 추출 |
| `chunk.py` | 페이지 텍스트를 RAG chunk로 분할 |
| `ollama_embed.py` | Ollama embedding API 호출 |
| `ollama_chat.py` | Ollama chat API 호출 |
| `vectorstore.py` | FAISS index 생성, 저장, 로드, 검색 |
| `query_expansion.py` | 한국어 질문을 영어 검색어로 확장 |
| `answer.py` | 검색 결과를 context로 묶고 답변 생성 |

### `scripts/`

터미널에서 직접 실행하는 파일입니다. 쉽게 말해 `oceanclaw/` 기능을 실행하는 버튼입니다.

| 파일 | 실행 목적 |
| --- | --- |
| `extract_pdf.py` | PDF를 `pdf_pages.jsonl`로 추출 |
| `chunk_pdf.py` | `pdf_pages.jsonl`을 `pdf_chunks.jsonl`로 변환 |
| `build_index.py` | PDF chunk를 embedding해서 `pdf.faiss` 생성 |
| `search.py` | PDF FAISS index 검색 |
| `ask.py` | PDF 검색 결과 기반으로 한국어 답변 생성 |
| `convert_sensor_events.py` | 원본 센서 CSV를 `sensor_events.csv`로 변환 |
| `build_sensor_index.py` | sensor event를 embedding해서 `sensor.faiss` 생성 |
| `search_sensor.py` | sensor FAISS index 검색 |

### `data/`

입력 데이터와 중간 산출물을 보관합니다.

| 경로 | 설명 |
| --- | --- |
| `data/raw/` | 원본 PDF, 원본 CSV |
| `data/interim/` | 원본에서 바로 추출한 중간 파일 |
| `data/processed/` | 검색/인덱싱에 쓰는 가공 파일 |

### `index/`

FAISS index와 문서 메타데이터를 저장합니다.

| 파일 | 설명 |
| --- | --- |
| `pdf.faiss` | PDF chunk embedding index |
| `pdf_docs.json` | PDF chunk 원문과 메타데이터 |
| `sensor.faiss` | sensor event embedding index |
| `sensor_docs.json` | sensor event 원문과 메타데이터 |

## 실행 순서

### PDF RAG

```powershell
python scripts/extract_pdf.py
python scripts/chunk_pdf.py
python scripts/build_index.py
python scripts/search.py "engine oil level check" --top-k 3
python scripts/ask.py "엔진 오일 점검 방법 알려줘" --top-k 3
```

### Sensor Event 검색

```powershell
python scripts/convert_sensor_events.py
python scripts/build_sensor_index.py
python scripts/search_sensor.py "GT compressor decay warning" --top-k 3
```

## 현재 완료된 기능

- PDF 페이지별 텍스트 추출
- PDF chunk 생성
- Ollama embedding
- FAISS dense retrieval
- 한국어 query expansion
- PDF 검색 기반 한국어 답변 생성
- sensor CSV를 점검 이벤트 CSV로 변환
- sensor event FAISS 검색

## 아직 남은 작업

- PDF 검색과 sensor 검색을 하나의 `ask.py`에서 통합
- 질문 의도에 따라 manual/sensor 검색 라우팅
- sensor 검색 결과 기반 답변 생성
- 검색 평가 자동화
- 답변 품질 개선
- LLM Wiki 생성
- Jetson Orin Nano 배포 테스트
