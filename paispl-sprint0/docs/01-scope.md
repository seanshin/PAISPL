# Sprint 0 제품 범위

## 목표

200병상 규모 병원의 연계형 디지털 플랫폼을 기준 제품군으로 삼는다. 자연어 요구를 구조화된 요구사항과 유효한 Feature Configuration으로 변환하고, 요구 변경 시 영향을 받는 자산만 계산할 수 있는 공통 계약을 만든다.

## 기준 사용자

- 병원 CIO 또는 디지털센터 책임자: 자연어로 기능과 제약을 정의한다.
- Product Architect: Feature 구성, 충돌, 파생 기능을 검토한다.
- Platform Engineer: Architecture Plan과 생성 Patch를 검토한다.
- QA 및 보안 담당자: Acceptance Test와 Policy Gate를 승인한다.
- 연구자: Gold Configuration과 생성 결과를 비교한다.

## MVP 포함

- EMR 및 FHIR 연계
- PACS 및 DICOM Gateway와 MRI 및 CT Adapter
- Passwordless, MFA, RBAC 또는 ABAC, Zero Trust
- Clinical AI Agent와 선택적 AI Diagnosis
- Patient Mobile과 Patient BFF
- Cloud, On Premise, Hybrid 중 하나의 배포 Profile
- Docker Compose 또는 Kubernetes 실행 Profile
- Audit, Encryption, Monitoring, Traceability

## MVP 제외

- EMR 원무 및 진료 기능 전체
- 실제 의료기기 제어
- 실환자 PHI와 운영 Credential
- 자동 규제 인증
- 무중단 Runtime Dynamic SPL
- 모든 언어와 프레임워크에 대한 임의 코드 생성

## 기준 성공 조건

1. Gold Configuration이 Feature Model의 모든 제약을 통과한다.
2. 모순되는 요구는 Variant 생성 전에 차단되고 원인이 제시된다.
3. 변경 시나리오별 Feature Delta와 예상 Component Impact를 계산할 수 있다.
4. Requirement, Feature, Component, Test 사이의 식별자가 유지된다.
5. Critical 보안 위반이나 추적 링크 누락이 있으면 Release가 차단된다.

