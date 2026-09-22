# 자연어와 UML의 관계 모델

## 문제 정의

자연어는 목표, 이유, 우선순위, 예외와 품질 요구를 풍부하게 표현하지만 모호하다. UML은 구조와 상호작용을 명확히 표현하지만 Feature 선택 이유, 불확실성, 금지 요구, 사업 우선순위를 충분히 보존하지 못한다. 따라서 둘을 직접 변환하면 다음 문제가 발생한다.

- 하나의 자연어 문장이 여러 UML Element로 분해되면서 원문의 근거가 사라진다.
- UML Component 하나가 여러 Feature와 Requirement를 구현해 변경 이유를 알기 어렵다.
- 자연어의 `가급적`, `필수`, `제외`, `유지`가 UML 구조만으로 구분되지 않는다.
- UML을 수동 수정하면 Feature Constraint와 충돌할 수 있다.
- Diagram과 실제 API 또는 코드 사이에 Drift가 생길 수 있다.

## 제안 관계

```text
Natural Language
  -> Requirement IR
  -> Feature Intent and Constraints
  -> Solver Validated Configuration
  -> Architecture Graph
  -> UML Projection
  -> Human Review
  -> Bounded Architecture Change Proposal
  -> Natural Language Explanation and Solver Revalidation
```

자연어와 UML 사이에는 Requirement IR과 Architecture Graph라는 두 개의 의미 고정점이 존재해야 한다. 자연어에서 직접 UML을 생성하거나 UML에서 직접 코드를 생성하는 경로는 허용하지 않는다.

## 변환 방향별 책임

### 자연어에서 UML

1. 자연어 문장을 Requirement, Intent, NFR, Constraint, Uncertainty로 분리한다.
2. 각 항목에 원문 인용 `source_quote`와 confidence를 기록한다.
3. Intent를 Feature Candidate에 매핑한다.
4. Solver가 유효한 Feature Configuration을 확정한다.
5. Feature to Asset Mapping으로 Architecture Graph를 합성한다.
6. Architecture Graph를 UML Component, Sequence, Activity, Deployment Diagram으로 투영한다.
7. 모든 UML Element에 Requirement와 Feature 식별자를 Tagged Value로 기록한다.

### UML에서 자연어

UML 수정은 명령이 아니라 Change Proposal이다.

1. 이전 UML Projection과 수정본의 Element Delta를 계산한다.
2. Delta를 Architecture Graph의 Component 또는 Interface 변경으로 변환한다.
3. Feature Mapping을 역조회해 영향을 받는 Feature와 Requirement를 계산한다.
4. 자연어 설명을 생성한다. 예를 들어 `Patient BFF가 추가되어 patient_mobile Feature가 필요합니다`와 같이 표현한다.
5. Feature Model과 Solver로 유효성을 검증한다.
6. 원래 요구와 충돌하거나 새로운 기능 선택이 필요하면 사용자 승인을 요청한다.
7. 승인 후 Requirement IR의 새 Version을 만들고 UML을 다시 생성한다.

## 추적 식별자

모든 관계는 이름이 아니라 불변 ID로 연결한다.

| Artifact | 식별자 예 | UML Tagged Value |
|---|---|---|
| Requirement | `FR-002` | `reqIds=FR-002` |
| NFR | `NFR-001` | `nfrIds=NFR-001` |
| Intent | `INT-005` | `intentIds=INT-005` |
| Feature | `pacs_integration` | `featureIds=pacs_integration` |
| Component | `CMP-DICOM-GW` | `componentId=CMP-DICOM-GW` |
| Interface | `API-DICOM-STOW` | `interfaceIds=API-DICOM-STOW` |
| Test | `AT-IMG-001` | `testIds=AT-IMG-001` |

PlantUML Source에는 다음 Header를 포함한다.

```text
' generated_from: ARCH-BASE-HOSP-001
' requirement_ir_version: 0.1.0
' feature_configuration: GOLD-BASE-HOSP-001
' generator_version: 0.1.0
```

## UML Profile

- `<<RequirementBound>>`: Requirement ID가 연결된 Element
- `<<FeatureRealization>>`: 선택 Feature를 구현하는 Component
- `<<PolicyEnforced>>`: 보안 또는 데이터 정책을 강제하는 Element
- `<<Generated>>`: 자동 생성되며 직접 편집할 수 없는 Element
- `<<ChangeProposal>>`: 사용자 수정으로 감지되어 아직 승인되지 않은 Element
- `<<EvidenceProducing>>`: Test 또는 Audit Evidence를 생성하는 Element

## 정보 손실 방지 규칙

- UML에 표현할 수 없는 우선순위, confidence, 원문 근거는 Requirement IR에 남긴다.
- `exclude`와 `preserve` Intent는 UML에서 Element 부재만으로 추론하지 않고 별도 Trace에 기록한다.
- Sequence Diagram의 Message는 실제 API Operation ID를 사용한다.
- Component Diagram의 Port와 Interface는 OpenAPI 또는 AsyncAPI 계약과 연결한다.
- Diagram에서 삭제된 Element는 즉시 Feature 제거로 해석하지 않고 Change Proposal로 처리한다.
- Round Trip 후 Requirement ID, Feature ID, Component ID 집합이 보존되지 않으면 변환을 실패 처리한다.

## 관계 품질 지표

- Requirement to UML Coverage: UML에 연결된 Requirement 비율
- UML Element Grounding Rate: Requirement 또는 Feature 근거가 있는 Element 비율
- Round Trip Identity Preservation: 왕복 변환 후 ID 보존율
- Semantic Drift Count: 자연어 의미와 UML 구조의 불일치 수
- Unsupported UML Edit Rate: Feature Model이 허용하지 않는 UML 수정 비율
- Explanation Fidelity: UML Delta의 자연어 설명이 실제 Delta를 정확히 설명하는 비율

## 연구 가설

- H UML 1: Requirement IR을 경유한 UML 생성은 자연어에서 직접 UML을 생성하는 방식보다 Grounding Rate가 높다.
- H UML 2: Tagged Trace ID를 포함하면 Architecture Review의 결함 원인 식별 시간이 감소한다.
- H UML 3: UML 수정을 Change Proposal로 처리하면 직접 Code Generation보다 Constraint Violation이 감소한다.
- H UML 4: 자동 재생성 방식은 수동 UML 이중 관리보다 Semantic Drift가 낮다.

