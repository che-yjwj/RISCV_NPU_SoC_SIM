# RISCV_NPU_SoC_SIM

RISC-V 기반 SoC 상에서 동작하는 NPU 아키텍처를 대상으로 하는  
정적 스케줄 기반 시뮬레이터 & 오프라인 컴파일러용 레포지토리입니다.  
이 레포지토리는 **Spec-Driven Development(SDD)** 원칙에 따라, 스펙 문서를 최우선으로 관리합니다.

---

## 1. 프로젝트 개요

`RISCV_NPU_SoC_SIM`의 목표는 다음과 같습니다.

- ONNX 기반 AI/LLM 모델을 입력으로 받는 오프라인 컴파일러
  - ONNX → 내부 IR → 타일링(Tiling) → 정적 스케줄링 → CMDQ(Command Queue) 생성
- CMDQ 기반 NPU 시뮬레이터
  - TE/VE/DMA/SPM/DRAM/NoC를 포함한 자원·메모리 중심 성능 분석
  - latency, bandwidth, utilization 등을 예측하는 분석용 시뮬레이터
- 시각화 및 프로파일링
  - 타임라인, bandwidth heatmap, 엔진 utilization 등
- Mixed-precision quantization, KV-cache 등 LLM 친화적인 아키텍처 실험 지원

자세한 시스템 아키텍처는 `docs/overview/system_architecture.md`를 참고하세요.

---

## 2. 디렉터리 구조 (요약)

```text
README.md             # 프로젝트 상위 소개
docs/                 # 스펙·설계·프로세스·테스트 문서
  overview/           # 시스템/데이터플로 개요
  spec/               # IR / ISA / Timing / Trace 스펙
  design/             # 컴파일러·시뮬레이터 설계 문서
  process/            # SDD 워크플로, 리뷰/네이밍 규칙
  test/               # 테스트 전략 및 계획

src/                  # 구현 코드 (진행 중)
  common/             # 공용 유틸리티/타입
  compiler/           # 오프라인 컴파일러 파이프라인
  simulator/          # NPU 시뮬레이터 코어

tests/                # 테스트 코드 (unit / integration / golden 등)
tools/                # 유틸리티 스크립트 (문서 상태 체크 등)
```

---

## 3. 문서 읽기 순서

이 레포지토리는 코드보다 문서를 먼저 업데이트하는 **Spec-Driven Development** 방식을 사용합니다.  
처음 레포지토리를 읽을 때는 다음 순서를 추천합니다.

1. 상위 목차
   - `docs/README_SPEC.md`
2. 전체 아키텍처와 데이터 플로
   - `docs/overview/system_architecture.md`
   - `docs/overview/dataflow_overview.md`
   - `docs/overview/module_responsibilities.md`
3. 핵심 스펙 (IR / ISA / Timing / Quantization / Trace)
   - IR:  
     - `docs/spec/ir/npu_ir_spec.md`  
     - `docs/spec/ir/quantization_ir_extension.md`  
     - `docs/spec/ir/tensor_metadata_spec.md`
   - ISA / CMDQ:  
     - `docs/spec/isa/cmdq_overview.md`  
     - `docs/spec/isa/cmdq_format_spec.md`  
     - `docs/spec/isa/opcode_set_definition.md`
   - Timing / Quantization / Trace:  
     - `docs/spec/timing/*.md`  
     - `docs/spec/quantization/*.md`  
     - `docs/spec/trace/*.md`
4. 설계 및 테스트
   - Design: `docs/design/*.md`
   - Test: `docs/test/*.md`

문서 상태(complete/draft 등)는 아래 스크립트로 한 번에 확인할 수 있습니다.

```bash
python tools/doc_status.py
```

---

## 4. 개발 및 기여 가이드 (요약)

새 기능/확장을 추가할 때는 다음 순서를 따르는 것을 원칙으로 합니다.

1. 관련 **Spec 문서** 업데이트 (`docs/spec/…`)
2. 필요 시 **Design 문서** 업데이트 (`docs/design/…`)
3. 실제 **코드 구현** (`src/…`)
4. **테스트 케이스** 설계 및 추가 (`tests/…`)

자세한 워크플로와 리뷰 규칙은 다음 문서를 참고하세요.

- `docs/process/spec_driven_development_workflow.md`
- `docs/process/contribution_and_review_guide.md`
- `docs/process/naming_convention.md`
- `docs/process/versioning_and_changelog_guide.md`

현재 레포지토리는 스펙·설계 문서를 중심으로 구조를 먼저 정리하는 단계이며,  
시뮬레이터 및 컴파일러 구현은 순차적으로 확장될 예정입니다.
