# Opcode Set Definition
**Path:** `docs/spec/isa/opcode_set_definition.md`  
**Version:** v1.1  
**Status:** Stable Draft  
<!-- status: complete -->
**Owner:** ISA Architect  
**Last Updated:** 2025-12-04  

---

## 1. 목적 (Purpose)
CMDQ 기반 ISA에서 사용되는 **opcode 전체 집합과 카테고리**를 정의하고,  
각 opcode가 어느 엔진에서 어떤 역할을 하는지, 어떻게 확장해야 하는지를 명시한다.  
`cmdq_overview.md`, `cmdq_format_spec.md`를 “개념/포맷”으로 보고, 이 문서는 “목록/정책” 역할을 한다.

## 2. 카테고리 개요
- **DMA Class**  
  - DRAM↔SPM 데이터 이동, 타일 단위 전송.  
  - 예: `DMA_LOAD_TILE`, `DMA_STORE_TILE`, (옵션) `DMA_PREFETCH_TILE`.
- **Tensor Engine(TE) Class**  
  - GEMM/Conv 등 매트릭스 연산 타일.  
  - 예: `TE_GEMM_TILE`, (향후) `TE_CONV_TILE`, `TE_SPARSE_GEMM_TILE`.
- **Vector Engine(VE) Class**  
  - LayerNorm/Softmax/GELU 등 벡터 기반 연산.  
  - 예: `VE_LAYERNORM_TILE`, `VE_SOFTMAX_TILE`, `VE_GELU_TILE`.
- **Sync / Control Class**  
  - 동기화 및 제어 흐름.  
  - 예: `BARRIER`, `SYNC_GROUP`, `NOP`, `END`.
- **LLM Extension Class**  
  - KV cache, rotary embedding, attention score 등 LLM 특화 연산.  
  - 기본적으로 DMA/TE/VE opcode를 재사용하되, 필요한 경우 별도 opcode(`KV_STORE_TILE`, `KV_LOAD_TILE`)를 사용한다.

## 3. 공통 메타 필드
모든 CMDQ 엔트리는 다음 공통 필드 집합을 공유한다 (`cmdq_format_spec.md` 참고).

| 필드              | 설명                                                |
|-------------------|-----------------------------------------------------|
| `opcode`          | 명령 종류 문자열                                   |
| `id`              | CMDQ 내 index (0‑based)                            |
| `layer_id`        | 연관 LayerIR ID (없을 수 있음)                     |
| `deps_before`     | issue 전 완료되어야 할 엔트리 ID 목록              |
| `deps_after`      | 이후 엔트리가 참조하는 완료 조건 (선택)           |
| `debug`           | 주석/출처 등 디버그용 메타데이터                  |

본 문서에서는 opcode별로 **추가 필드(required/optional)**와 **engine binding**을 정의한다.

## 4. DMA Class Opcode

### 4.1 DMA_LOAD_TILE
- **목적:** DRAM → SPM 방향 타일 로드.
- **Engine:** DMAEngine.
- **주요 필드(추가):**
  - `tensor_role` (weight / activation / kv / embedding)
  - `qbits`
  - `dram_addr`
  - `spm_bank`, `spm_offset`
  - `num_elements`
  - (옵션) `stride_bytes`

### 4.2 DMA_STORE_TILE
- **목적:** SPM → DRAM 방향 타일 저장.
- 필드는 `DMA_LOAD_TILE`와 동일 구조이나, 보통 `direction="write"`로 해석.

### 4.3 DMA_PREFETCH_TILE (옵션)
- **목적:** 향후 prefetch 모델 도입 시 사용.  
  실행 의미는 load와 유사하나, 소비 엔진 실행보다 앞서 발생하여 SPM에 미리 data를 배치.

## 5. Tensor Engine(TE) Class Opcode

### 5.1 TE_GEMM_TILE
- **목적:** GEMM/MatMul 타일 실행.
- **Engine:** `TensorEngine[te_id]`.
- **주요 필드(추가):**
  - `te_id`
  - `ifm_bank`, `ifm_offset`
  - `wgt_bank`, `wgt_offset`
  - `ofm_bank`, `ofm_offset`
  - `m`, `n`, `k`
  - `qbits_weight`, `qbits_activation`

### 5.2 (향후) TE_CONV_TILE, TE_SPARSE_GEMM_TILE
- Conv, sparse GEMM 등은 별도 opcode로 확장하되,  
  기존 GEMM opcode의 의미는 변경하지 않는다.
- **Attention 전용 TE opcode**  
  - 필요 시 `TE_QKT_TILE`(Q × Kᵀ), `TE_AV_TILE`(Attention weighted value) 등으로 명명한다.  
  - 필드 구조는 `TE_GEMM_TILE`과 동일하며, `tensor_role`(q/k/v) 정도만 달라진다.

## 6. Vector Engine(VE) Class Opcode

### 6.1 VE_LAYERNORM_TILE
- **목적:** LayerNorm 타일 처리.
- **Engine:** `VectorEngine[ve_id]`.
- **주요 필드:**
  - `ve_id`
  - `in_bank`, `in_offset`
  - `out_bank`, `out_offset`
  - `length`
  - `qbits_activation`
  - (옵션) `eps`

### 6.2 VE_SOFTMAX_TILE / VE_GELU_TILE
- Softmax/GELU 등은 `length`, `qbits_activation` 외에  
  필요 시 approximation mode, temperature 등의 속성을 확장 필드로 갖는다.

## 7. Sync / Control Class Opcode

### 7.1 BARRIER
- **목적:** 여러 엔트리의 완료를 기다린 뒤 이후 엔트리를 issue.
- **필드:**
  - `wait_for`: 기다릴 CMDQ entry id 리스트.

### 7.2 SYNC_GROUP (옵션)
- 여러 엔트리를 “그룹”으로 묶어 group 단위로 동기화할 때 사용 가능.

### 7.3 END / NOP
- `END`: CMDQ 실행 종료, Host에 완료 신호 전달.  
- `NOP`: 디버깅/정렬 목적, 실행 의미 없음.

## 8. LLM Extension Class Opcode

### 8.1 KV_STORE_TILE (0x30)
- **목적:** SPM에 있는 K/V 타일을 DRAM의 KV cache에 append/write-back. Prefill/Decode 공통 사용.
- **Engine:** DMAEngine (`kv_store` 채널로 구분 가능).
- **주요 필드(추가):**
  - `head_id` (필수): multi-head 구분.
  - `kv_kind` (필수): `k` 또는 `v`.
  - `spm_bank`, `spm_offset` (필수): 소스 타일 위치.
  - `dram_base_addr` (필수): KV cache 베이스 주소.
  - `t_start`, `t_len` (필수): 토큰 시퀀스 범위.
  - `d_start`, `d_len` (선택): head dimension 범위(partial KV slice가 필요한 경우).
  - `qbits_kv` (필수): KV bitwidth.
  - (선택) `kv_layout_id`: 레이아웃/stride 프로파일 ID.

### 8.2 KV_LOAD_TILE (0x31)
- **목적:** DRAM의 KV cache에서 특정 범위(K/V)를 SPM으로 fetch. 주로 Decode 단계에서 사용.
- **Engine:** DMAEngine (`kv_load` 채널로 구분 가능).
- **주요 필드(추가):**
  - `head_id` (필수): multi-head 구분.
  - `kv_kind` (필수): `k` 또는 `v`.
  - `spm_bank`, `spm_offset` (필수): 목적지 타일 위치.
  - `kv_range_desc` (필수): KV fetch 범위 서술자 포인터 또는 인라인 구조.
    - `t_start`, `t_len`: 토큰 시퀀스 범위.
    - `d_start`, `d_len`: head dimension 범위.
  - `qbits_kv` (필수): KV bitwidth.
  - (선택) `kv_layout_id`: 레이아웃/stride 프로파일 ID.

### 8.3 기타 LLM 연산
- Q/K/V projection, attention score, rotary embedding 등은  
  TE/VE opcode를 재사용하되 `tensor_role`/`op_mode`로 구분하거나, 필요 시 `ATTN_*` prefix opcode로 확장한다.

## 9. 확장/변경 정책
1. **기존 opcode 의미 변경 금지**  
   - breaking change가 필요하면 새 opcode를 추가하고, `opcode_set_definition.md`에 명시.
2. **새 opcode 추가 시**  
   - 카테고리, engine binding, 필수/선택 필드, 실행 의미를 모두 정의해야 한다.
3. **Deprecated 관리**  
   - 사용 중단 opcode는 `deprecated_since` 메타 필드와 이 문서에 함께 기록.
4. **버전 관리**  
   - opcode 세트에 breaking change가 발생하면 `Version`을 올리고,  
     CMDQ generator / simulator가 해당 버전을 인식하도록 한다.

## 10. 참조 문서
- `cmdq_overview.md`  
- `cmdq_format_spec.md`  
- `npu_ir_spec.md`  
- `docs/references/p2_riscv_npu/xNPU_ISA_v1_kv_extension_full.md`
