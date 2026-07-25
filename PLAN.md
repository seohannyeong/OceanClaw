# OceanClaw 개발 계획서

## 1. 프로젝트 목표

OceanClaw는 선박 기관실에서 기관사와 정비사가 방대한 영문 기술 매뉴얼과 과거 정비 이력을 빠르게 조회할 수 있도록 돕는 선박 정비 AI Agent이다.

핵심 목표는 다음과 같다.

- 선박 기술 매뉴얼 PDF를 한국어 자연어로 검색한다.
- CSV 또는 DB 기반 정비 이력을 자연어로 조회한다.
- 모든 답변에 PDF 페이지, CSV 행, Wiki 문서 등 출처를 명시한다.
- 인터넷이 불안정한 선박 환경을 고려해 Ollama 기반 로컬 LLM을 우선 지원한다.
- 최종적으로 NVIDIA Jetson Orin Nano에서 구동 가능한 경량 배포 구조를 만든다.

## 2. 핵심 사용자 시나리오

### 2.1 기술 스펙 확인

기관장이 다음과 같이 질문한다.

```text
메인 베어링 볼트의 초기 조임 토크 값은?
```

시스템은 매뉴얼 또는 Wiki에서 관련 내용을 검색하고 다음 형태로 답변한다.

```text
메인 베어링 볼트의 초기 조임 토크 값은 150 Nm입니다.
출처: 매뉴얼 p.142
```

### 2.2 과거 정비 이력 조회

정비사가 다음과 같이 질문한다.

```text
4번 실린더 피스톤 링 교체가 마지막으로 언제였지?
```

시스템은 정비 이력 CSV 또는 DB를 검색해 날짜, Running Hours, 작업자, 조치 내용을 반환한다.

### 2.3 복합 질의

기관장이 다음과 같이 질문한다.

```text
지난 6개월간 메인 엔진 베어링 관련 문제가 있었나?
그리고 권장 교체 간격은?
```

시스템은 정비 이력과 매뉴얼을 함께 검색해 과거 문제 기록과 권장 점검 주기를 종합한다.

## 3. 전체 아키텍처

```text
PDF 매뉴얼
  -> 페이지별 텍스트 추출
  -> chunk 생성
  -> embedding
  -> FAISS index
  -> 검색

CSV 정비 이력
  -> row 단위 문서화
  -> embedding 또는 조건 검색
  -> 검색

질문
  -> 질문 의도 분석
  -> 매뉴얼 검색 / 이력 검색 / Wiki 검색
  -> 근거 문서 수집
  -> Ollama LLM 답변 생성
  -> 출처 포함 답변 반환
```

초기 버전에서는 LangChain과 Mattermost를 바로 넣지 않는다. 먼저 단순하고 검증 가능한 RAG 파이프라인을 만든 뒤, 기능이 안정되면 Agent와 UI 연동을 추가한다.

## 4. 개발 단계

### 4.1 1단계: 프로젝트 뼈대 재구성

목표는 코드 흐름이 섞이지 않는 최소 구조를 만드는 것이다.

예상 폴더 구조:

```text
OceanClaw/
  README.md
  PLAN.md
  requirements.txt
  .env.example
  data/
    raw/
    interim/
    processed/
  index/
  oceanclaw/
    config.py
    pdf_extract.py
    chunk.py
    embed.py
    vectorstore.py
    search.py
    answer.py
  scripts/
    extract_pdf.py
    chunk_pdf.py
    build_index.py
    ask.py
    run_eval.py
```

원칙:

- PDF 추출은 `pdf_extract.py`에서만 담당한다.
- chunk 생성은 `chunk.py`에서만 담당한다.
- embedding은 `embed.py`에서만 담당한다.
- 검색은 `search.py`에서만 담당한다.
- 답변 생성은 `answer.py`에서만 담당한다.
- 실행용 파일은 `scripts/`에 둔다.

### 4.2 2단계: PDF 처리 파이프라인

목표는 PDF가 잘 읽히는지 눈으로 확인 가능한 JSONL 결과물을 만드는 것이다.

처리 흐름:

```text
data/raw/manual.pdf
  -> data/interim/pdf_pages.jsonl
  -> data/processed/pdf_chunks.jsonl
```

`pdf_pages.jsonl` 형식:

```json
{"source": "manual.pdf", "page": 1, "text": "..."}
```

`pdf_chunks.jsonl` 형식:

```json
{"source": "manual.pdf", "page": 1, "chunk_id": "manual-p1-c0", "text": "..."}
```

이 단계에서는 `pypdf`를 우선 사용한다. 단, 스캔 PDF처럼 텍스트 레이어가 없는 문서는 OCR이 필요할 수 있으므로 추후 OCR 옵션을 따로 검토한다.

### 4.3 3단계: CSV 정비 이력 처리

목표는 정비 이력을 검색 가능한 문서로 바꾸는 것이다.

처리 흐름:

```text
data/raw/maintenance_logs.csv
  -> data/interim/log_rows.jsonl
  -> data/processed/log_docs.jsonl
```

`log_docs.jsonl` 형식:

```json
{
  "source": "maintenance_logs.csv",
  "row": 1,
  "text": "date: 2024-11-15; component: Cylinder #4; action: piston ring replacement",
  "raw": {}
}
```

초기에는 row 단위 검색으로 시작하고, 이후 날짜 필터, 부품명 필터, Running Hours 필터를 추가한다.

### 4.4 4단계: Embedding 및 FAISS Index

목표는 로컬에서 검색 가능한 벡터 인덱스를 만드는 것이다.

우선순위:

1. Ollama embedding 모델 사용
2. FAISS CPU index 저장
3. PDF index와 CSV index를 분리 저장

예상 산출물:

```text
index/pdf.faiss
index/pdf_docs.json
index/logs.faiss
index/log_docs.json
```

Jetson Orin Nano에서는 GPU 메모리와 RAM 제약이 있으므로, 처음부터 작은 embedding 모델과 CPU 기반 FAISS를 기준으로 설계한다.

### 4.5 5단계: 검색 및 답변 생성

목표는 사용자가 질문하면 관련 문서를 찾고 한국어 답변을 생성하는 것이다.

처리 흐름:

```text
질문 입력
  -> query embedding
  -> PDF 검색
  -> CSV 검색
  -> 검색 결과 정렬
  -> Ollama 답변 생성
  -> 출처 표시
```

답변 원칙:

- 검색된 근거 안에서만 답변한다.
- 확실하지 않으면 모른다고 답한다.
- 기술 수치에는 단위와 출처를 붙인다.
- 정비 이력에는 날짜, Running Hours, 작업자를 함께 표시한다.

### 4.6 6단계: 평가 자동화

목표는 답변이 잘 나오는지 감으로 보지 않고 질문 세트로 검증하는 것이다.

평가 파일:

```text
eval/questions.csv
```

예상 컬럼:

```csv
question,expected_source,expected_keyword
```

평가 항목:

- 정답 키워드 포함 여부
- 출처 포함 여부
- PDF 페이지 검색 성공 여부
- CSV 행 검색 성공 여부
- 환각 답변 여부

최소 30개 질문 세트를 목표로 한다.

### 4.7 7단계: LLM Wiki

목표는 단순 RAG를 넘어 선박 지식을 Markdown Wiki로 자산화하는 것이다.

예상 구조:

```text
wiki/
  components/
    main_bearing.md
    cylinder_4.md
  procedures/
    piston_ring_replacement.md
  logs/
    2024-11-15_cylinder_4_piston_ring.md
```

Wiki 문서는 Obsidian 호환 Markdown으로 작성한다.

문서 안에는 다음 정보를 포함한다.

- 부품명
- 주요 스펙
- 정비 절차
- 관련 정비 이력
- 원본 PDF 페이지 출처
- 관련 문서 링크

### 4.8 8단계: Agent화

목표는 사용자의 질문 의도에 따라 적절한 도구를 자동 선택하게 하는 것이다.

도구 후보:

- `search_manual`: PDF 매뉴얼 검색
- `search_logs`: 정비 이력 검색
- `search_wiki`: LLM Wiki 검색

초기에는 직접 만든 라우팅 규칙으로 시작하고, 이후 LangChain Agent로 확장한다.

### 4.9 9단계: Mattermost 및 OceanClaw Skill 연동

목표는 현장 친화적인 채팅 인터페이스를 제공하는 것이다.

기능:

- Mattermost 채널에서 질문 입력
- 이상 증상별 스레드 관리
- 답변과 출처 자동 표시
- 정비 이력 조회 결과 공유

이 단계는 RAG와 평가가 안정된 뒤 진행한다.

## 5. NVIDIA Jetson Orin Nano 적용 계획

계획서에는 없지만 실제 운영 환경을 고려해 Jetson Orin Nano를 배포 목표 장비로 포함한다.

### 5.1 Jetson 사용 목적

- 선박 내부 로컬 서버 역할
- 인터넷 없이 Ollama 기반 LLM 추론 수행
- FAISS 검색 서버 실행
- Mattermost 또는 API 서버와 연동
- 저전력 Edge AI 환경 검증

### 5.2 Jetson 제약사항

Jetson Orin Nano는 일반 데스크탑보다 메모리와 저장공간이 제한적이다.

따라서 다음 원칙을 따른다.

- 대형 LLM 대신 소형 모델 사용
- embedding 모델도 가벼운 모델 사용
- PDF 원문 전체를 매번 LLM에 넣지 않음
- 검색 결과 top-k를 작게 유지
- index는 미리 생성해서 Jetson에 배포
- 답변 생성과 검색 서버를 분리 가능하게 설계

### 5.3 Jetson 후보 모델

초기 후보:

- `gemma:2b`
- `gemma2:2b`
- `phi3:mini`
- `qwen2.5:3b`
- `nomic-embed-text`

모델은 실제 Jetson에서 속도와 메모리를 측정한 뒤 확정한다.

### 5.4 Jetson 배포 구조

```text
개발 PC
  -> PDF/CSV 전처리
  -> chunk 생성
  -> FAISS index 생성
  -> 평가

Jetson Orin Nano
  -> Ollama 실행
  -> FAISS index 로드
  -> FastAPI 검색/답변 서버 실행
  -> Mattermost 또는 로컬 UI 연동
```

초기에는 개발 PC에서 모든 기능을 완성한 뒤, Jetson에는 검증된 index와 최소 실행 서버만 올린다.

## 6. 기술 스택

초기 기술 스택:

- Python 3.10+
- pypdf
- pandas 또는 csv 표준 라이브러리
- Ollama
- FAISS CPU
- FastAPI
- Markdown

후순위 기술:

- LangChain
- Mattermost API
- Docker
- Obsidian Vault
- OCR
- Gemini API

Gemini는 비용과 인터넷 의존성이 있으므로 초기 개발에서는 필수로 두지 않는다. 단, 온라인 고성능 위키 생성이나 비교 평가용으로 선택적으로 사용할 수 있다.

## 7. 역할 분담 제안

### 개발 담당

- 프로젝트 구조 설계
- PDF extract, chunk, embedding, index 구현
- Ollama 답변 생성
- 검색 평가 자동화
- Jetson 배포 테스트

### 데이터 담당

- 공개 선박 매뉴얼 PDF 수집
- 정비 이력 샘플 또는 실제 데이터 확보
- 기대 답변 및 출처 정리
- 평가 질문 30개 작성

### UI/연동 담당

- Mattermost 연동
- 채팅 인터페이스
- 결과 표시 방식 설계
- Wiki/Obsidian 화면 구성

## 8. 마일스톤

### M1: 새 프로젝트 뼈대 완성

- 기본 폴더 구조 생성
- `.env.example` 작성
- PDF 추출 스크립트 작성
- README 작성

### M2: PDF RAG 최소 기능 완성

- 페이지별 추출 JSONL 생성
- chunk JSONL 생성
- embedding 생성
- FAISS index 생성
- PDF 질문 답변 가능

### M3: CSV 정비 이력 검색 추가

- CSV row 문서화
- 이력 검색 구현
- PDF 검색 결과와 통합
- 출처 표시

### M4: 평가 자동화

- 평가 질문 세트 작성
- 검색 정확도 확인
- 답변 키워드 검증
- 환각률 점검

### M5: Jetson Orin Nano 배포 검증

- Ollama 설치 및 모델 실행
- FAISS index 로드
- API 서버 실행
- 응답 속도 및 메모리 사용량 측정

### M6: LLM Wiki 구축

- 부품별 Markdown 생성
- 정비 절차 문서 생성
- 정비 이력 링크 생성
- Wiki 검색 추가

### M7: Agent 및 Mattermost 연동

- 질문 라우팅
- 도구 자동 선택
- Mattermost 채널 답변
- 스레드 기반 정비 관리

## 9. 우선 개발 순서

가장 먼저 할 일은 다음과 같다.

```text
1. README.md 생성
2. requirements.txt 생성
3. data/raw, data/interim, data/processed 폴더 생성
4. pdf_extract.py 구현
5. scripts/extract_pdf.py 구현
6. 실제 Yanmar PDF로 pdf_pages.jsonl 생성 확인
7. chunk.py 구현
8. scripts/chunk_pdf.py 구현
```

이 순서대로 가면 코드가 섞이지 않고, 각 단계 결과물을 눈으로 확인하면서 개발할 수 있다.

## 10. 개발 원칙

- 처음부터 복잡한 Agent를 만들지 않는다.
- 각 단계는 JSONL 산출물을 남긴다.
- 데이터 처리, 검색, 답변 생성을 파일 단위로 분리한다.
- 출처 없는 답변은 실패로 본다.
- Jetson에서 돌아갈 수 있도록 모델과 index 크기를 항상 의식한다.
- 실제 데이터가 부족하면 공개 매뉴얼과 가짜 정비 이력으로 먼저 파이프라인을 검증한다.
- 실제 데이터가 들어오면 평가 질문과 기대 출처를 함께 만든다.
