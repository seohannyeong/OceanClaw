# 한국어 질문 검색 비교 실험

## 범위

- A `original`: 한국어 원문을 그대로 임베딩
- B `expanded`: 기존 `expand_query()`로 영어 단어를 추가한 뒤 임베딩
- C `translated`: Ollama로 영어 검색 질문을 번역한 뒤 임베딩
- 세 방식 모두 기존 PDF FAISS 인덱스와 인덱스 메타데이터에 기록된 임베딩 모델을 사용한다.
- D `multilingual`: 한국어 원문을 BGE-M3로 임베딩하고 같은 청크로 만든 별도 인덱스에서 검색한다. 규칙 확장과 번역은 적용하지 않는다.
- 서비스 검색 코드와 규칙 사전은 수정하지 않는다.

## 실행

프로젝트 루트에서 Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python scripts\compare_retrieval.py --validate-only
python scripts\compare_retrieval.py
```

스크립트 위치를 기준으로 경로를 해석하므로 `scripts` 폴더에서 실행해도 된다.
기존 설정과 동일하게 환경변수 또는 `config.py` 기본값을 사용한다. `.env`를 자동으로 읽지는 않는다.
기본 번역 모델은 `gemma3:4b`이며, 설치된 다른 모델을 명시할 수 있다.

```powershell
python scripts\compare_retrieval.py --translation-model gemma3:4b --timeout 300
python scripts\compare_retrieval.py --limit 2
python scripts\compare_retrieval.py --modes original expanded
```

다국어 모델 설치 및 별도 인덱스 생성(기존 `index/pdf.faiss` 보존):

```powershell
ollama pull bge-m3
python scripts\build_index.py --model bge-m3 --faiss index/bge_m3/pdf.faiss --docs index/bge_m3/pdf_docs.json
python scripts\compare_retrieval.py --modes original expanded translated multilingual
```

이미 BGE-M3 인덱스가 있다면 마지막 명령만 실행한다. `build_index.py`는 지정한 출력 파일을 덮어쓰므로 기존 기본 경로로 실행하지 않는다.
다국어 인덱스의 모든 문서가 기존 청크와 같은지 검사하고, 비교 실행 시 해당 인덱스 해시도 결과에 기록한다.
질문 임베딩 모델은 선택한 인덱스 메타데이터에서 읽는다. 서로 다른 모델의 벡터를 혼합하지 않는다.

`--limit`은 실행 확인용이며 앞의 질문부터 선택한다. 전체 성능 보고에는 30개 전부를 사용한다.

## 평가 질문

`data/eval/manual_queries.jsonl`에는 PDF 69~81페이지에서 확인한 질문 30개와 원문 근거가 있다.
페이지는 PDF 파일의 1부터 시작하는 페이지 번호다. 인쇄 페이지와는 다르다.

| 그룹 | 개수 | 목적 |
|---|---:|---|
| covered | 10 | 기존 사전의 장비 용어를 사용하는 질문 |
| paraphrase | 10 | 앞의 10개와 같은 근거를 묻는 다른 표현 |
| uncovered | 10 | 사전에 등록되지 않은 주요 용어의 질문 |

이는 매뉴얼 추출 텍스트를 바탕으로 작성한 초기 평가용 라벨이다. 현장 전문가 검수나 PDF 표의 시각적 검수를 완료한 데이터셋은 아니다.
`uncovered`는 현재 규칙에 일치하는 표현이 없는 질문으로 구성했다. 일부 paraphrase에는 일반 규칙이 적용될 수 있다.
covered와 paraphrase는 같은 근거를 공유하므로 독립된 20개 정비 작업으로 해석하지 않는다.
아직 별도 개발/최종평가 분할은 하지 않았다. 이 30개 결과로 규칙을 개선했다면 최종 성능은 새 질문으로 검증한다.
분할할 때도 동일 근거를 공유하는 질문 쌍을 같은 분할에 넣어 누출을 막는다.

## 입력 고정

첫 검증 시 `data/eval/benchmark.lock.json`에 페이지 JSONL, 청크 JSONL, FAISS, 문서 메타데이터, 질문 파일의 SHA-256을 기록한다.
이후 실행은 해시가 다르면 중단한다. 인덱스를 생성하거나 기존 데이터를 덮어쓰지 않는다.
청크 JSONL과 인덱스 메타데이터의 문서 목록이 일치하는지, 모든 정답 문장이 페이지와 청크에 존재하는지도 검사한다.
의도적으로 데이터를 변경할 때는 기존 lock과 결과를 보관하고 별도 버전의 벤치마크를 만든다.

## 출력

`output/eval/<실행시각>/`에 저장한다.

- `manifest.json`: 입력 해시, 모델명, 번역 프롬프트, 실행 조건
- `resolved_questions.json`: 질문별 정답 근거 청크 ID
- `results.jsonl`: 실제 검색 질문, Top-3 원문/페이지/점수, 관련성, 단계별 시간, 오류
- `comparison.csv`: 질문별 비교표와 수동 번역/검색 검토란
- `summary.json`: 방식별 전체/그룹별 Hit@3, MRR@3, 성공 요청 평균/중앙값 소요 시간
- `memory_summary.json`: Ollama가 보고한 모델별 로드 크기/VRAM 관측 최댓값
- `integrity.json`: 실행 중 원본 입력 변경 여부

Hit@3는 지정된 페이지의 근거 문장을 포함한 청크가 Top-3에 있는지 평가한다.
MRR@3는 첫 근거 청크의 순위 역수다. 1위=1, 2위=0.5, 3위=약 0.333, 실패=0.
오류도 전체 분모에 포함하고 실패로 처리한다. 성공 횟수와 오류 횟수를 반드시 함께 보고한다.
같은 정답이 다른 페이지에 있거나 청크에 동등한 설명이 있으면 자동 평가에서 누락될 수 있다. 원문을 보고 라벨을 보완하되 모든 방식을 같은 라벨로 재평가한다.

## 시간과 번역 검토

번역은 temperature=0으로 실행하며 장비명, 수치, 단위, 부정 표현을 보존하고 원문에 없는 원인이나 절차를 추가하지 않도록 지시한다.
프롬프트만으로 정확성을 보장할 수 없다. CSV의 `translation_review`에 누락, 의미 변경, 불필요한 추가를 기록한다.
번역문에 한글이 남거나 영문이 없으면 실패로 기록하며 한국어 원문으로 몰래 대체하지 않는다.

순서는 고정 seed로 섞고 캐시/워밍업 없이 실행한다. 시간에는 모델 최초 로딩과 모델 간 교체 비용이 포함될 수 있다.
`transform_seconds`는 번역 또는 확장, `embedding_seconds`는 질문 임베딩과 정규화, `search_seconds`는 FAISS 검색 시간이다.
`total_seconds`에는 이 과정과 결과 조립이 포함되며 초기 인덱스 로딩과 메모리 관측 요청 시간은 제외한다.
단일 실행은 탐색적 비교다. 최종 속도 비교에는 같은 환경에서 반복 실행하고 콜드 스타트와 워밍업 후 성능을 나누어 측정한다.
모델 이름이 같더라도 모델 파일이 바뀌면 실험 조건이 달라질 수 있다. manifest에 현재 설치된 모델 digest와 Ollama 버전, 플랫폼, 실험 코드/확장 사전 해시를 기록한다.
기존 인덱스를 만들었던 당시 모델 digest는 없어 현재 모델과 같은 파일이었는지는 소급 확인할 수 없다.

## 메모리 해석

번역 직후와 검색 직후 `/api/ps`를 조회하고 원본 응답을 `results.jsonl`에 저장한다.
`size`와 `size_vram`은 Ollama가 보고하는 로드된 모델 크기와 VRAM이다. 둘을 더하지 않는다.
관측 최댓값은 추론 중의 순간 피크, 전체 Python/OS 메모리, Jetson 공유 메모리 사용량이 아니다.
다른 모델이 동시에 로드되어 있을 수 있으므로 프로세스 전체 사용량으로 해석하지 않는다.
메모리 관측 실패는 0으로 바꾸지 않고 오류로 기록한다.
데스크탑 결과만으로 Jetson 8GB에 답변 생성 모델까지 함께 운용할 수 있다고 확정하지 않는다.
Jetson에서는 같은 실험과 별도로 실제 `/ask`를 실행하며 `tegrastats`로 시스템 공유 메모리와 응답 시간을 측정한다.
