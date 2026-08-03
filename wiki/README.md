# OceanClaw Wiki

이 폴더는 OceanClaw의 LLM Wiki이자 Obsidian Vault로 사용할 수 있는 Markdown 지식 저장소입니다.

## 폴더 구조

```text
wiki/
  components/   부품, 계통, 장비별 지식
  procedures/   점검, 정비, 운전 절차
  logs/         센서 이벤트와 정비 이력 요약
  templates/    Wiki 문서 작성 템플릿
```

## 작성 원칙

- 문서는 Obsidian에서 바로 열 수 있는 Markdown으로 작성합니다.
- 관련 문서는 `[[문서명]]` 형태의 내부 링크로 연결합니다.
- 매뉴얼이나 CSV에서 가져온 내용은 반드시 출처를 남깁니다.
- 확실하지 않은 내용은 추정으로 쓰지 않고 `확인 필요`로 표시합니다.
- 하나의 문서는 하나의 부품, 절차, 이벤트 주제만 다룹니다.

## 문서 유형

- `components/`: 엔진 오일, 냉각수, dipstick, GT compressor 같은 부품/계통 설명
- `procedures/`: 엔진 오일 점검, 냉각수 점검 같은 작업 절차
- `logs/`: sensor warning, watch event, 정비 이력 요약

## 출처 표기 예시

```markdown
## 출처

- yanmar_6lf_operation_manual.pdf p.69
- sensor event sensor-230-compressor
```
