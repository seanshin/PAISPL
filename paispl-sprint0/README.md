# PAISPL Sprint 0 Design Package

이 패키지는 프롬프트 기반 AI Software Product Line의 첫 구현을 시작하기 위한 공통 설계 기준이다. 연구 실험과 MVP 구현은 동일한 Requirement IR, Feature Model, Gold Configuration, Acceptance Test를 사용한다.

## Sprint 0 완료 범위

- 의료 플랫폼 기준 요구사항 1개
- 순차 변경 시나리오 3개
- Requirement IR JSON Schema와 예제 4개
- 의료 Feature Catalog 38개
- Feature Model과 교차 제약 25개
- 참조 아키텍처 및 Feature to Component Mapping
- 단계별 Gold Configuration 4개
- Acceptance Test 20개
- ADR 2개와 초기 MVP Backlog
- 정적 검증 도구와 검증 보고서

## 기준 Vertical Slice

```text
Natural-language requirement
  -> Requirement IR
  -> Feature configuration
  -> Constraint validation
  -> Architecture plan
  -> Deployable variant
  -> Acceptance evidence
```

## 폴더

| 경로 | 목적 |
|---|---|
| `docs` | 제품 경계, 사용자, 성공 조건 |
| `schemas` | Requirement IR 계약 |
| `catalog` | Feature 메타데이터 |
| `models` | Feature 계층, 그룹, 제약 |
| `scenarios` | 기준 요구와 순차 변경 |
| `examples` | Schema를 따르는 Requirement IR 예제 |
| `gold` | 사람이 검토한 기대 구성 |
| `architecture` | 참조 컴포넌트와 Feature 매핑 |
| `tests` | 제품 변형 Acceptance Test |
| `adr` | 주요 아키텍처 결정 기록 |
| `backlog` | 6개월 MVP 초기 Backlog |
| `tools` | 패키지 정적 검증 도구 |

## 검증

Python 3 환경에서 다음을 실행한다.

```bash
python tools/validate_sprint0.py
```

검증기는 Schema 적합성, Feature 및 Constraint 수, 참조 무결성, Gold Configuration의 Mandatory 및 Group 및 Requires 및 Excludes 규칙, Scenario와 Acceptance Test의 참조를 검사한다.

## 다음 구현 단계

1. `packages/requirement-ir`에서 JSON Schema 기반 Validator를 구현한다.
2. `packages/feature-engine`에서 YAML 모델을 Z3 또는 PySAT 표현으로 변환한다.
3. 기준 요구를 입력해 `BASE-HOSP-001` 구성을 생성하고 Gold와 비교한다.
4. `CHG-001`부터 순서대로 Feature Delta와 예상 영향 범위를 계산한다.
5. Acceptance Test를 CI Gate로 연결한다.

