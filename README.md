# OceanClaw

선박 정비 매뉴얼 PDF와 센서 이벤트 CSV를 검색해서 답변하는 Offline-First AI Agent 프로젝트입니다.

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

### 3. 통합 질문 답변

```powershell
python scripts/ask.py "엔진 오일 점검 방법 알려줘" --top-k 3
python scripts/ask.py "GT compressor warning 이벤트 보여줘" --top-k 3
python scripts/ask.py "GT compressor warning 이벤트와 관련 매뉴얼 같이 알려줘" --route both --top-k 2
python scripts/ask.py "엔진 오일 점검 방법 알려줘" --route wiki --top-k 2
python scripts/ask.py "엔진 오일 점검 방법 알려줘" --route all --top-k 1
python scripts/ask.py "엔진 오일 점검 방법 알려줘" --route all --top-k 1 --save-log
```

Jetson처럼 응답이 느린 환경에서는 timeout을 늘려 실행합니다.

```bash
export OLLAMA_TIMEOUT=300
python scripts/ask.py "엔진 오일 점검 방법 알려줘" --top-k 1 --route manual
```

### 4. API 서버 실행

로컬 PC에서만 접속할 때:

```powershell
python scripts/run_api.py --host 127.0.0.1 --port 8000
```

같은 네트워크의 다른 기기에서 접속할 때:

```powershell
python scripts/run_api.py --host 0.0.0.0 --port 8000
```

브라우저에서 확인:

```text
http://127.0.0.1:8000/docs
http://<Jetson-IP>:8000/docs
```

### 5. Wiki 문서 생성

```powershell
python scripts/generate_wiki.py "엔진 오일 점검" --route manual --type procedure
python scripts/generate_wiki.py "GT compressor warning" --route sensor --type log
```

### 6. Wiki 검색

```powershell
python scripts/build_wiki_index.py
python scripts/search_wiki.py "엔진 오일 점검" --top-k 3
```

### 7. Mattermost Slash Command

OceanClaw API 서버를 켠 뒤 Mattermost custom slash command의 Request URL을
`http://<server-ip>:8000/mattermost/slash`로 설정합니다.

`.env`에는 Mattermost에서 발급한 token을 저장합니다.

```env
MATTERMOST_SLASH_TOKEN=your-slash-command-token
MATTERMOST_RESPONSE_TYPE=ephemeral
MATTERMOST_DEFAULT_ROUTE=all
MATTERMOST_TOP_K=2
MATTERMOST_SAVE_LOG=true
```

Mattermost에서 사용하는 명령어 예시:

```text
/oceanclaw 엔진 오일 점검 방법 알려줘
```

로컬 테스트 예시:

```powershell
curl.exe -X POST http://127.0.0.1:8000/mattermost/slash `
  -H "Content-Type: application/x-www-form-urlencoded" `
  -d "token=your-slash-command-token&text=엔진 오일 점검 방법 알려줘"
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
index/wiki.faiss
index/wiki_docs.json
wiki/
```

## 현재 상태

- PDF 텍스트 추출 구현 완료
- LangChain Text Splitter 기반 PDF chunk 생성 구현 완료
- Ollama embedding + FAISS 검색 구현 완료
- 한국어 query expansion 구현 완료
- Sensor event CSV 변환 및 검색 구현 완료
- PDF 검색과 sensor 검색 통합 완료
- Wiki 검색 결과를 `/ask` 답변 context에 포함하는 route 구현 완료
- Ollama chat 기반 답변 생성 구현 완료
- Jetson 실행을 고려해 Ollama 기본 timeout 300초 적용
- FastAPI 기반 외부 접속 API 구현 완료
- Obsidian 호환 LLM Wiki 기본 구조 생성 완료
- RAG 근거 기반 Wiki Markdown 자동 생성 구현 완료
- Wiki Markdown FAISS 검색 구현 완료
- 질문/답변/출처를 `wiki/logs/`에 자동 저장하는 기능 구현 완료
- Mattermost Slash Command endpoint 구현 완료

## 다음 작업

- Mattermost 서버에서 custom slash command 등록 및 실제 채널 테스트
- sensor event 중복 결과 요약 개선
- Jetson Orin Nano 배포 테스트
- FastAPI 서버를 Jetson에서 `0.0.0.0:8000`으로 실행하고 외부 접속 확인
