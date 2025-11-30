# Mixed Precision Policy Specification
**Path:** `docs/spec/quantization/mixed_precision_policy.md`  
**Version:** v1.0  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** Quantization Architect  
**Last Updated:** YYYY-MM-DD

---

## 1. 목적
레이어/역할/타겟별로 서로 다른 bitwidth를 적용하기 위한 정책(QConfig) 구조와 적용 절차를 정의한다.

## 2. 정책 계층
1. **Global 기본값:** 프로젝트 공통 bitwidth.
2. **Module/Layer override:** 레이어 ID 기반 지정.
3. **Fine-grain override (선택):** head, tensor role, tile 범위.

## 3. QConfig 포맷
```yaml
defaults:
  weight: 4
  activation: 8
  kv: 4
layers:
  ffn_block_3:
    weight: 4
    activation: 8
  attn_block_2:
    kv: 4
    heads:
      0: { kv: 4 }
      1: { kv: 8 }
```
`Quantization Annotator`는 QConfig를 읽어 LayerIR/TensorIR qbits 필드를 업데이트한다.

## 4. 정책 평가 루프
1. baseline run (예: FP16) → accuracy 참조.
2. mixed precision 후보 적용 → 시뮬레이터 latency/traffic 측정.
3. 정확도 영향 허용 범위 내인지 외부 평가와 비교.

## 5. 가드레일
- 허용 bitwidth 집합 `{2,4,8,16}`.
- KV는 activation보다 낮은 bitwidth 허용 가능하나 weight보다 낮아선 안 됨 같은 프로젝트별 규칙 정의.
- CMDQ generation 전에 모든 qbits 필드가 설정되어야 함.

## 6. 자동화 포인트
- YAML QConfig → JSON IR patching 스크립트.
- 실험 매트릭( latency, bytes, accuracy )을 CSV로 축적하여 정책 튜닝.

## 7. 참조
- `quantization_model_overview.md`
- `quantization_ir_extension.md`
