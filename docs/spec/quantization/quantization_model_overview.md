# Quantization Model Overview
**Path:** `docs/spec/quantization/quantization_model_overview.md`  
**Version:** v1.0  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** Quantization Architect  
**Last Updated:** YYYY-MM-DD

---

## 1. 목적
프로젝트에서 채택한 정적 양자화 철학과 적용 범위를 요약한다. 모든 하위 스펙(bitwidth mapping, KV cache, mixed precision 정책)의 상위 문서 역할을 한다.

## 2. 목표
- 레이어별 Weight/Activation/KV bitwidth 분리.
- 메모리·DMA·Timing과 직접 연동되는 메타데이터 제공.
- Mixed precision 실험 시나리오(LLM-friendly) 지원.

## 3. 범위
| 카테고리 | 포함 내용 |
|----------|-----------|
| IR 주석 | LayerIR/TensorIR qbits 필드, QConfig 흐름 |
| 메모리 모델 | qbits→bytes 계산, alignment, packing |
| KV Cache | KV 전용 bitwidth, append 모델 |
| 정책 | 글로벌 기본값 + 레이어/헤드 override |

## 4. 워크플로우
```
ONNX → IRBuilder → Quantization Annotator → NPU IR(qbits 주입)
      → TileGraph/Allocator/Scheduler → CMDQ(qbits 필드 유지)
      → Simulator (DMA/TE/VE qbits 기반 모델)
```

Quantization 메타데이터는 다음 스펙들과 밀접하게 연결된다.

- IR 스펙: `docs/spec/ir/npu_ir_spec.md` (`qbits_weight`, `qbits_activation`, `qbits_kv` 필드)  
- CMDQ 스펙: `docs/spec/isa/cmdq_format_spec.md` (`qbits`, `qbits_weight`, `qbits_activation` 필드)  
- Timing 스펙: `docs/spec/timing/dma_timing_spec.md`, `te_timing_spec.md`, `ve_timing_spec.md` (bytes 계산 및 latency 모델)  
- Trace 스펙: `docs/spec/trace/trace_format_spec.md` (ENGINE_EVENT/summary에서 qbits 및 bytes/latency 메트릭 기록)

## 5. Config 예시
```yaml
quantization:
  defaults:
    weight: 4
    activation: 8
    kv: 4
  overrides:
    layer.ffn_out: { weight: 8, activation: 8 }
    layer.attn_qkv: { activation: 8 }
```

## 6. 품질 지표
- Latency 영향 (baseline 대비 %)
- DRAM bytes 감소량
- 정확도 영향 (외부 평가)

## 7. 참조 문서
- `quantization_ir_extension.md`
- `bitwidth_memory_mapping.md`
- `kv_cache_quantization_spec.md`
- `mixed_precision_policy.md`
