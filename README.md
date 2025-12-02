# RISCV_NPU_SoC_SIM
**Status:** Active  
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-02

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

### 타깃 및 범위

- **타깃 워크로드**: 모바일·엣지 환경의 LLM Inference(특히 Prefill/Decode 분리와 KV cache 재사용 시나리오).
- **SoC 구성**: RISC-V CPU + AXI 기반 NPU + DRAM/NoC/Interrupt, 정적 스케줄 기반 NPU 엔진(TE/VE/DMA/SPM).
- **활용 목적**: 정적 스케줄링의 성능/메모리 특성을 빠르게 검증하는 연구·실험용 시뮬레이터 및 오프라인 컴파일러.

---

## 2. 현재 구현 상태

| 영역 | 상태 | 비고 |
| --- | --- | --- |
| 문서 (Spec/Design/Test) | Stable Draft | SDD 기반 문서가 우선 정비되어 있으며, 개선 안은 `docs/process/doc_improvement_tasks.md`로 추적 |
| 오프라인 컴파일러 코드 (`src/compiler/`) | Planned | 스켈레톤만 존재, 문서를 기준으로 단계별 구현 예정 |
| NPU 시뮬레이터 (`src/simulator/`) | Planned | Global cycle loop/엔진 모델 구현 전 단계 |
| 공통 유틸/테스트 (`src/common/`, `tests/`) | Planned | Golden trace/테스트 플랜은 문서로 정의, 실제 코드/케이스는 차후 추가 |

---

## 3. 디렉터리 구조 (요약)

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

## 4. 문서 읽기 순서

이 레포지토리는 코드보다 문서를 먼저 업데이트하는 **Spec-Driven Development** 방식을 사용합니다.  
처음 레포지토리를 읽을 때는 아래 표 순서를 추천합니다.

| 순서 | 레벨 | 문서 | 설명 |
| --- | --- | --- | --- |
| 1 | 필수 | `docs/README_SPEC.md` | 전체 문서 인덱스와 구조 파악 |
| 2 | 필수 | `docs/overview/system_architecture.md` | 오프라인 컴파일러 + 시뮬레이터 아키텍처 개요 |
| 3 | 권장 | `docs/overview/dataflow_overview.md`, `docs/overview/module_responsibilities.md` | 데이터 플로우와 모듈 책임 정리 |
| 4 | 필수 | `docs/spec/ir/*.md` | 내부 IR, 양자화 확장, 텐서 메타데이터 스펙 |
| 5 | 필수 | `docs/spec/isa/*.md` | CMDQ 개념/포맷/opcode 정의 |
| 6 | 권장 | `docs/spec/timing/*.md` | DMA/TE/VE/SPM/Bus 타이밍 모델 |
| 7 | 권장 | `docs/spec/quantization/*.md`, `docs/spec/trace/*.md` | Quantization 정책과 Trace/Visualization 스펙 |
| 8 | 참고 | `docs/design/*.md` | 컴파일러·시뮬레이터·툴 설계 세부 |
| 9 | 참고 | `docs/test/*.md` | 테스트 전략/계획, Golden trace 요구사항 |

---

## 5. 개발 및 기여 가이드 (요약)

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
