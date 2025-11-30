# IR Builder Design
**Path:** `docs/design/ir_builder_design.md`  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** TBD  
**Last Updated:** YYYY-MM-DD

---

## 1. 목적
IRBuilder는 ONNX 그래프를 NPU IR(Graph + TensorTable)로 변환하는 모듈이다.  
이 문서는 ONNX→LayerIR/TensorIR 매핑 규칙과 내부 구조를 정의한다.

관련 스펙:
- `docs/spec/ir/npu_ir_spec.md`
- `docs/spec/ir/tensor_metadata_spec.md`
- `docs/spec/ir/quantization_ir_extension.md`

## 2. 책임
- **입력**
  - ONNX Graph (노드, 텐서, attribute).
  - 선택적 초기 QConfig (기본 bitwidth 정보).
- **출력**
  - NPU IR:
    - Graph: LayerIR 노드, edges.
    - TensorTable: TensorIR 메타데이터.
- **주요 역할**
  - ONNX 노드를 NPU-friendly op_type(GEMM, LAYER_NORM, QKV_PROJ 등)으로 정규화.
  - 텐서 shape/layout/role/qbits 기본값 설정.
  - fusion/split 규칙 적용 (예: MatMul+Add→GEMM, Q/K/V projection 등).
- **하지 말아야 할 일**
  - 타일링/스케줄링/주소 계산.
  - 정확한 qbits 결정(이는 Quantization Annotator가 담당).

## 3. 내부 구조

### 3.1 주요 컴포넌트
- `OnnxLoader`
  - ONNX 파일을 로드하고 내부 중간 표현(ONNX IR)을 구성.
- `GraphNormalizer`
  - opset 변환, 불필요한 노드 제거, 패턴 기반 fusion 수행.
- `LayerIrBuilder`
  - 정규화된 그래프를 순회하며 LayerIR 노드 생성.
- `TensorTableBuilder`
  - 모든 텐서에 대해 TensorIR 메타데이터 생성.

### 3.2 데이터 구조
```python
class LayerIr:
    id: str
    op_type: str
    inputs: list[str]
    outputs: list[str]
    attributes: dict
    shape: dict
    qbits_weight: Optional[int]
    qbits_activation: Optional[int]
    qbits_kv: Optional[int]
```

## 4. 알고리즘 / 플로우

### 4.1 ONNX → NPU op 매핑
- 예:
  - `MatMul + Add` → `GEMM`
  - `LayerNormalization` → `LAYER_NORM`
  - `Attention` 관련 서브그래프 → `QKV_PROJ`, `ATTN_SCORE`, `ATTN_OUTPUT`

### 4.2 Tensor 메타데이터 생성
1. ONNX 값 정보에서 shape/dtype 추출.
2. role 결정:
   - parameter: `weight` / `embedding`
   - intermediate activation: `activation`
   - KV cache 관련 텐서: `kv`
3. layout 설정:
   - Transformer: `[B, T, H]`, `[B, H, T, D]` 등.
4. qbits 초기값:
   - global defaults 또는 QConfig에서 가져오되,  
     실제 적용은 Quantization Annotator에서 finalize.

## 5. 인터페이스
- `IrBuilder.build(onnx_model, qconfig) -> NpuIr`
  - 내부에서 위 컴포넌트를 순차적으로 호출.

구성 파라미터:
- fusion on/off, LLM-specific 패턴 활성화 여부.
- naming 규칙 설정 (layer_id, tensor_id prefix 등).

## 6. 예시 시나리오
- simple MLP ONNX 모델에 대해:
  - `Linear → GEMM + BIAS`, `ReLU` 그대로.
  - TensorTable에 weight/activation 텐서가 올바른 role/layout/qbits로 생성되는지 확인.

## 7. 향후 확장
- 더 복잡한 패턴 (swin, conv+bn+relu) fusion.
- multi-graph/branching 지원.
