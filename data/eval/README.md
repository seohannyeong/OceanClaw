# OceanClaw Evaluation Data

이 폴더는 OceanClaw 검색/답변 품질을 확인하기 위한 평가셋을 관리합니다.

## 파일 역할

| 파일 | 역할 |
| --- | --- |
| `manual_queries.jsonl` | 개발 중 검색 품질 개선에 사용한 매뉴얼 질문 30개 |
| `manual_holdout_v1.jsonl` | 개선 후 검증에 사용하는 holdout 질문 15개 |
| `manual_review_template.csv` | 팀원이 검색/답변 결과를 직접 평가하는 표 |
| `benchmark.lock.json` | 개발 평가 입력 파일 고정값 |
| `holdout_v1.lock.json` | holdout 평가 입력 파일 고정값 |

## 평가 기준

검색 평가는 먼저 `Top-3 안에 기대 출처가 들어오는지`를 봅니다.

답변 평가는 사람이 확인합니다.

- `answer_correct`: 답변이 질문에 맞는지
- `source_correct`: 제시한 출처가 실제 근거인지
- `safety_issue`: 안전상 위험하거나 매뉴얼에 없는 지시가 있는지
- `notes`: 왜 맞거나 틀렸는지 짧게 기록

## 팀원 작업 순서

1. Web UI에서 질문을 입력합니다.
2. 검색 범위는 우선 `매뉴얼`, Top K는 `3`으로 둡니다.
3. 답변과 출처를 확인합니다.
4. `manual_review_template.csv`에 `top1_page`, `top3_pages`, `hit_at_3`, `answer_correct`, `source_correct`, `safety_issue`, `notes`를 채웁니다.

예시:

```text
top1_page: 69
top3_pages: 69,69,73
hit_at_3: O
answer_correct: O
source_correct: O
safety_issue: X
notes: 오일 점검 절차와 온도 조건을 포함함
status: reviewed
```

## 개발자용 자동 평가

기존 평가 스크립트:

```powershell
python scripts\compare_retrieval.py --validate-only
python scripts\compare_retrieval.py --modes original expanded translated multilingual --limit 30
python scripts\validate_holdout.py --limit 15 --modes titles
```

Jetson에서 실제 `/ask` 응답을 측정할 때:

```bash
python scripts/validate_holdout.py --api-url http://127.0.0.1:8000 --require-jetson --limit 15 --repeats 1
```

## 새 질문을 추가할 때 규칙

- 질문에는 실제 매뉴얼에 답이 있어야 합니다.
- `page`에는 기대 출처 페이지를 적습니다.
- `evidence`에는 해당 페이지에 실제로 존재하는 짧은 원문 문장을 적습니다.
- 개발에 사용한 질문과 최종 검증 질문은 분리합니다.
- 개선 후 성능을 확인할 질문은 `manual_holdout_v1.jsonl`처럼 별도 파일로 관리합니다.
