# GT Compressor Warning Events

## 이벤트 요약

GT Compressor 관련 sensor event는 compressor decay 감소를 기준으로 watch 또는 warning 상태로 변환됩니다.

## 관련 장비

- GT Compressor

## 증상

- compressor decay 감소
- sensor event에서 severity가 `watch` 또는 `warning`으로 표시될 수 있음

## 권장 조치

- GT Compressor 성능 저하 여부를 점검합니다.
- 반복되는 warning event는 running hours 구간과 함께 확인합니다.
- 필요하면 관련 sensor event 검색 결과와 매뉴얼 점검 절차를 함께 검토합니다.

## 관련 문서

- [[coolant]]
- [[engine_oil]]

## 출처

- data/processed/sensor_events.csv
