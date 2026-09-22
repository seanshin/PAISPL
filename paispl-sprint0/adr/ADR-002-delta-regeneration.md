# ADR 002 Delta 기반 선택적 재생성

## 상태

Accepted for MVP

## 결정

요구 변경은 전체 저장소 재생성이 아니라 이전 및 신규 Feature Configuration의 Delta로 처리한다. Delta를 Architecture Dependency Graph에 전파하여 영향 폐쇄를 구하고, 허용된 자산만 수정한다.

## 이유

전체 재생성은 검토 범위, Token 비용, 회귀 위험과 추적 복잡도를 증가시킨다. 변경 계약은 수정 가능 자산, 보존 자산과 필수 시험을 명시해 Agent의 과잉 수정을 제한한다.

## 결과

- Architecture Graph의 Dependency Type을 관리해야 한다.
- Gold Impact Set과 Impact Precision 및 Recall이 필요하다.
- 보존 대상으로 지정된 파일의 변경은 Verification Gate에서 차단한다.

