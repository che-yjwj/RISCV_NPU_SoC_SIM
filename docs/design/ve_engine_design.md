# Vector Engine Design
**Path:** `docs/design/ve_engine_design.md`  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** TBD  
**Last Updated:** YYYY-MM-DD

---

## 1. 목적
Vector Engine(VE)은 LayerNorm, Softmax, GELU 등 **벡터/element-wise + reduction 연산의 tile latency**를 모델링한다.  
이 문서는 VE job 모델, SIMD 처리율, 타이밍 계산을 정의한다.

관련 스펙:
- `docs/spec/timing/ve_timing_spec.md`
- `docs/spec/isa/cmdq_format_spec.md` (`VE_*_TILE`)

## 2. 책임
- **입력**
  - `VE_LAYERNORM_TILE`, `VE_SOFTMAX_TILE`, `VE_GELU_TILE` 등 CMDQ 엔트리.
  - SPM 내 입력/출력 텐서 위치 (bank/offset).
  - VE 성능 파라미터 (lanes, ops_per_lane, SFU latency 등).
- **출력**
  - VE job completion 이벤트.
  - VE 관련 `ENGINE_EVENT` trace (op_type, length, qbits_activation, start/end cycle).
- **주요 역할**
  - length, qbits, op 종류에 따라 element-wise, reduction, SFU latency를 조합.
  - multi-VE 환경에서 per-VE busy 시간 추적.
- **하지 말아야 할 일**
  - DMA/TE 역할 수행.
  - tile 배치/스케줄링 변경.

## 3. 내부 구조

### 3.1 Job 구조
```python
class VeJob:
    cmdq_id: int
    ve_id: int
    op_type: str   # LAYERNORM_TILE, SOFTMAX_TILE, GELU_TILE ...
    length: int
    qbits_activation: int
    start_cycle: Optional[int]
    end_cycle: Optional[int]
```

### 3.2 VE 상태
- `busy_until_cycle[ve_id]`
- `job_queue[ve_id]`

## 4. 알고리즘 / 플로우

### 4.1 Latency 계산
`ve_timing_spec.md`에 정의된 공식을 따른다.

- 공통 형태:
```text
total_cycles =
  init_cycles
  + elementwise_cycles
  + reduction_cycles (있다면)
  + sfu_cycles (있다면)
  + finalize_cycles
```

- 예) LayerNorm:
  - mean/variance reduction + normalize pass + finalize.
- 예) Softmax:
  - max reduction → exp pass → sum reduction → normalize.

### 4.2 스케줄링
TE와 유사하게, VE는 busy-until 모델을 사용:
```pseudo
for each ve_id:
    if busy_until_cycle[ve_id] <= current_cycle and job_queue[ve_id] not empty:
        job = job_queue[ve_id].pop()
        job.start_cycle = current_cycle
        job.end_cycle = current_cycle + latency(job)
        busy_until_cycle[ve_id] = job.end_cycle
        emit_engine_event_start(job)

    if just_reached(job.end_cycle):
        emit_completion_event(job.cmdq_id)
        emit_engine_event_end(job)
```

## 5. 인터페이스
- `VeEngine.submit(job: VeJob) -> None`
- `VeEngine.step(cycle: int, trace_engine) -> list[CompletionEvent]`
- `VeEngine.is_busy(ve_id: int) -> bool`

구성 파라미터:
- SIMD lanes, ops_per_lane_factor.
- `sfu_latency_exp`, `sfu_latency_rsqrt`, `reduction_pipeline_latency`.
- bitwidth scaling 함수.

## 6. 예시 시나리오
- 긴 sequence의 Softmax tile을 여러 VE에 분배하여  
  길이에 따른 latency scaling 및 multi-VE load balance를 trace로 확인.

## 7. 향후 확장
- rotary embedding, log-softmax 등 새로운 연산 타입 추가.
- fused 연산 (예: LN + residual add)용 opcode와 timing 모델.
- gather/scatter 패턴과 VE 연동.
