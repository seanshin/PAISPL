# ADR 001 LLM과 Solver의 책임 분리

## 상태

Accepted for MVP

## 결정

LLM은 자연어 해석, 후보 Feature 생성, 모호성 질문과 설명을 담당한다. Feature 구성의 유효성은 Feature Model과 Solver가 판정한다. Solver가 유효성을 확인하지 않은 구성은 Architecture Synthesis로 전달하지 않는다.

## 이유

자연어 추론은 유연하지만 조합 제약의 결정적 검증에는 적합하지 않다. 반대로 Solver는 의미 해석을 할 수 없지만 명시적 제약의 만족 여부와 Unsat Core를 제공할 수 있다.

## 결과

- Requirement IR과 Feature Model 사이에 명시적 Mapping이 필요하다.
- LLM의 confidence가 낮으면 자동 실행을 중단한다.
- 모든 생성 Variant는 Solver Evidence를 포함한다.

