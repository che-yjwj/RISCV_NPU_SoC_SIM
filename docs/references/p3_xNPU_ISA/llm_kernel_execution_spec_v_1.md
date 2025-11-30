# LLM Kernel Execution Specification (v1)

## 1. Purpose & Scope
본 문서는 Transformer/LLM 1개 block(Attention + MLP)의 실행을 **xNPU ISA + MicroScheduler + Memory/NoC 모델** 관점에서 정의한다.

목표:
- QKV Projection ~ Attention(Softmax) ~ Value Projection ~ Output Projection ~ MLP까지의 전체 경로를, xNPU ISA 시퀀스와 Descriptor 기반으로 명시
- 각 단계에서 TE/VE, DMA, SRAM/DRAM, MicroScheduler가 수행해야 할 동작을 정의
- Py-V 기반 NPU 시뮬레이터가 LLM block 단위를 end-to-end로 실행할 수 있도록 요구사항을 제공

---

## 2. LLM Block 구조 (단일 Layer 기준)

### 2.1 연산 구성
1. Input: X ∈ R[B, T, H]
2. Q = X · Wq, K = X · Wk, V = X · Wv
3. Q', K', V'에 rotary embedding 적용(옵션)
4. Attention score S = softmax(QKᵀ / √d)
5. O_attn = S · V
6. O_proj = O_attn · Wo
7. Residual & Norm: Y1 = LN(X + O_proj)
8. MLP: Y2 = MLP(Y1) (GEMM1 → ACT → GEMM2)
9. Residual & Norm: Y_out = LN(Y1 + Y2)

### 2.2 하드웨어 매핑 개요
- **TE(TensorEngine)**: 모든 GEMM (Q/K/V, O_proj, MLP GEMM1/2)
- **VE(VectorEngine)**: LN/RMSNorm, Softmax(1D), Rotary, Activation, bias, residual
- **DMA+SRAM**: X, QKV, S, V, O_attn, Y1, Y2 등 텐서의 타일링과 DRAM↔SRAM 이동 담당
- **MicroScheduler**: 전체 job graph를 관리하고 TE/VE/DMA를 스케줄링

---

## 3. xNPU ISA 시퀀스 (High-Level)

### 3.1 ISA Primitive 가정
- `XNPU.MATMUL rd, rs1`       : GEMM/MatMul (TE)
- `XNPU.LAYERNORM rd, rs1`    : LayerNorm/RMSNorm (VE)
- `XNPU.SOFTMAX_1D rd, rs1`   : row-wise softmax (VE)
- `XNPU.ROTARY_1D rd, rs1`    : rotary embedding (VE)
- `XNPU.VOP rd, rs1`          : Activation/elementwise op (VE)
- `XNPU.WAIT rs1`             : token completion wait

`rs1`는 descriptor pointer, `rd`는 completion token을 받는다고 가정.

### 3.2 1 Block 실행 시 ISA 예시 (단순화)
```asm
# 1) Q/K/V Projection (3x GEMM)
XNPU.MATMUL   x10, a0      # desc_qkv_q
XNPU.MATMUL   x11, a1      # desc_qkv_k
XNPU.MATMUL   x12, a2      # desc_qkv_v

# 2) Rotary Embedding (optional)
XNPU.ROTARY_1D x13, a3     # desc_rotary_q
XNPU.ROTARY_1D x14, a4     # desc_rotary_k

# 3) Attention score: QK^T + Softmax
XNPU.MATMUL    x15, a5     # desc_qk_gemm (Q x K^T)
XNPU.SOFTMAX_1D x16, a6    # desc_softmax

# 4) Weighted sum: softmax(V)
XNPU.MATMUL    x17, a7     # desc_sv_gemm

# 5) Output projection GEMM
XNPU.MATMUL    x18, a8     # desc_o_proj

# 6) Residual + LN
XNPU.VOP       x19, a9     # desc_residual_add_1 (X + O_proj)
XNPU.LAYERNORM x20, a10    # desc_ln_1

# 7) MLP (GEMM1 → ACT → GEMM2)
XNPU.MATMUL    x21, a11    # desc_mlp_gemm1
XNPU.VOP       x22, a12    # desc_mlp_act
XNPU.MATMUL    x23, a13    # desc_mlp_gemm2

# 8) Residual + LN (출력)
XNPU.VOP       x24, a14    # desc_residual_add_2 (Y1 + Y2)
XNPU.LAYERNORM x25, a15    # desc_ln_2
```

각 명령은 비동기 job을 생성하고, `XNPU.WAIT` 또는 상위 레벨 동기화 규칙에 따라 completion을 기다릴 수 있다.

---

## 4. Descriptor 설계 (각 연산별)

### 4.1 공통 필드
```c
struct xnpu_tensor_desc {
    uint64_t src_addr;
    uint64_t dst_addr;
    uint32_t shape[4];      // B, T, H, 또는 B, H, T 등
    uint32_t stride[4];
    uint32_t dtype;         // FP16, BF16, FP32, INT8 등
    uint32_t flags;         // layout, transpose, etc.
};
```

### 4.2 MatMul Descriptor (GEMM)
```c
struct xnpu_matmul_desc {
    uint64_t a_addr;      // X 또는 Q/K/V/O_attn/Y1 등
    uint64_t b_addr;      // Wq/Wk/Wv/Wo/W1/W2 등
    uint64_t c_addr;      // 출력 텐서 주소
    uint32_t m, n, k;     // GEMM 크기
    uint32_t lda, ldb, ldc;
    uint32_t batch;       // batched GEMM
    uint32_t flags;       // transpose flags, bias enable, etc.
};
```

### 4.3 LayerNorm Descriptor
```c
struct xnpu_ln_desc {
    uint64_t src_addr;    // 입력 X or Y1 or Y2
    uint64_t dst_addr;
    uint64_t gamma_addr;
    uint64_t beta_addr;
    uint32_t hidden_size;
    float    eps;
    uint32_t batch;       // 전체 row 개수 (B*T 등)
    uint32_t flags;
};
```

### 4.4 Softmax Descriptor
```c
struct xnpu_softmax_desc {
    uint64_t src_addr;    // QK^T 결과
    uint64_t dst_addr;    // S (softmax 결과)
    uint32_t vec_len;     // softmax 적용 길이 (예: T)
    uint32_t outer_count; // B * num_heads * T 등
    uint32_t flags;       // causal, mask enable 등
};
```

### 4.5 Rotary Descriptor
```c
struct xnpu_rotary_desc {
    uint64_t src_addr;    // Q 혹은 K 텐서
    uint64_t dst_addr;
    uint64_t cos_addr;
    uint64_t sin_addr;
    uint32_t head_dim;
    uint32_t batch;
    uint32_t seq_len;
    uint32_t flags;       // interleaved 등
};
```

### 4.6 VOP Descriptor (Activation/Residual 등)
```c
struct xnpu_vop_desc {
    uint64_t src0_addr;   // 기본 입력
    uint64_t src1_addr;   // optional (residual/add용)
    uint64_t dst_addr;
    uint32_t len;         // element 개수
    uint32_t op_type;     // ADD, BIAS_ADD, GELU, SILU 등
    uint32_t flags;
};
```

---

## 5. MicroScheduler 관점의 Job Graph

### 5.1 Job Node 정의
각 ISA 명령은 내부적으로 하나 이상의 Job 노드로 분해된다.

예시: `XNPU.MATMUL(desc_qkv_q)` →
- DMA_IFM_Q (DRAM→SRAM)
- DMA_WGT_WQ
- TE_GEMM_Q
- DMA_OFM_Q (SRAM→DRAM)

### 5.2 Attention Block Job Graph (단일 head 개념)

순서:
1. Q/K/V GEMM jobs (3개 GEMM) + 각 GEMM에 대한 DMA jobs
2. (옵션) Rotary jobs
3. QK^T GEMM jobs
4. Softmax jobs
5. S·V GEMM jobs
6. Output projection GEMM jobs
7. Residual add + LN jobs
8. MLP GEMM1 → ACT → GEMM2 → Residual + LN jobs

MicroScheduler는 각 job 간의 dependency를 DAG로 유지하며, **ready && resource-available** 조건에서 job을 issue 한다.

---

## 6. Memory/NoC 관점의 데이터 흐름

### 6.1 DRAM ↔ SRAM Tile 흐름
- X, Q, K, V, S, O_attn, Y1, Y2, 최종 Y_out 등은 모두 DRAM 상에 배치
- 각 GEMM/LN/Softmax/Activation 실행 시, 필요한 sub-tensor/tile만 SRAM으로 이동

예: QK^T
1. Q_tile (B, head, T, d) → SRAM
2. K_tile (B, head, T, d) → SRAM
3. TE가 QK^T tile을 계산하여 SRAM의 S_tile에 저장
4. S_tile → DRAM 또는 SRAM 상에서 바로 softmax 실행 (구현 정책에 따라)

### 6.2 Bandwidth & Overlap
- DMAEngine은 다음 tile에 대한 prefetch job을 미리 수행
- TE/VE job이 실행되는 동안 다음 tile의 DMA job을 overlapping
- SRAM 용량 제한 및 bank conflict 규칙에 따라 prefetch depth 조정

---

## 7. Execution Phase 정리 (단일 Layer)

### Phase 1: Q/K/V Projection
- ISA: 3× `XNPU.MATMUL`
- Job: Q/K/V 각각에 대해 DMA_IFM, DMA_WGT, TE_GEMM, DMA_OFM
- Memory: X, Wq/Wk/Wv → DRAM; Q/K/V 결과도 DRAM 또는 SRAM
- 특징: TE 위주, VE 개입 없음

### Phase 2: Rotary (옵션)
- ISA: 2× `XNPU.ROTARY_1D` (Q, K)
- Job: DMA_Q, DMA_K, DMA_COS/SIN → VE_ROTARY → DMA write
- Memory: cos/sin LUT가 DRAM에 존재, 일부 SRAM에 캐시

### Phase 3: QK^T + Softmax
- ISA: `XNPU.MATMUL`(QK^T) + `XNPU.SOFTMAX_1D`
- Job: DMA_Q, DMA_K, TE_GEMM_S, VE_SOFTMAX
- Memory: S(QK^T 결과)은 tile 단위로 SRAM에 저장 후 Softmax 실행, 가능하면 DRAM 쓰기 전 Softmax까지 완료

### Phase 4: Attention Output (S·V)
- ISA: `XNPU.MATMUL`(S·V)
- Job: DMA_S, DMA_V, TE_GEMM_attn
- Memory: O_attn 생성

### Phase 5: Output Projection + Residual + LN
- ISA: `XNPU.MATMUL`(O_proj) + `XNPU.VOP`(residual add) + `XNPU.LAYERNORM`
- Job: TE_GEMM_O, VE_ADD, VE_LN
- Memory: X, O_proj, Y1 관리

### Phase 6: MLP (GEMM1→ACT→GEMM2)
- ISA: `XNPU.MATMUL` + `XNPU.VOP` + `XNPU.MATMUL`
- Job: TE_GEMM1, VE_ACT, TE_GEMM2

### Phase 7: 최종 Residual + LN
- ISA: `XNPU.VOP`(Y1+Y2) + `XNPU.LAYERNORM`
- Job: VE_ADD, VE_LN → 최종 Y_out

---

## 8. Synchronization & Token 사용 패턴

### 8.1 Token 기반 의존성 관리
각 ISA 명령은 token(rd)를 반환할 수 있음:

```asm
XNPU.MATMUL   x10, a0   # Q
XNPU.MATMUL   x11, a1   # K
XNPU.MATMUL   x12, a2   # V

XNPU.WAIT     x10
XNPU.WAIT     x11
XNPU.WAIT     x12

XNPU.MATMUL   x13, a5   # QK^T
```

하지만 일반적으로는 MicroScheduler 내부 DAG로 의존성을 관리하고, ISA 레벨에서는 최소한의 WAIT만 사용하거나, 상위 레벨에서는 전혀 WAIT를 사용하지 않을 수도 있다.

### 8.2 Layer-Level Barrier
- 한 Layer 전체를 하나의 Launch 단위로 보고, Layer 끝에서만 CPU sync
- 내부 LN/Softmax/MLP 간 의존성은 MicroScheduler가 관리

---

## 9. KV Cache 연동 (간단 버전)

### 9.1 K/V Cache Layout
- DRAM 상에 `[B, num_heads, T_total, head_dim]` 형태
- 새로운 토큰이 올 때마다 마지막 T 위치에 append

### 9.2 Execution에서의 차이점
- K/V GEMM 결과는 직접 KV cache DRAM 영역에 써야 함
- QK^T 연산에서는 **과거 timestep 포함 전체 K를 읽어야 함**

MicroScheduler는 seq_len 증가에 따라 K/V DMA 양이 증가하는 것을 반영해야 한다.

---

## 10. Profiling Points (LLM-Specific)

### 10.1 관심 메트릭
- Q/K/V Projection GEMM time
- QK^T GEMM vs Softmax time 비율
- S·V GEMM time
- Output Projection vs MLP time
- LN/Softmax/Activation(VE) 비중
- DRAM BW 사용량 (Per Phase)
- SRAM bank conflict count (Per Phase)

### 10.2 이벤트 태깅
각 job/phase 별로 phase ID를 태깅하여:
- Phase별 latency
- Phase별 BW/Utilization 분석 가능하도록 설계

---

## 11. 확장 계획
1. Grouped-Query Attention(GQA), Multi-Query Attention(MQA)에 대한 별도 descriptor 확장
2. FlashAttention 스타일의 SRAM tile 재사용 및 S/Softmax/O_attn를 완전 on-chip에서 처리하는 패턴 지원
3. KV cache shard/partition 모델링 (NoC/다중 NPU 코어 환경)
4. Mixture-of-Experts(MoE) MLP 구조에 대한 job graph 패턴 정의

---

