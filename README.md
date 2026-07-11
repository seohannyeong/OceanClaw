# ⚓ OceanClaw - 선박 정비 AI Agent (MVP)

선박 기관실에서 방대한 영문 기술 매뉴얼(PDF)과 정비 이력(CSV)을
**한국어 자연어 질문**으로 검색하고, **출처와 함께** 답을 받는 RAG 에이전트.

> 이 버전은 **MVP**입니다. Mattermost / 웹 UI / Obsidian Wiki / Ollama / Docker /
> 복잡한 LangChain Agent는 의도적으로 제외했습니다.

## MVP 범위

포함:
- PDF 매뉴얼 1개 + 정비 이력 CSV 1개
- 터미널에서 한국어 질문 입력
- PDF 관련 문단 의미 검색 (FAISS + Gemini 임베딩)
- CSV 관련 정비 이력 검색
- Gemini가 한국어 답변 생성 + 출처 표시(`[매뉴얼 p.N]`, `[정비이력 #N]`)

## 빠른 시작

```bash
# 1) 가상환경 + 의존성
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2) API 키 설정
cp .env.example .env
#   .env 파일을 열어 GEMINI_API_KEY 입력
#   키 발급: https://aistudio.google.com/apikey

# 3) 샘플 데이터 생성 (PDF 매뉴얼 + 정비이력 CSV)
python scripts/make_sample_data.py

# 4) 인덱스 빌드 (임베딩 → FAISS)
python build_index.py

# 5) 질문하기
python ask.py                                   # 대화형
python ask.py "메인 베어링 볼트 초기 조임 토크 값은?"   # 단발
```

## 데모 질문 예시

샘플 데이터 기준으로 잘 동작하는 질문들:

- `메인 베어링 볼트의 초기 조임 토크 값은?` → 150 Nm (매뉴얼 p.3)
- `4번 실린더 피스톤 링은 언제 마지막으로 교체했어?` → 2024-11-15 (정비이력)
- `메인 베어링 권장 점검 주기는?` → 5년 / 60,000시간 (매뉴얼 p.7)
- `최근 메인 베어링 #3 오일 간격 추세 알려줘` → CSV 이력 종합

## 실제 데이터로 교체

`.env`에서 `PDF_PATH`, `CSV_PATH`를 실제 파일로 지정한 뒤
`python build_index.py`를 다시 실행하면 됩니다.
CSV 컬럼 구조는 자유롭게 바꿔도 됩니다(각 행 전체가 검색 대상).

## 구조

```
oceanclaw/
  config.py       설정(.env)
  gemini.py       Gemini 임베딩 + 답변 생성
  ingest.py       PDF/CSV → 검색 문서
  vectorstore.py  FAISS 벡터 저장소
  pipeline.py     빌드 + 질의 파이프라인
  cli.py          터미널 인터페이스
build_index.py    인덱스 빌드 진입점
ask.py            질의 진입점
scripts/make_sample_data.py   샘플 PDF/CSV 생성
```

## 모델명 참고

`.env`의 `GEMINI_MODEL` / `EMBED_MODEL`은 본인 계정에서 접근 가능한
모델로 바꾸세요. 기본값은 널리 쓰이는 `gemini-2.5-flash` /
`text-embedding-004`이며, 계획서 기준 모델(`gemini-3.1-flash`,
`gemini-embedding-001`)로 변경 가능합니다.
```
# OceanClaw
