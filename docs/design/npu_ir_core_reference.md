# NPU-IR Core Reference (TOG-Compatible, Non-SSoT)

**Path:** `docs/design/npu_ir_core_reference.md`  
**Status:** Reference  
<!-- status: reference -->
**Owner:** Core Maintainers  
**Last Updated:** 2025-12-15

본 문서는 PyTorchSim TOG(Tile Operation Graph) 계열의 IR 개념을 이 코드베이스 관점에서 정리한 **참고(Reference)** 문서이다.

- 메인 IR의 단일 소스 오브 트루스(SSoT): `docs/spec/ir/npu_ir_spec.md`
- TileGraph 이후 선택적 IR(옵션): `docs/spec/ir/tile_ir_optional_spec.md`

---

## 0. Scope & Positioning

본 문서는 PyTorchSim TOG(Tile Operation Graph)를 정적 스케줄링 기반 NPU에 맞게 재정의한 “NPU-IR(코어)”의 개념적 골격을 정리한다.

이 IR은 다음을 동시에 만족한다.

- PyTorchSim TOG와 개념적구조적 호환
- 정적 스케줄링 NPU에서 실행 가능
- 컴파일러  시뮬레이터  CMDQ 백엔드의 공통 계약(Contract)

관련 문서:
- Tile IR(TDG/TileDesc/Tile ops, 메인 optional): `docs/spec/ir/tile_ir_optional_spec.md`
- 로어링/경계(Design): `docs/design/static_scheduler_design.md`, `docs/design/cmdq_generator_design.md`
- 실행 timebase/결정론(Design): `docs/design/cycle_loop_design.md`
- CMDQ/Barrier 의미론(Spec): `docs/spec/isa/cmdq_format_spec.md`

---

## 1. Design Principles

1. Tile is the atomic execution unit
2. Memory movement is explicit
3. Synchronization is explicit (Tag + Wait)
4. Loops are structural IR (not general control flow)
5. Compute latency is deterministic
6. IR is backend-agnostic

주의
- Instruction-level IR 아님
- Micro-op IR 아님

---

## 2. Top-Level Objects

### 2.1 NpuProgram

NpuProgram
  version string
  hw_profile HwProfile
  tensors TensorTable
  graphs list[NpuGraph]

### 2.2 HwProfile

HwProfile
  num_cores int
  te_shape [int, int]        # e.g. [64, 64]
  ve_lanes int               # SIMD width
  spm_size_bytes int
  spm_bank_count int
  dram_bw_GBps float
  noc_bw_GBps float

의도
- 컴파일 타임 타일 분해
- TLS 사이클 추정
- 자원 초과 검증

---

## 3. Tensor & Memory Model

### 3.1 Tensor

Tensor
  tensor_id string
  dtype f32  f16  bf16  int8  int4  i32
  shape [int]
  layout NCHW  NHWC  BLOCKED
  memory_space DRAM  SPM

### 3.2 MemRef

MemRef
  tensor_id string
  space DRAM  SPM  L0  L1
  dtype same as Tensor
  shape [int]
  base_addr optional[int]

---

## 4. Graph Structure

### 4.1 NpuGraph

NpuGraph
  name string
  entry NodeId
  nodes map[NodeId, NpuNode]
  edges list[Edge]

### 4.2 Edge

Edge
  src NodeId
  dst NodeId
  kind DATA  EVENT  CONTROL

Rules
- Loop scope 내부에서는 DAG
- 암묵적 순서 금지
- 모든 의존성은 Edge 또는 Tag로 표현

---

## 5. Address Expression

### 5.1 AFFINE (Tile Stride)

AddressExpr
  kind AFFINE
  base int
  terms
    - loop_id int
      stride int

의미
  addr = base + Σ(loop_idx  stride)

### 5.2 INDIRECT (KV  Sparse)

AddressExpr
  kind INDIRECT
  base int
  index_ref MemRef
  scale int

---

## 6. Tag & Synchronization Model

### 6.1 Tag

Tag
  tensor_id string
  tile_id string
  epoch int
  role LOAD  STORE  KV_LOAD  KV_STORE

Semantics
- Tag는 DMA 완료 이벤트를 의미
- Tag는 전역적으로 유일
- DmaWait은 tag completion barrier

---

## 7. Node Types

### 7.1 LoopBegin  LoopEnd

LoopBegin
  loop_id int
  loop_type PARALLEL  ACCUMULATION  INNER
  iter_begin int
  iter_end int
  iter_step int

Loop semantics
- PARALLEL core-level 분할
- ACCUMULATION 순차 누적 (decode)
- INNER TEVE 내부 루프

---

### 7.2 DMA Nodes

DmaLoad  DmaStore
  src MemRef
  dst MemRef
  bytes int
  addr AddressExpr
  tag Tag

DmaWait
  wait_tags [Tag]
  mode ALL

---

### 7.3 ComputeTile

ComputeTile
  engine TE  VE  SPARSE
  cycles int
  inputs [MemRef]
  outputs [MemRef]
  kernel_meta
    op string
    tile_shape [int]
    dtype string

---

## 8. Notes

- 본 문서는 IR의 구조와 의미를 정의한다.
- 실행 모델, 스케줄링, CMDQ 매핑은 별도 문서에서 정의한다.
