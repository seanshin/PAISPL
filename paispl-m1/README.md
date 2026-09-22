# PAISPL M1 Prototype

M1은 Sprint 0 설계 자산을 실행 가능한 Requirement IR Validator와 Feature Constraint Engine으로 연결한다.

## 기능

- Requirement IR JSON Schema 검증
- 자연어에서 추출된 Intent를 Feature include, exclude, replace, preserve 연산으로 적용
- Mandatory, Parent, Group Cardinality, Requires, Excludes 전파와 검증
- 기존 Configuration을 기준으로 순차 변경 처리
- Feature Delta와 Intent to Feature Trace 출력
- Gold Configuration과의 Exact Match 자동시험

## 실행

```bash
python -m paispl_m1.cli validate-ir \
  --design-root ../paispl-sprint0 \
  ../paispl-sprint0/examples/BASE-HOSP-001.requirement-ir.json

python -m paispl_m1.cli solve-sequence \
  --design-root ../paispl-sprint0
```

개발 환경에서는 `PYTHONPATH=src`를 지정하거나 패키지를 Editable Mode로 설치한다.

## M1 경계

M1은 코드 저장소를 생성하지 않는다. 출력은 Solver로 검증된 Feature Configuration과 Delta, Trace Link다. 이 결과는 M2 Architecture Synthesizer의 입력 계약이 된다.

