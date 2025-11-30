# NPU Simulator Core Design
**Path:** `docs/design/npu_simulator_core_design.md`  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** TBD  
**Last Updated:** YYYY-MM-DD

---

## 1. 목적
NPU Simulator Core는 CMDQ를 입력으로 받아 **cycle 기반으로 DMA/TE/VE/메모리/Trace를 통합 시뮬레이션**하는 상위 모듈이다.  
이 문서는 Simulator Core의 서브모듈 구성, 데이터 흐름, 확장 포인트를 정의한다.

관련 스펙:
- `docs/overview/system_architecture.md`
- `docs/spec/isa/cmdq_overview.md`, `cmdq_format_spec.md`
- `docs/spec/timing/*.md`
- `docs/spec/trace/trace_format_spec.md`

## 2. 책임 (Responsibilities)
- **입력**
  - CMDQ(JSON) 및 실행 config (엔진 수, 타이밍 모델 파라미터, 메모리 구성).
  - Optional: IR/TileGraph snapshot (디버깅/Trace 메타용).
- **출력**
  - Trace 파일(JSON): timeline events, bandwidth samples, summary metrics.
  - 통계 객체: latency, DRAM bytes, 엔진별 utilization 등.
- **주요 역할**
  - Control FSM + CMDQExecutor를 통해 CMDQ fetch/deps/issue 제어.
  - DMA/TE/VE/MemoryModel/TraceEngine 인스턴스 생성·수명 관리.
  - Global cycle loop를 돌며 모든 엔진/버스/메모리/trace를 동기화.
- **하지 말아야 할 일**
  - CMDQ/IR 생성(컴파일러 영역).
  - 타이밍 모델 공식 변경(이는 timing spec 및 엔진 설계 문서에서 정의).

## 3. 내부 구조

### 3.1 서브모듈 구성
- `ControlFSM` / `CMDQExecutor`
  - CMDQ 엔트리 상태 관리: NOT_ISSUED / READY / ISSUED / COMPLETED.
  - deps_before 조건 만족 여부와 엔진 availability를 기반으로 issue.
- `DMAEngine[]`, `TensorEngine[]`, `VectorEngine[]`
  - 각각 `dma_timing_spec.md`, `te_timing_spec.md`, `ve_timing_spec.md`에 정의된 모델 구현.
- `MemoryModel`
  - `spm_model_spec.md`, `bus_and_noc_model.md`에 따른 SPM bank 및 Bus/NoC 모델.
- `TraceEngine`
  - `trace_format_spec.md`에 맞는 timeline_events, bandwidth_samples, summary_metrics 생성.
- `GlobalCycleLoop`
  - 전체 시스템을 하나의 cycle 타임스텝으로 업데이트.

### 3.2 주요 데이터 구조
- `SimulatorConfig`
  - `n_te`, `n_ve`, `n_dma`, DRAM/NoC/SPM 파라미터, quantization/timing 모델 선택.
- `SimulatorState`
  - 현재 cycle, CMDQ pointer, per-engine busy_until, 큐 길이, 통계 누적값.
- `EngineEventQueue`
  - 엔진 completion 이벤트를 ControlFSM/CMDQExecutor에 전달.

## 4. 알고리즘 / 플로우

### 4.1 초기화 시퀀스
1. Config 로딩 (`SimulatorConfig` 생성).
2. CMDQ JSON 파싱 → internal CMDQ entry 배열 생성.
3. ControlFSM/CMDQExecutor 초기화 (모든 엔트리 상태 NOT_ISSUED).
4. DMA/TE/VE/MemoryModel/TraceEngine 인스턴스 생성.

### 4.2 Global Cycle Loop 개략
```pseudo
cycle = 0
while not control_fsm.is_finished():
    # 1) 엔진 업데이트
    for dma in dma_engines:
        dma.step(cycle, memory_model, trace_engine)
    for te in tensor_engines:
        te.step(cycle, trace_engine)
    for ve in vector_engines:
        ve.step(cycle, trace_engine)
    memory_model.step(cycle, trace_engine)

    # 2) 완료 이벤트 처리
    control_fsm.consume_engine_events(engine_event_queue)

    # 3) CMDQ issue
    control_fsm.step_issue(cycle, cmdq, engines)

    cycle += 1

trace_engine.finalize()
```

### 4.3 종료 조건
- `END` opcode가 deps를 모두 만족하고 실행 완료된 시점에  
  ControlFSM이 `is_finished() == True`를 반환.

## 5. 인터페이스 (예시)

- Python 스타일 예시:
  - `SimulatorCore.run(cmdq_path: str, config: SimulatorConfig) -> TraceResult`
  - `SimulatorCore.step(cycles: int = 1)` : interactive 모드에서 사용 가능.
- 구성 파라미터:
  - 모드: full trace / summary only / validation only.
  - seed, debug level, 최대 cycle 수(safety guard).

## 6. 예시 시나리오

- **단일 GEMM 레이어 시나리오**
  1. Offline compiler가 GEMM 1개에 대한 CMDQ를 생성 (`DMA_LOAD_TILE` 2개, `TE_GEMM_TILE` 1개, `DMA_STORE_TILE` 1개, `END` 1개).
  2. SimulatorCore는 CMDQ를 읽고 cycle loop를 실행.
  3. 결과 trace에서 TE 엔진 busy 구간과 DRAM bandwidth를 확인.

## 7. 향후 확장
- 멀티 NPU / 멀티 core 시뮬레이션 지원 (여러 CMDQ를 병렬로 실행).
- partial re-simulation (특정 레이어/토큰 범위만 재시뮬레이션).
- 온디바이스 프로파일러와의 연동을 위한 trace 다운샘플링 모드.
