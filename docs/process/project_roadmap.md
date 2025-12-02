# Project Roadmap — RISCV_NPU_SoC_SIM
**Status:** Draft v1  
**Owner:** TBD  
**Last Updated:** 2025-12-02

---

# 1. Overview

`RISCV_NPU_SoC_SIM` 프로젝트는 모바일·임베디드 NPU 아키텍처를 대상으로  
**IR → Compiler Pass → CMDQ → Cycle-Accurate Simulator → Trace/Visualization → DSE**  
까지 포함하는 **엔드투엔드 AI 하드웨어 시뮬레이션 플랫폼** 구축을 목표로 한다.

본 Roadmap은 다음 문서들을 상위 지침으로 삼아 작성된다.

- `milestone_plan.md` (Phase 기반 구현 계획)
- `vibe_coding_sdd_guide.md` (SDD + Codex 개발 원칙)
- `docs/spec/**` (기능·동작 정의)
- `docs/design/**` (모듈 설계)
- `docs/process/**` (개발 프로세스, 네이밍 규칙, PRD/TDD workflow)

---

# 2. High‑Level Architecture

프로젝트 전체는 다음 6개 서브시스템으로 구성된다.

```
┌──────────────────────────────┐
│         Workload Loader       │  (ONNX)
└──────────────┬───────────────┘
               │
┌──────────────▼──────────────┐
│        Compiler Pipeline     │
│  IR Builder → Tiling → SPM   │
│  Alloc → Scheduler → CMDQ    │
└──────────────┬──────────────┘
               │ CMDQ
┌──────────────▼──────────────┐
│     Cycle-Based Simulator    │
│   ControlFSM + Engines(TE/VE)│
│   DMA + SPM + DRAM           │
└──────────────┬──────────────┘
               │ Trace
┌──────────────▼──────────────┐
│     Trace & Visualization    │
│ Gantt, BW Heatmap, Timeline  │
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│      DSE / Scenario Engine   │
│  Config Sweep / Comparison   │
└──────────────────────────────┘
```

---

# 3. Roadmap Structure

전체 개발은 다음 5개의 Stage로 구성된다.

1. **Stage A — Foundation (Phase 0~1)**  
   코드 스켈레톤 구축 + MatMul-only E2E 파이프라인 완성  
2. **Stage B — NPU Timing & Engine Modeling (Phase 2)**  
   TE/VE/DMA/SPM/DRAM 타이밍 모델 기반의 현실적 시뮬레이터 구축  
3. **Stage C — Full Operator Support (Phase 3)**  
   Conv·Attention을 포함한 Transformer 연산 전체 지원  
4. **Stage D — LLM Specialization (Phase 4)**  
   Quantization, KV cache, Prefill/Decode 모드 지원  
5. **Stage E — DSE Platform (Phase 5)**  
   Config Sweep, 시나리오 실험, Report Generator  

아래는 각 Stage별 목표·범위·결과물을 요약한다.

---

# 4. Stage A — Foundation (Phase 0~1)

## 목표
- 코드 스켈레톤과 디렉터리 구조 확립
- MatMul-only 파이프라인을 세로로 관통
- SDD 기반 개발 루틴 안정화

## 산출물
- `riscv_npu_sim/` 패키지 구조
- IR/Tensor/Quant/CMDQ/Trace dataclass
- Compiler Pass skeleton (MatMul 전용)
- Simulator core + TE Engine 최소 버전
- Trace Writer 최소 버전
- 통합 테스트: `test_single_matmul_pipeline.py`

---

# 5. Stage B — NPU Timing & Engine Modeling (Phase 2)

## 목표
- 주요 엔진의 타이밍 모델을 스펙 기반으로 구현
- 자원 경합 모델링(SPM bank conflict, DRAM latency/BW)
- TE/VE/DMA 엔진의 overlap을 Cycle 단위로 재현

## 산출물
- TE/VE/DMA/Bus/NoC/DRAM/SPM timing 모듈
- 자원 상태 기반 ControlFSM dispatch 정책
- 확장된 Trace (BW/time/gantt-friendly)
- Unit test suite (timing correctness)

---

# 6. Stage C — Full Operator Support (Phase 3)

## 목표
- Conv/Attention IR + Tiling + Scheduling + CMDQ + Engine까지 end‑to‑end 구현
- Tiling/Scheduling 정책 변경이 성능 차이를 명확히 드러내도록 설계

## 산출물
- Conv IR & Tile Planner
- Attention IR & KV access 모델
- Conv/Attn용 CMDQ opcode
- Tiling/Scheduling 정책 파라미터화
- Mixed-operator E2E tests (MatMul+GELU+Attention)

---

# 7. Stage D — LLM Specialization (Phase 4)

## 목표
- Quantization, KV cache, Prefill/Decode 모드 도입  
- 모바일 NPU 기반 LLM inference 성능 분석 기능 확보

## 산출물
- QuantMeta 기반 bitwidth → memory mapping
- KV cache quant/latency/spm layout
- Prefill/Decode별 CMDQ 스케줄
- Trace: KV access, sequence length, attention cost 등

---

# 8. Stage E — DSE Platform (Phase 5)

## 목표
- 다양한 NPU config 조합을 자동으로 돌리고 결과를 비교·시각화하는 플랫폼 구축

## 산출물
- DSE Engine  
- Scenario YAML  
- CLI (`sim run`, `sim dse`)  
- Summary reports (latency, BW, engine util, hotspots)  
- Viewer 연동

---

# 9. Development Principles

본 Roadmap은 다음 개발 원칙에 따라 진행한다.

- **SDD 원칙**  
  문서(스펙/설계)가 구현을 주도하며 Codex는 집행자 역할
- **Vertical-first**  
  얇은 E2E 파이프라인을 먼저 완성
- **Modular & Replaceable**  
  엔진/타이밍/스케줄러는 모두 플러그인 구조 유지
- **Trace-first Design**  
  모든 결과는 trace로 수집, 뷰어에서 표현 가능해야 함
- **Test-first for Core Logic**  
  엔진·타이밍·스케줄러는 단위 테스트 기반 구현

---

# 10. Timeline (Indicative)

```
Stage A: 2–4 weeks
Stage B: 4–6 weeks
Stage C: 4–8 weeks
Stage D: 3–5 weeks
Stage E: 4–6 weeks
```

맨 처음에는 Stage A~B를 우선적으로 수행하고,  
필요 시 LLM Stage(D)보다 Conv/Attention Stage(C)를 먼저 진행할 수 있다.

---

# 11. Roadmap 관리 방법

- 모든 Task는 `milestone_plan.md`와 ID로 연결  
  - 예: `(P1-C-IRB-001)`, `(P2-S-TE-004)`
- Codex Vibe Coding 시에는 `vibe_coding_sdd_guide.md`의 템플릿 사용
- Task 완료 시:
  1. 해당 위치 문서 업데이트  
  2. 코드 PR + 테스트  
  3. Roadmap Task 체크  
  4. Trace 기반 성능 sanity 검사  

---

# 12. 결론

`RISCV_NPU_SoC_SIM`은  
**문서 기반 SDD → 코드 기반 구현 → Trace 기반 검증 → DSE 기반 최적화**  
라는 통합 워크플로를 중심으로 개발되는 NPU 시뮬레이터 프로젝트이다.

본 Roadmap은 "전체 구조의 방향성"을 제공하며,  
구체적인 Task·TODO는 `milestone_plan.md`에서 관리한다.
