# PAISPL UML 활용 전략

## 결론

UML은 PAISPL에서 유용하다. 다만 자연어 요구를 곧바로 UML로 바꾼 뒤 UML만으로 제품을 생성하는 방식은 권장하지 않는다. Feature의 선택 가능성과 교차 제약은 Feature Model과 Solver가 담당하고, UML은 유효 구성이 확정된 뒤 Architecture Contract와 Agent 작업 가이드 및 인간 검토 화면으로 사용한다.

## 권장 책임 분리

| 관심사 | 권위 있는 원본 | UML 역할 |
|---|---|---|
| 기능 선택과 제외 | Feature Model | 선택 결과를 Note 또는 Stereotype으로 표시 |
| Requires 및 Excludes | Constraint DSL 및 Solver | 검토용 설명만 표시 |
| 서비스와 인터페이스 | Architecture Graph | Component Diagram으로 시각화 |
| 업무 및 생성 흐름 | Workflow Model | Activity Diagram으로 실행 순서 표현 |
| 런타임 상호작용 | API 및 Event Contract | Sequence Diagram으로 호출 관계 검토 |
| 배포 Profile | Deployment Model | Deployment Diagram으로 Node 배치 검토 |
| 추적성 | Trace Graph | Class 또는 Object Diagram으로 관계 탐색 |

## 가장 유용한 UML 유형

1. Component Diagram: Feature에서 선택된 서비스, Gateway, Adapter, 저장소와 인터페이스를 검토한다.
2. Activity Diagram: Prompt에서 IR, Solver, Architecture, Patch, Verification으로 이어지는 파이프라인을 표현한다.
3. Sequence Diagram: 환자 모바일, BFF, 인증, FHIR, EMR 같은 런타임 계약과 호출 순서를 검토한다.
4. Deployment Diagram: Cloud, On Premise, Hybrid Profile에 따른 Node와 Trust Boundary를 확인한다.
5. Class Diagram: Requirement, Feature, Component, Test, Evidence 사이의 추적 메타모델을 설명한다.

Use Case Diagram은 이해관계자 범위 합의에는 유용하지만 코드 생성 입력으로서의 가치는 낮다. State Machine Diagram은 장시간 Workflow, 승인, 실패 복구가 복잡해지는 M2 이후에 도입한다.

## 운영 원칙

- UML 파일을 사람이 별도로 편집해 원본 모델과 이중 관리하지 않는다.
- Requirement IR, Feature Configuration, Architecture Graph에서 PlantUML을 생성한다.
- 생성된 UML의 `model_version`과 입력 Artifact ID를 Header에 기록한다.
- Component와 Sequence Diagram에 사용된 인터페이스 이름은 OpenAPI 또는 AsyncAPI 계약과 동일해야 한다.
- UML 변경만으로 코드 생성을 승인하지 않고 Solver 및 Contract Test를 통과해야 한다.
- Delta Planner는 UML 이미지 차이가 아니라 Architecture Graph Diff를 사용한다.

## 연구 실험

10개 복합 시나리오를 UML 중간표현 사용군과 미사용군으로 나눈다. 동일한 Requirement IR과 Feature Configuration을 제공하고 다음을 측정한다.

- Architecture Interface Mismatch 수
- 생성 코드의 Acceptance Test 통과율
- Impact Set Precision 및 Recall
- Agent Token과 재시도 횟수
- Architect의 검토 시간과 결함 발견 수
- UML과 실제 Architecture Graph 사이의 Drift Ratio

가설은 UML 사용군이 인터페이스 불일치와 검토 시간을 줄이지만, UML을 별도 원본으로 수동 관리하면 Drift와 유지비가 증가한다는 것이다.

## 도입 순서

- M0: Component, Activity, Traceability Class Diagram
- M1: Architecture Graph에서 PlantUML 자동생성
- M2: 변경 전후 Diagram Diff와 Sequence Diagram
- M3: Deployment Diagram 및 Workflow State Machine

