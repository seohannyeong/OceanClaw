# OceanClaw - 선박 정비 AI Agent (MVP)

OceanClaw는 선박 정비 현장에서 기술 매뉴얼 PDF와 정비 이력 CSV를 자연어로 검색하고, 출처가 포함된 답변을 제공하는 로컬 RAG 기반 AI Agent입니다.

현재 MVP는 Gemini 비용 없이 시작할 수 있도록 Ollama 기반 로컬 실행을 기본으로 합니다.

## 주요 기능

- PDF 기술 매뉴얼 검색
- CSV 정비 이력 검색
- FAISS 기반 로컬 벡터 인덱스
- Ollama 기반 로컬 임베딩 및 답변 생성
- 질문 유형별 검색 라우팅
  - 토크, 간격, 권장 주기, 절차 질문은 매뉴얼 중심 검색
  - 최근, 마지막, 이력, 작업자 질문은 정비 이력 중심 검색
  - 복합 질문은 매뉴얼과 정비 이력을 함께 검색
- 답변 본문에 출처 표시
  - `[매뉴얼 p.N]`
  - `[정비이력 #N]`

## 현재 범위

포함:

- 샘플 PDF 매뉴얼 1개
- 샘플 정비 이력 CSV 1개
- CLI 기반 질의응답
- Ollama 로컬 모델 연동
- FAISS 인덱스 생성 및 로드
- 검색 품질 개선용 쿼리 확장 및 재정렬

아직 포함하지 않음:

- Obsidian 호환 LLM Wiki 자동 생성
- Mattermost 연동
- 웹 UI
- LangChain Agent 기반 도구 자동 라우팅
- Docker 배포
- 실제 선박 매뉴얼/OCR 고도화

## 요구 사항

- Python 3.10 이상
- Ollama
- Windows PowerShell 기준 실행 예시 제공

Ollama 설치 후 다음 모델이 필요합니다.

```powershell
ollama pull nomic-embed-text
ollama pull gemma3:4b
```

역할:

- `nomic-embed-text`: PDF/CSV와 질문을 벡터로 변환
- `gemma3:4b`: 검색 결과를 바탕으로 한국어 답변 생성

## 빠른 시작

### 1. 가상환경 생성 및 패키지 설치

```powershell
cd C:\Users\서한녕\oceanclaw\OceanClaw

python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env.example`을 참고해 `.env`를 만듭니다.

```powershell
copy .env.example .env
```

Ollama 기본 설정 예시:

```env
LLM_PROVIDER=ollama

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_CHAT_MODEL=gemma3:4b
OLLAMA_EMBED_MODEL=nomic-embed-text

PDF_PATH=data/manual.pdf
CSV_PATH=data/maintenance_logs.csv
```

주의:

- `.env`는 개인 로컬 설정 파일입니다.
- API 키나 민감 정보는 `.env.example`에 넣지 마세요.
- `.env`는 `.gitignore`에 포함되어 GitHub에 올라가지 않습니다.

### 3. 샘플 데이터 생성

```powershell
.venv\Scripts\python scripts\make_sample_data.py
```

생성 파일:

```text
data/manual.pdf
data/maintenance_logs.csv
```

### 4. 인덱스 빌드

```powershell
.venv\Scripts\python build_index.py
```

생성 파일:

```text
index/pdf.faiss
index/pdf.json
index/csv.faiss
index/csv.json
```

인덱스 파일은 PDF/CSV 내용을 의미 검색용 벡터로 변환해 저장한 검색 캐시입니다. 질문할 때 매번 원본 문서를 처음부터 읽지 않고, 인덱스를 검색해 관련 문단과 행을 찾습니다.

### 5. 질문 실행

단건 질문:

```powershell
.venv\Scripts\python ask.py "메인 베어링 볼트의 초기 조임 토크 값은?"
```

대화형 실행:

```powershell
.venv\Scripts\python ask.py
```

## 예시 질문

```text
메인 베어링 볼트의 초기 조임 토크 값은?
메인 베어링 오일 간격 허용 한계는?
메인 베어링 권장 점검 주기는?
4번 실린더 피스톤 링 교체가 마지막으로 언제였지?
최근 메인 베어링 #3 상태는 어때?
지난 6개월간 메인 엔진 베어링 관련 문제가 있었나? 그리고 권장 교체 간격은?
```

예시 답변:

```text
초기 조임 토크 값은 150 Nm 입니다. [매뉴얼 p.3]
```

```text
2024년 11월 15일 [정비이력 #6]에 4번 실린더 피스톤 링 4개 전량 교체되었습니다.
```

## 검색 품질 개선 내용

초기 버전은 모든 질문에 대해 PDF와 CSV를 항상 함께 검색했습니다. 이 방식은 토크 값 질문에 정비 이력이 섞이고, 정비 이력 질문에 매뉴얼이 섞이는 문제가 있었습니다.

현재는 질문을 세 가지 경로로 라우팅합니다.

```text
manual - PDF 매뉴얼만 검색
logs   - CSV 정비이력만 검색
both   - PDF와 CSV를 함께 검색
```

또한 한국어 질문과 영어 매뉴얼을 잘 연결하기 위해 쿼리 확장을 적용합니다.

예:

```text
메인 베어링 -> main bearing main bearings
토크 -> torque tightening torque
간격 -> clearance oil clearance gap
피스톤 링 -> piston rings
교체 -> replacement renewal replace
```

CSV 정비 이력은 부품 번호, 작업 유형, 날짜 최신성 등을 기준으로 재정렬합니다.

예:

- `#3` 질문은 `Main Bearing #3` 행에 가산점
- `4번 실린더` 질문은 `Cylinder 4` 행에 가산점
- `교체` 질문은 `Replacement` 행에 가산점
- `최근`, `마지막` 질문은 최신 날짜에 가산점

PDF 매뉴얼도 질문 의도에 따라 재정렬합니다.

예:

- 토크 질문은 `Tightening Torque` 문서 우선
- 권장 주기 질문은 `Recommended Maintenance Intervals` 문서 우선
- 간격 질문은 `Clearance` 문서 우선

## 프로젝트 구조

```text
OceanClaw/
  ask.py                         질의응답 실행 진입점
  build_index.py                 인덱스 빌드 진입점
  requirements.txt               Python 의존성
  .env.example                   환경 변수 예시
  README.md                      프로젝트 설명

  oceanclaw/
    config.py                    환경 설정 로드
    ingest.py                    PDF/CSV 로딩 및 문서 변환
    vectorstore.py               FAISS 벡터 저장소
    llm.py                       LLM provider 선택
    ollama.py                    Ollama 로컬 모델 연동
    gemini.py                    Gemini provider 구현
    pipeline.py                  인덱스 빌드 및 질의응답 파이프라인
    cli.py                       CLI 출력 및 REPL

  scripts/
    make_sample_data.py          샘플 PDF/CSV 생성
```

## GitHub 업로드 주의 사항

다음 파일은 GitHub에 올리지 않습니다.

```text
.env
.venv/
data/*.pdf
data/*.csv
index/*.faiss
index/*.json
```

이유:

- `.env`: 개인 설정 및 API 키 포함 가능
- `.venv`: 로컬 가상환경
- `data/`: 실제 매뉴얼과 정비 이력은 민감 데이터일 수 있음
- `index/`: 원본 데이터에서 생성된 파생 파일

## 현재 한계

- 샘플 PDF는 텍스트 기반 PDF만 처리합니다.
- 스캔 PDF나 표/도면 OCR은 아직 처리하지 않습니다.
- 답변 생성 모델이 검색된 근거의 일부 수치를 생략할 수 있습니다.
- 검색 라우팅은 현재 규칙 기반입니다.
- 실제 선박 데이터 적용 전에는 데이터 보안 검토가 필요합니다.

## 다음 개발 계획

1. 테스트 질문 세트 작성
   - 기관장 수준 질문 10개부터 시작
   - 기대 답변과 기대 출처를 함께 기록

2. 답변 생성 프롬프트 개선
   - 허용/최대/최소/한계 질문에서 관련 수치를 빠뜨리지 않도록 강화

3. LLM Wiki 생성
   - PDF/CSV 내용을 Obsidian 호환 Markdown으로 구조화
   - 예: `wiki/Main Bearing.md`, `wiki/Piston Rings.md`

4. Agent 구조 확장
   - `search_manual`
   - `search_logs`
   - `search_wiki`
   - 질문 의도별 도구 자동 선택

5. Mattermost/OceanClaw 연동
   - 현장 채널에서 질문
   - 증상별 스레드 관리
   - 출처 포함 답변 제공
