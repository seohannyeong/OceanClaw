# OceanClaw Project Structure

## 전체 구조

```text
OceanClaw/
  README.md
  PLAN.md
  requirements.txt
  .gitignore

  oceanclaw/
    config.py
    pdf_extract.py
    chunk.py
    ollama_embed.py
    ollama_chat.py
    vectorstore.py
    query_expansion.py
    router.py
    answer.py
    api.py

  scripts/
    extract_pdf.py
    chunk_pdf.py
    build_index.py
    search.py
    convert_sensor_events.py
    build_sensor_index.py
    search_sensor.py
    ask.py
    run_api.py
    generate_wiki.py
    build_wiki_index.py
    search_wiki.py

  data/
    raw/
    interim/
    processed/

  index/
    pdf.faiss
    pdf_docs.json
    sensor.faiss
    sensor_docs.json
    wiki.faiss
    wiki_docs.json

  wiki/
    README.md
    components/
    procedures/
    logs/
    templates/

  docs/
    project_structure.md
    search_eval_2026-07-24.md
```

## 핵심 폴더

### `oceanclaw/`

실제 기능 코드가 들어있는 폴더입니다. CLI, API 서버, 향후 Mattermost 봇에서 재사용할 핵심 로직입니다.

| 파일 | 역할 |
| --- | --- |
| `config.py` | 프로젝트 경로, 모델명, index 경로 설정 |
| `pdf_extract.py` | PDF를 페이지별 텍스트 JSONL로 추출 |
| `chunk.py` | LangChain Text Splitter 기반 chunk 생성 |
| `ollama_embed.py` | Ollama embedding API 호출 |
| `ollama_chat.py` | Ollama chat API 호출 |
| `vectorstore.py` | FAISS index 생성, 저장, 로드, 검색 |
| `query_expansion.py` | 한국어 질문을 영어 검색어로 확장 |
| `router.py` | manual/sensor 검색 점수 기반 route 결정 |
| `answer.py` | 검색 결과를 context로 묶고 답변 생성 |
| `api.py` | FastAPI 기반 HTTP API |

### `scripts/`

터미널에서 직접 실행하는 진입점입니다.

| 파일 | 실행 목적 |
| --- | --- |
| `extract_pdf.py` | PDF를 `pdf_pages.jsonl`로 추출 |
| `chunk_pdf.py` | `pdf_pages.jsonl`을 `pdf_chunks.jsonl`로 변환 |
| `build_index.py` | PDF chunk를 embedding해서 `pdf.faiss` 생성 |
| `search.py` | PDF FAISS index 검색 |
| `convert_sensor_events.py` | 원본 sensor CSV를 OceanClaw event CSV로 변환 |
| `build_sensor_index.py` | sensor event를 embedding해서 `sensor.faiss` 생성 |
| `search_sensor.py` | sensor FAISS index 검색 |
| `ask.py` | manual/sensor 통합 RAG 답변 생성 |
| `run_api.py` | FastAPI 서버 실행 |
| `generate_wiki.py` | 검색 근거 기반 Obsidian Markdown Wiki 문서 생성 |
| `build_wiki_index.py` | Wiki Markdown chunk 생성 및 FAISS index 생성 |
| `search_wiki.py` | Wiki FAISS index 검색 |

### `wiki/`

계획서의 LLM Wiki와 Obsidian Vault 요구사항을 만족하기 위한 Markdown 지식 저장소입니다.

| 경로 | 설명 |
| --- | --- |
| `wiki/components/` | 부품, 계통, 장비별 지식 문서 |
| `wiki/procedures/` | 점검, 정비, 운전 절차 문서 |
| `wiki/logs/` | 센서 이벤트와 정비 이력 요약 문서 |
| `wiki/templates/` | Wiki 문서 작성 템플릿 |

## 실행 순서

### PDF RAG

```powershell
python scripts/extract_pdf.py
python scripts/chunk_pdf.py
python scripts/build_index.py
python scripts/search.py "engine oil level check" --top-k 3
```

### Sensor Event 검색

```powershell
python scripts/convert_sensor_events.py
python scripts/build_sensor_index.py
python scripts/search_sensor.py "GT compressor decay warning" --top-k 3
```

### 통합 질문 답변

```powershell
python scripts/ask.py "엔진 오일 점검 방법 알려줘" --top-k 3
```

### Wiki 문서 생성

```powershell
python scripts/generate_wiki.py "엔진 오일 점검" --route manual --type procedure
```

### Wiki 검색

```powershell
python scripts/build_wiki_index.py
python scripts/search_wiki.py "엔진 오일 점검" --top-k 3
```

### API 서버

```powershell
python scripts/run_api.py --host 127.0.0.1 --port 8000
```

외부 접속이 필요하면 Jetson 또는 서버 장비에서:

```powershell
python scripts/run_api.py --host 0.0.0.0 --port 8000
```

## 완료된 기능

- PDF 페이지별 텍스트 추출
- LangChain Text Splitter 기반 PDF chunk 생성
- Ollama embedding
- FAISS dense retrieval
- 한국어 query expansion
- sensor CSV를 점검 이벤트 CSV로 변환
- sensor event FAISS 검색
- manual/sensor 통합 RAG 답변 생성
- FastAPI 서버
- Obsidian 호환 Wiki 기본 구조
- RAG 근거 기반 Wiki Markdown 자동 생성
- Wiki Markdown FAISS 검색

## 남은 작업

- manual/sensor/wiki 통합 RAG 답변 생성
- `search_manual`, `search_sensor`, `search_wiki` tool 구조 정리
- Mattermost 연동
- Jetson Orin Nano 배포 테스트
- 검색/답변 평가 자동화
