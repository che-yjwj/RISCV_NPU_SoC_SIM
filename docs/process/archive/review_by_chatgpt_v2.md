# RISCV_NPU_SoC_SIM — Full Documentation Review

본 문서는 `docs/` 디렉토리(단, `docs/references/` 제외)의 모든 문서에 대한 리뷰를 통합한 문서이다.  
각 문서의 목적, 현재 수준, 강점, 부족한 점, 그리고 향후 개선 방향을 명확히 정리하여  
코드베이스의 문서 완성도를 끌어올리는 데 목적이 있다.

---

# 1. Top-Level 문서

## 1.1 docs/README_SPEC.md

### ✔ Summary
문서 집합의 엔트리 포인트 역할을 하는 상위 문서로, spec-driven 구조를 설명하는 핵심 문서.

### ✔ Strengths
- 전체 카테고리를 정리해 문서 네비게이션 역할 수행
- SDD 기반 개발 방향성을 명확히 표현

### ✖ Weaknesses
- 시스템 아키텍처 개요가 부족함  
- 독자가 읽어야 할 문서 우선순위 부재  
- 전반적인 pipeline(onnx→ir→compile→sim)이 명확히 드러나지 않음

### ⭐ Recommendations
- `docs/overview/*` 문서와 연결하는 navigation section 추가  
- 전체 시스템 아키텍처 도식 포함  
- “Documentation Reading Guide” 섹션 추가

---

# 2. Design Directory 리뷰

아래 문서들은 시뮬레이터의 핵심 모듈들을 정의한다.

문서 목록:
```
cmdq_generator_design.md
control_fsm_design.md
cycle_loop_design.md
dma_engine_design.md
ir_builder_design.md
npu_simulator_core_design.md
offline_compiler_design.md
spm_allocator_design.md
static_scheduler_design.md
te_engine_design.md
ve_engine_design.md
tiling_planner_design.md
visualizer_design.md
```

---

## 2.1 cmdq_generator_design.md

### ✔ Summary
StaticScheduler 및 Tile Planner의 산출물을 기반으로 CMDQ를 생성하는 모듈의 정의.

### ✔ Strengths
- Tile-level ScheduleDAG → CMDQ entry 흐름 정의
- CMDQ 생성이 pipeline 내 위치가 명확함

### ✖ Weaknesses
- CMDQ JSON schema가 충분히 상세하지 않음  
- 예제(CMDQ entry 예시)가 없음  
- dependency resolution 규칙이 단편적  

### ⭐ Recommendations
- CMDQ JSON Schema 문서화  
- TE/VE/DMA tile 예제 CMDQ 생성 과정 추가  
- StaticScheduler → CMDQ 의 stage별 mapping flow 추가  

---

## 2.2 control_fsm_design.md

### ✔ Strengths
- Control FSM의 상태 기반 업데이트 방식을 기술  
- Cycle loop 내에서 FSM의 역할이 명확

### ✖ Weaknesses
- CPU/NPU 경계에서 역할 명확화 필요  
- FSM 상태 정의가 미흡  
- 이벤트/인터럽트 처리 흐름 부재  

### ⭐ Recommendations
- FSM 상태 다이어그램(mermaid) 추가  
- idle/blocked/starved 등의 state semantics 정의  
- NPU-CPU 인터페이스 시그널 목록 명세화  

---

## 2.3 cycle_loop_design.md

### ✔ Strengths
- “Global cycle loop = 전체 시뮬레이터의 tick 단위 메커니즘”을 명확히 선언  
- 각 엔진/메모리 업데이트 순서가 기술됨

### ✖ Weaknesses
- clock domain 차이(예: CPU 2GHz / NPU 1GHz) 처리 규칙 미비  
- stall/bandwidth/latency 반영 기준 부족  
- trace event timestamp 규칙 부재  

### ⭐ Recommendations
- 각 엔진/메모리의 `cycles_per_global_tick` 개념 추가  
- TE/VE/DMA contention 모델을 표로 정의  
- Trace flush 규칙 정의  

---

## 2.4 dma_engine_design.md

### ✔ Strengths
- DMA → BUS → SPM 흐름 설명  
- 모바일 NPU에서 DMA의 중요성을 잘 포착함

### ✖ Weaknesses
- DRAM bank conflict, burst length, arbitration 미비  
- 여러 DMA 요청의 priority 및 schedule 미정  
- SPM refill 정책 문서화 부족  

### ⭐ Recommendations
- Arbitration (RR, fixed-pri, dynamic-pri) 규칙 명시  
- DRAM latency model(`tRCD`, `tCL`, `bank conflict penalty`) 포함  
- SPM line-based vs tile-based refill 정책 문서화  

---

## 2.5 ir_builder_design.md

### ✔ Strengths
- ONNX → 내부 IR로 변환하는 프레임워크를 정의  
- IR node 구조 개략 제시

### ✖ Weaknesses
- IR spec이 개요 수준에 그침  
- IR 필드, 타입, quant, layout 등의 구체 구조 미비  
- IR pass pipeline 부재  

### ⭐ Recommendations
- `spec/npu_ir_spec.md` 파일로 확장  
- Pass pipeline 명시:
  ```
  ONNX → Canonicalize → ShapeInference → Tiling → MemoryPlan → Scheduling → CMDQ → ISA Lowering
  ```
- IR node 구조/필드의 테이블 정의

---

## 2.6 npu_simulator_core_design.md

### ✔ Strengths
- SimulatorCore를 top-level aggregator로 정의  
- 전체 구조를 하나의 entry point로 단일화한 점 탁월

### ✖ Weaknesses
- 내부 모듈간 관계를 나타내는 diagram 미비  
- init → run → finalize lifecycle 없음  
- multi-thread 시 사용 여부 문서화되지 않음  

### ⭐ Recommendations
- Core architecture diagram 추가  
- Simulator public API 정의  
- NPU-CPU 하위 인터페이스 스펙 포함  

---

## 2.7 offline_compiler_design.md

### ✔ Strengths
- Offline compile pipeline을 별도로 설계  
- 모바일 정적 스케줄링 방식과 일치

### ✖ Weaknesses
- Compiler artifacts 정의가 불충분  
- layer-by-layer vs whole-model compile 비교 없음  

### ⭐ Recommendations
- output schema 정의(tile.json, schedule.json, cmdq.json)  
- Offline compiler pipeline 그래프 제공  

---

## 2.8 spm_allocator_design.md

### ✔ Strengths
- SPM allocator를 독립 모듈로 정의  
- tile-level allocation 구조가 반영됨

### ✖ Weaknesses
- SPM fragmentation handling 없음  
- bank conflict 고려 부족  
- direct-mapped / set-assoc 선택이 불명확  

### ⭐ Recommendations
- 2D tile-aware allocation 설명  
- SPM bank conflict 모델링 추가  
- SPM 조회/할당 비용 함수 정의  

---

## 2.9 static_scheduler_design.md

### ✔ Strengths
- 모바일 NPU에 적합한 정적 스케줄링 기반  
- tile DAG 기반 접근이 적절

### ✖ Weaknesses
- 스케줄 우선순위 규칙 미정  
- TE/VE/DMA 스케줄 조합 규칙 부족  
- dependency solver 기능 미문서화  

### ⭐ Recommendations
- priority-based scheduling 규칙 정의  
- unified DAG 예시 추가  

---

## 2.10 te_engine_design.md

### ✔ Strengths
- TE의 tile 연산 모델 정의  
- Tensor Engine의 역할 구분이 명확

### ✖ Weaknesses
- pipeline stage 부족  
- systolic array 기반 latency 모델 없음  
- VE와의 차별화 요소가 부재  

### ⭐ Recommendations
- pipeline stage(fetch → load → compute → store) 정의  
- tile-to-array mapping 규칙 명세  
- TE-specific latency 공식 포함  

---

## 2.11 ve_engine_design.md

### ✔ Strengths
- VE를 독립 엔진으로 명확히 분리  
- SIMD 기반 벡터 연산 흐름 존재

### ✖ Weaknesses
- lane 수, vector width 명시 없음  
- reduction latency 미문서화  
- TE-VE 간 병렬 실행 조건 부재  

### ⭐ Recommendations
- SIMD lane diagram 추가  
- reduction/accumulate 대기시간 정의  
- TE/VE scheduling conflict model 추가  

---

## 2.12 tiling_planner_design.md

### ✔ Strengths
- LLM workloads의 핵심: tile planning을 따로 분리  
- Tiling planner 구조가 명확

### ✖ Weaknesses
- tile size 탐색 알고리즘 설명 부족  
- TE/VE tile size 상호작용 없음  
- DRAM–SPM 비용 모델 미비  

### ⭐ Recommendations
- LLM attention/FFN용 tiling 규칙 정의  
- 타일 search space 정의  
- 비용 함수(cost function) 명시  

---

## 2.13 visualizer_design.md

### ✔ Strengths
- timeline/trace 기반 시각화 구조 정의  
- Gantt chart 형태의 목표 명확

### ✖ Weaknesses
- trace schema 설명 부족  
- memory bandwidth, stall breakdown visualization 부재  

### ⭐ Recommendations
- JSON trace schema 정의  
- 예시 timeline 추가  
- bandwidth/stall plotter 설계 문서화  

---

# 3. Overview Documents

### ✔ Strengths
- architecture overview 작성을 위한 기반은 존재

### ✖ Weaknesses
- system overview, dataflow overview, memory/noC overview가 부재  
- 전체 문서 네비게이션 포인트 부족  
- IR/Compiler/Simulator/Tracer의 전체 흐름이 하나의 페이지에 없음  

### ⭐ Recommendations
필수 신규 문서:
```
docs/overview/system_architecture_overview.md
docs/overview/compute_dataflow_overview.md
docs/overview/memory_noc_overview.md
docs/overview/sdd_devflow_overview.md
```

---

# 4. Test Documents

## test/test_plan.md  

### ✔ Strengths
- 테스트 계획 문서가 별도 존재하는 점 우수

### ✖ Weaknesses
- Unit/Integration/E2E 테스트의 범위가 아직 불명확  
- 각 모듈의 pass criteria가 없음  

### ⭐ Recommendations
- “Layer 별 테스트” + “Pipeline 전체 테스트” 정의  
- CI 기준(정확성 + 성능 추세) 정의  

---

# 5. Simulator Architecture — 종합 개선 방향

### 🔥 Problems Identified
1. 모듈별 문서는 있으나 전역 통합 그림이 없음  
2. IR → Tiling → Memory Plan → Schedule → CMDQ → ISA → Cycle Loop 단계 연결 부재  
3. TE/VE/DMA/SPM/DRAM timing 모델이 부족  
4. 모든 문서가 skeleton 수준  
5. Trace & Visualizer 문서가 미완성  

### 🌟 Recommended Strategic Direction
- Phase 0: overview 문서 먼저 강화  
- Phase 1: IR/ISA/CMDQ/Schedule/Timing spec을 단일 pipeline으로 묶기  
- 모든 Design 문서에 상위 Spec 참조 포함  
- LLaMA block 전체 예제 추가  

---

# 6. Conclusion
본 리뷰 문서는 향후 문서/아키텍처 정비 작업의 기준점이 된다.  
각 문서에 존재하는 강점을 기반으로 더욱 일관된 SDD 문서 체계를 구축하면  
시뮬레이터의 유지보수성과 확장성이 크게 향상될 것이다.

---

# 7. Revision History

| Version | Date | Notes |
|--------|------|--------|
| 1.0 | 2025-12-02 | Full documentation review 최초 생성 |