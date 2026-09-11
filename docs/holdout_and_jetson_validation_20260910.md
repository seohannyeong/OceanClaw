# 새 질문 검증 및 Jetson 측정 준비

## 완료 범위

- 기존 개발용 30문항과 정답 페이지가 겹치지 않는 신규 15문항을 작성하고 입력 해시를 고정했다.
- 고정된 PDF 청크로 번역 검색, BGE-M3 원문 검색, 제목 추가 BGE-M3 검색을 실행했다.
- 제목 인덱스와 인접 문맥을 `/ask`에서 선택할 수 있게 연결했다. 기존 기본 동작은 변경하지 않았다.
- Windows PC에서 실제 HTTP `/ask` 요청 6건을 확인했다.
- **Jetson 실측은 미완료다.** 기존 Tailscale 주소 `100.103.244.58`의 SSH 연결이 시간 초과되어 실행하지 못했다.

## 새 질문 결과

| 방법 | 정답 근거 Hit@3 | 검색 시간 중앙값 |
| --- | --- | --- |
| 질문 번역 + 기존 nomic 검색 | 9/15 (60.0%) | 0.538초 |
| 한국어 원문 + BGE-M3 | 10/15 (66.7%) | 0.034초 |
| 한국어 원문 + 제목 추가 BGE-M3 | 12/15 (80.0%) | 0.035초 |
| 제목 추가 + 인접 문맥 | 문맥 내 근거 포함 12/15 | 위 검색 뒤 문맥 추가 |

인접 문맥의 지표는 Hit@3가 아니다. 검색 결과 3개 외의 문맥을 추가한 후의 근거 포함률이다.

- 번역과 제목 추가의 첫 요청은 각각 86.27초와 26.94초였다. 모델 로딩 등이 섞인 첫 요청과 이후 시간을 구분해야 한다. 제목 없는 BGE 추가 비교는 모델이 이미 로딩된 상태였다.
- 중앙값은 전체 요청에서 계산했다. 실행 순서와 캐시를 통제한 정밀 속도 벤치마크는 아니다.
- 제목 추가 방식의 실패 질문: h09(보관 기간 기준), h10(보존 처리 표지), h12(재사용 시 마개 제거).
- 번역에서 `증기 → steam`, `윤활유 → grease`, `마개 → valves` 등의 의미 변형이 관찰됐다. 검색 성공과 번역 정확성은 별개다.
- 15문항은 같은 매뉴얼의 6개 페이지에서 작성했다. 기존 30문항과 페이지는 분리했지만 외부 전문가가 만든 블라인드 테스트는 아니며, 질문 간 주제 상관도 있다.
- 결과를 보고 임베딩 모델, 번역 프롬프트, 제목 생성 규칙을 수정하지 않았다. 제목 없는 BGE는 제목 추가 효과를 분리하기 위한 추가 대조 실행이다.

## 로컬 API 확인

Windows PC, gemma3:4b, h01~h03 각각 2방식, 1회 실행. Jetson 수치가 아니다.

| 방식 | HTTP 성공 | 응답 시간 중앙값 | 평균 근거 본문 길이 |
| --- | --- | --- | --- |
| titles | 3/3 | 2.38초 | 2,092자 |
| titles_neighbors | 3/3 | 2.78초 | 3,670자 |

두 방식 모두 세 질문의 정답 근거가 응답의 results에 포함됐다. 다만 답변 완성도는 다음과 같이 별도 검토했다.

| 질문 | 답변 검토 |
| --- | --- |
| h01: 해수 흡입 밸브를 열어야 하는 이유 | 두 방식 모두 임펠러 손상을 언급했지만 `펌프 내부 임펠러`를 `엔진 내부 임펠러`라고 부정확하게 표현했다. 인접 문맥 방식은 건식 작동 원인을 추가했다. |
| h02: 기관실 증기 확인 | titles는 `가연성 증기`를 `연기`로 바꿨다. titles_neighbors는 가스와 가연성 증기를 정확하게 표현했다. |
| h03: 엔진 작동 중 시동 조작 유지 | 두 방식 모두 중단해야 한다는 방향은 맞다. 최대 15초라는 별도 시동 설명도 추가되어 운전 중 15초 유지가 허용된다고 오해되지 않도록 표현 검토가 필요하다. |

출처 목록은 **검색되어 제공된 근거 목록**이며, 생성된 각 문장을 실제로 뒷받침하는지 자동 검증한 인용 목록은 아니다.

Ollama `/api/ps`에서 BGE-M3는 약 0.87GiB, gemma3:4b는 약 3.69GiB로 보고됐다. 이는 로컬에서 로딩된 모델의 보고값으로, OS 전체 메모리나 최대 사용량이 아니다. 이전 실험의 nomic 모델도 함께 로딩되어 있었다. Jetson 메모리 예산으로 그대로 사용할 수 없다.

## API 사용법

```json
{
  "question": "시동 전에 바닷물 흡입 밸브가 열려 있는지 봐야 하는 이유가 뭐야?",
  "route": "manual",
  "manual_profile": "titles_neighbors",
  "top_k": 3,
  "max_context_chars": 5000,
  "save_log": false
}
```

- `manual_profile`: 기존 `legacy`, 제목 추가 `titles`, 제목 및 인접 문맥 `titles_neighbors`.
- 새 방식은 `route=manual`에서만 허용한다. 센서와 Wiki 검색은 기존 방식 그대로다.
- 인접 문맥은 같은 파일·페이지·절의 바로 앞뒤 청크로 제한하고 절 경계에서 잘라 제공한다.
- 본문 합계 5,000자를 기본 제한으로 사용한다. 메타데이터·시스템 프롬프트를 포함한 토큰 한도는 아니다.
- `results.context_role`로 seed와 neighbor를 구분한다. 이웃에는 검색 점수를 부여하지 않는다.
- `timing`에 검색·생성·총 처리 시간, `context_chars`에 본문 길이를 기록한다.
- `TITLED_MANUAL_INDEX_DIR`로 제목 인덱스 위치를 지정할 수 있다. 기본값은 `index/bge_m3_titles_20260910_213358`이다.

## Jetson 실행

제공된 `jetson_benchmark_bundle.zip`은 측정용 코드와 인덱스의 스냅샷이다. `.env`, 토큰, 가상환경, 개인 Wiki 로그는 포함하지 않는다. 기존 배포 폴더와 분리해서 사용한다.

Windows PowerShell에서 Jetson 접속이 복구된 뒤 프로젝트 폴더에서 실행:

```powershell
scp output/jetson_benchmark_bundle.zip oceanclaw@100.103.244.58:~/
ssh oceanclaw@100.103.244.58
```

Jetson 터미널:

```bash
mkdir -p ~/OceanClaw-benchmark-20260910
python3 -m zipfile -e ~/jetson_benchmark_bundle.zip ~/OceanClaw-benchmark-20260910
cd ~/OceanClaw-benchmark-20260910
source ~/OceanClaw/.venv/bin/activate
python -m pip install -r requirements.txt
ollama pull bge-m3
ollama pull gemma3:4b
python scripts/run_jetson_benchmark.py --repeats 2
```

전제: Ollama 서버가 실행 중이고 `tegrastats`가 PATH에 있어야 한다. 기존 가상환경 위치가 다르면 활성화 경로를 맞춘다. 모델 다운로드 후 기존 Windows 결과의 모델 digest와 같은지도 manifest에서 확인한다.

측정기는 로컬 전용 18080 포트에 임시 API를 띄운다. 사용 중이면 `--port 18081`로 변경한다. 기존 8000 서버를 종료하지 않는다. 15질문 × 2방식 × 2회 = 60회 답변 생성이므로 시간이 걸릴 수 있다. 실행 확인만 할 때는 `--limit 3 --repeats 1`을 사용한다. 측정 중 다른 질문 요청은 피한다.

생성 결과는 `output/eval/ask_benchmark_날짜시간/`에 저장된다.

- `manifest.json`: 실제 장비, 모델 버전, 입력 해시, 실행 조건.
- `results.jsonl`: 질문별 답변, 근거, HTTP 소요 시간, 서버 내부 시간, Ollama 모델 보고값.
- `tegrastats.log`: 500ms 간격 장비 메모리·CPU·GPU 등 원본 로그.
- `memory_summary.json`: 샘플링한 장비 전체 RAM 최대값. 프로세스별 RSS나 순간 최대값은 아니다.
- `summary.json`: 방식별 성공 여부, 근거 포함 건수, 중앙값·최대 지연.

첫 회는 모델 로딩 여부를 별도 확인하고, 두 번째 회는 실행 순서를 반대로 한다. 결과 파일의 `repeat` 기준으로 나누어 비교한다. 생성 답변 평가는 `answer_review=pending`으로 남겨 사람이 원문과 대조하도록 했다.

## 결론

**제목 추가 BGE-M3를 우선 후보로 삼을 근거는 강화됐다. 인접 문맥의 상시 적용은 아직 확정하지 않는다.** 신규 15문항에서는 근거 포함률이 추가로 늘지 않았으며 문맥 길이는 증가했다. Jetson에서의 속도·메모리 실측과 생성 답변 검토를 마친 뒤 기본 설정 변경 여부를 결정한다.

## 결과 위치

- 새 질문: `data/eval/manual_holdout_v1.jsonl`
- 입력 고정: `data/eval/holdout_v1.lock.json`
- 번역/제목 비교: `output/eval/holdout_20260910_214433/`
- 제목 없는 BGE 대조: `output/eval/holdout_20260910_215030/`
- 로컬 API: `output/eval/ask_benchmark_20260910_214916/`
- 자동 회귀 테스트: `scripts/test_contextual_api.py`, `scripts/test_chunk_context.py`, `scripts/test_compare_retrieval.py`
