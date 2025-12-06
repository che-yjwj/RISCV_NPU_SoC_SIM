# Gantt Timeline Specification
**Path:** `docs/spec/trace/gantt_timeline_spec.md`  
**Version:** v1.0  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-04

---

## 1. 목적
시뮬레이터 타임라인 이벤트를 Gantt 차트로 시각화하기 위한 필드, 렌더링 규칙, 검증 절차를 정의한다.

## 2. 이벤트 구조
- 입력: `trace_format_spec.md`의 `ENGINE_EVENT`.
- 필수 필드: `engine`, `engine_id`, `cmdq_id`, `layer_id`, `tile_id`, `start_cycle`, `end_cycle`.
- 옵션 필드: `deps`, `color_hint`, `quantization_bits`, `notes`.

## 3. 시각화 규칙
| 항목 | 규칙 |
|------|------|
| 축 | X축=cycle, Y축=engine lane |
| 색상 | 엔진 타입별 기본 팔레트 (DMA=blue, TE=green, VE=orange, CTRL=gray) |
| 겹침 | 동일 엔진에서 겹치는 이벤트는 스택 표시, idle 구간은 연한 회색 |
| 주석 | deps/토큰 구간은 상단 마커로 강조 |

## 4. 데이터 파이프라인
```
trace.json → timeline normalizer → (optional) filtering/grouping → renderer
```
CLI/GUI 모두 JSON→SVG/PNG/HTML export를 지원.

## 5. Validation
- `start_cycle <= end_cycle`.
- Gantt 범위는 trace summary `cycles_total`을 초과하지 않아야 함.
- CMDQ id가 timeline 시퀀스에 존재하는지 확인.

## 6. 최소 필드 표 (ENGINE_EVENT 매핑)

| 필드 | 타입 | 필수 여부 | 설명 |
| --- | --- | --- | --- |
| `engine` | string | 필수 | `"DMA"`, `"TE"`, `"VE"`, `"HOST"` 등 |
| `engine_id` | int | 필수 | Y축 lane 식별자 |
| `start_cycle` | int | 필수 | Gantt bar 시작 |
| `end_cycle` | int | 필수 | Gantt bar 끝 |
| `layer_id` | string/null | 권장 | 레이어/모듈 구분용 라벨 |
| `tile_id` | string/null | 옵션 | 타일 단위 식별자 |
| `cmdq_id` | int | 권장 | CMDQ와 상호 점프 시 사용 |
| `color_hint` | string/null | 옵션 | 강조가 필요한 경우 커스텀 색상 힌트 |

## 6. 인터랙션 요구사항(옵션)
- 범위 선택/줌, 엔진/레이어 필터, 토큰 경계 jump.

## 7. 향후 확장
- stall 이벤트 오버레이.
- multi-node 동기화 선 표현.
- hot path 자동 강조.

---

## 8. LLaMA Prefill/Decode 타임라인 예시
`llama_attention_timeline_full.md`를 기반으로, LLaMA Self-Attention에서 주로 관찰되는 타임라인 패턴을 요약한다. Trace 이벤트는 `trace_format_spec.md`의 `phase`/`token_index` 메타데이터를 사용해 Prefill/Decode 구간을 구분한다.

### 8.1 연표(Phase별 주요 단계)

| Phase | 주요 CMDQ/Trace 이벤트 | 엔진 |
| --- | --- | --- |
| Prefill – QKV Projection | `DMA_LOAD_TILE(X/Wq/Wk/Wv)` → `TE_MATMUL_TILE(Q/K/V)` | DMA, TE |
| Prefill – KV Store | `KV_STORE_TILE(K_t)`, `KV_STORE_TILE(V_t)` | KV DMA |
| Prefill – Output Projection | `TE_QKT_TILE`, `VE_SOFTMAX_TILE`, `TE_AV_TILE`, `TE_MATMUL_TILE`, `DMA_STORE_TILE` | TE, VE, DMA |
| Decode – KV Load | `KV_LOAD_TILE(K_all/V_all)` (t 증가에 비례) | DMA |
| Decode – QKᵀ/Softmax/Attn·V | `TE_QKT_TILE`, `VE_SOFTMAX_TILE`, `TE_AV_TILE` | TE, VE |
| Decode – Output Projection | `TE_MATMUL_TILE`, `DMA_STORE_TILE` | TE, DMA |

### 8.2 간단한 텍스트 타임라인

```
Prefill:
 DMA : |--Load X/W--|    |--KV Store--|
 TE  :      |--Q/K/V MatMul--|      |--QKᵀ--|      |--Attn·V--|   |--Out MatMul--|
 VE  :                                |--Softmax--|
 KV  :                  |--Store K/V--|
 SYNC:          [wait]         [wait]       [wait]

Decode (token loop):
 DMA :      |--KV Load--|
 TE  :            |--QKᵀ--|      |--Attn·V--|   |--Out MatMul--|
 VE  :                 |--Softmax--|
 SYNC:          [wait]        [wait]
```

### 8.3 시각화 팁
- Prefill/Decode 경계에 `MARKER_EVENT`를 추가하여 타임라인 상단에 phase band를 그린다.
- Token별 latency를 강조하려면 `TOKEN_EVENT`의 `start_cycle/end_cycle`을 사용해 상단에 별도 레인을 표시한다.
- KV-load 지연이 전체 latency에 미치는 영향을 보기 위해 DMA 레인에 `stall_event` 오버레이를 추가한다.

이 예시는 `docs/test/golden_trace_examples.md`의 `GT-LLM-01`와 연계해 시뮬레이터 타임라인 시각화를 검증할 때 활용할 수 있다.
