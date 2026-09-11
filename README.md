# OceanClaw

OceanClaw는 선박 정비 매뉴얼 PDF, 센서 이벤트 CSV, Obsidian Wiki 문서를 검색해 근거 기반 답변을 생성하는 로컬 RAG 기반 선박 정비 AI Agent입니다.

Ollama 기반 로컬 LLM, FAISS vector search, FastAPI, Mattermost Slash Command, Obsidian 호환 Wiki 구조를 사용합니다.

프로젝트 폴더 구조와 파일별 역할은 [docs/project_structure.md](docs/project_structure.md)를 참고하세요.

## 현재 기본 검색 방식 (2026-09-11)

- 매뉴얼: PDF 제목 + 청크 본문을 BGE-M3로 임베딩하고 한국어 질문 원문으로 Top-3 검색합니다. 기본 경로에서는 번역과 규칙 기반 query expansion을 사용하지 않습니다.
- 인덱스: `index/manual_titles/pdf.faiss`, `index/manual_titles/pdf_docs.json`. 기존 실험 인덱스는 보존합니다.
- `/ask`, `/search/manual`, CLI, Web UI, Mattermost, Wiki 생성의 매뉴얼 검색에 적용됩니다. 센서와 Wiki 인덱스는 기존 nomic 방식을 유지합니다.
- 인접 문맥은 기본 비활성화입니다. API에서 `manual_profile=titles_neighbors`로 선택할 수 있으며, `legacy`는 이전 방식입니다.
- 경로를 생략하면 매뉴얼과 센서를 함께 검색합니다. 서로 다른 임베딩 모델의 점수로 경로를 비교하지 않습니다. 매뉴얼만 필요하면 `--route manual` 또는 API의 `route=manual`을 사용하세요.
- 명시한 Top-K와 환경변수는 유지됩니다. 기존 `.env`의 `MATTERMOST_TOP_K=2`를 사용하는 경우 3으로 바꾸려면 직접 수정하세요.
- Jetson에는 변경 코드와 `index/manual_titles`를 함께 반영하고 API를 재시작해야 합니다. 이전 측정용 ZIP에는 이번 변경이 포함되어 있지 않습니다.

## 1. 로컬 실행 준비

프로젝트 폴더로 이동합니다.

```powershell
cd C:\Users\서한녕\oceanclaw\OceanClaw
```

가상환경을 생성하고 실행합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

패키지를 설치합니다.

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

환경변수 파일을 준비합니다.

```powershell
Copy-Item .env.example .env
```

`.env`에서 필요한 값을 수정합니다. Mattermost token 같은 민감한 값은 `.env`에만 넣고 GitHub에는 올리지 않습니다.

## 2. Ollama 모델 설치

Ollama를 설치한 뒤 서버가 실행 중인지 확인합니다.

```powershell
ollama --version
```

채팅 모델과 임베딩 모델을 내려받습니다.

```powershell
ollama pull gemma3:4b
ollama pull bge-m3
ollama pull nomic-embed-text
```

모델이 정상 동작하는지 확인합니다.

```powershell
ollama run gemma3:4b
```

`.env` 기본값은 다음과 같습니다.

```env
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_CHAT_MODEL=gemma3:4b
OLLAMA_EMBED_MODEL=nomic-embed-text
TITLED_MANUAL_INDEX_DIR=index/manual_titles
OLLAMA_TIMEOUT=60
```

Jetson처럼 응답이 느린 환경에서는 `OLLAMA_TIMEOUT=300` 정도로 늘리는 것을 권장합니다.

## 3. 데이터와 인덱스 생성 순서

현재 기본 입력 파일은 다음 위치를 사용합니다.

```text
data/raw/yanmar_6lf_operation_manual.pdf
data/raw/data.csv
```

처음 실행하거나 데이터가 바뀐 경우 아래 순서대로 실행합니다.

### PDF 매뉴얼 인덱스

```powershell
python scripts\extract_pdf.py
python scripts\chunk_pdf.py
python scripts\build_index.py
```

결과물:

```text
data/interim/pdf_pages.jsonl
data/processed/pdf_chunks.jsonl
index/manual_titles/pdf.faiss
index/manual_titles/pdf_docs.json
```

이미 제공된 제목 인덱스가 있으면 재생성할 필요가 없습니다. 데이터 변경 후 재생성은 `python scripts\build_index.py --overwrite`로 실행합니다. 기존 본문 전용 인덱스 생성은 `--legacy` 옵션으로만 실행됩니다. 제목 없는 PDF 구간은 본문만 임베딩되며, 제목 매칭 결과는 `heading_audit.json`에 저장됩니다.

검색 확인:

```powershell
python scripts\search.py "엔진 오일 점검 방법" --top-k 3
```

이전 검색은 `--profile legacy`로 선택합니다. 검색의 `--faiss`, `--docs`, `--model`은 legacy 전용이며 제목 검색 인덱스 위치는 `--index-dir`로 지정합니다.

### Sensor 인덱스

```powershell
python scripts\convert_sensor_events.py
python scripts\build_sensor_index.py
```

결과물:

```text
data/processed/sensor_events.csv
index/sensor.faiss
index/sensor_docs.json
```

검색 확인:

```powershell
python scripts\search_sensor.py "engine temperature high warning" --top-k 3
```

### Wiki 인덱스

```powershell
python scripts\build_wiki_index.py
```

결과물:

```text
data/processed/wiki_chunks.jsonl
index/wiki.faiss
index/wiki_docs.json
```

검색 확인:

```powershell
python scripts\search_wiki.py "엔진 오일 점검" --top-k 3
```

## 4. CLI로 질문하기

통합 RAG 답변:

```powershell
python scripts\ask.py "엔진 오일 점검 방법 알려줘" --route all --top-k 3
```

답변을 Obsidian Wiki log로 저장:

```powershell
python scripts\ask.py "엔진 오일 점검 방법 알려줘" --route all --top-k 3 --save-log
```

검색 경로는 다음 중 선택할 수 있습니다.

```text
manual
sensor
wiki
both
all
```

## 5. Wiki 문서 생성

검색된 근거를 바탕으로 Obsidian에서 열 수 있는 Markdown 문서를 생성합니다.

```powershell
python scripts\create_wiki_note.py "엔진 오일 점검" --route all --top-k 3
```

문서 유형을 직접 지정할 수도 있습니다.

```powershell
python scripts\create_wiki_note.py "엔진 오일 점검" --type procedure
python scripts\create_wiki_note.py "GT compressor warning" --type log --route sensor
```

문서 생성 후 Wiki 검색 인덱스까지 바로 갱신하려면:

```powershell
python scripts\create_wiki_note.py "엔진 오일 점검" --rebuild-index
```

생성된 문서는 기본적으로 `wiki/procedures`, `wiki/components`, `wiki/logs` 중 적절한 폴더에 저장됩니다.

## 6. FastAPI 서버와 Web UI

로컬 PC에서만 사용할 때:

```powershell
python scripts\run_api.py --host 127.0.0.1 --port 8000
```

같은 네트워크의 다른 기기에서도 접속하게 할 때:

```powershell
python scripts\run_api.py --host 0.0.0.0 --port 8000
```

브라우저에서 Web UI를 엽니다.

```text
http://127.0.0.1:8000
```

API 문서는 다음 주소에서 확인합니다.

```text
http://127.0.0.1:8000/docs
```

주요 endpoint:

```text
GET  /health
POST /ask
POST /search/manual
POST /search/sensor
POST /search/wiki
POST /wiki/notes
POST /mattermost/slash
POST /mattermost/wiki-note
```

## 7. Mattermost 사용법

OceanClaw API 서버를 먼저 실행합니다.

```powershell
python scripts\run_api.py --host 0.0.0.0 --port 8000
```

Mattermost가 Docker에서 실행 중이면 Slash Command의 Request URL은 보통 다음처럼 설정합니다.

```text
http://host.docker.internal:8000/mattermost/slash
```

질문 답변용 Slash Command:

```text
Title: OceanClaw
Command Trigger Word: oceanclaw
Request URL: http://host.docker.internal:8000/mattermost/slash
Request Method: POST
```

Wiki 문서 생성용 Slash Command:

```text
Title: OceanClaw Wiki Note
Command Trigger Word: oceanclaw-note
Request URL: http://host.docker.internal:8000/mattermost/wiki-note
Request Method: POST
```

`.env`에는 Mattermost token을 넣습니다.

```env
MATTERMOST_SLASH_TOKEN=your-slash-command-token
MATTERMOST_RESPONSE_TYPE=ephemeral
MATTERMOST_DEFAULT_ROUTE=all
MATTERMOST_TOP_K=2
MATTERMOST_SAVE_LOG=true
MATTERMOST_WIKI_NOTE_ROUTE=all
MATTERMOST_WIKI_NOTE_TOP_K=3
MATTERMOST_WIKI_NOTE_REBUILD_INDEX=false
```

Mattermost 채팅창에서 테스트합니다.

```text
/oceanclaw 엔진 오일 점검 방법 알려줘
/oceanclaw-note 엔진 오일 점검
```

Docker Mattermost에서 로컬 PC의 API를 호출할 때 막히면 Mattermost System Console에서 `AllowedUntrustedInternalConnections`에 다음 값을 허용해야 할 수 있습니다.

```text
host.docker.internal
```

## 8. Jetson 실행 방법

Jetson에서 프로젝트를 받은 뒤 폴더로 이동합니다.

```bash
cd ~/OceanClaw
```

가상환경을 만들고 패키지를 설치합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Ollama 모델을 설치합니다.

```bash
ollama pull gemma3:4b
ollama pull nomic-embed-text
```

Jetson은 응답이 느릴 수 있으므로 timeout을 늘립니다.

```bash
export OLLAMA_TIMEOUT=300
```

서버를 외부 접속 가능하게 실행합니다.

```bash
python scripts/run_api.py --host 0.0.0.0 --port 8000
```

Jetson IP를 확인합니다.

```bash
hostname -I
```

데스크탑에서 접속합니다.

```text
http://<Jetson-IP>:8000
http://<Jetson-IP>:8000/docs
```

접속이 안 되면 먼저 ping으로 네트워크 연결을 확인합니다.

```powershell
ping <Jetson-IP>
```

## 9. 현재 구현 상태

- PDF 텍스트 추출 및 JSONL 저장
- LangChain 기반 chunk 분할
- Ollama embedding 기반 문서 vector 변환
- FAISS 기반 manual, sensor, wiki 검색
- 한국어 질문과 영어 매뉴얼 검색을 보완하는 query expansion
- Ollama chat 기반 RAG 답변 생성
- 답변 출처와 검색 근거 제공
- 답변 결과를 `wiki/logs`에 자동 저장
- Obsidian 호환 Wiki 폴더 구조
- RAG 근거 기반 Wiki Markdown 문서 생성
- FastAPI API 서버
- 브라우저 Web UI
- Mattermost Slash Command 답변 연동
- Mattermost Wiki 문서 생성 명령 연동
- Jetson Orin Nano 실행 구조

## 10. GitHub 업로드 주의사항

다음 파일은 보안상 GitHub에 올리지 않습니다.

```text
.env
.venv/
```

임시 파일, 영상 결과물, 테스트 산출물은 필요한 경우에만 선택해서 올립니다.

```text
tmp/
output/video/
```

전체 파일을 무조건 `git add .` 하기보다, 커밋할 파일을 확인한 뒤 올리는 것을 권장합니다.

```powershell
git status
git add README.md oceanclaw static scripts .env.example requirements.txt
git commit -m "웹 UI 및 실행 문서 정리"
```
