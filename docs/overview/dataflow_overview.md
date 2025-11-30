NPU System Dataflow Overview

Version: v1.0
Status: Stable Draft
<!-- status: complete -->
Owner: System Architect
Last Updated: YYYY-MM-DD

1. 목적 (Purpose)

이 문서는 NPU Simulator & Offline Compiler 전체 파이프라인의 데이터 흐름(Dataflow) 을 상위 수준에서 정의한다.
데이터가:

ONNX → IR → TileGraph → CMDQ → Simulator → Trace → Visualization

까지 어떤 단계들을 거치며
2) Mixed precision, tile, SPM allocation, TE/VE scheduling, KV cache, memory bandwidth
등이 실제로 어떻게 흐름에 반영되는지를 정리한다.

본 문서는 개발자/리뷰어가 전체 시스템을 빠르게 이해하고
각 단계가 생산하는 산출물의 의미와 연계를 명확히 이해할 수 있도록 하는 상위 아키텍처 문서이다.

2. 전체 Dataflow 요약

전체 흐름은 아래와 같다.

   ┌────────────────┐
   │  ONNX Model    │
   └───────┬────────┘
           │
           ▼
   ┌────────────────┐
   │  IR Builder    │
   └───────┬────────┘
           │
   (Quantization Annotation: W/A/KV bit)
           │
           ▼
   ┌─────────────────────────┐
   │  Tiling Planner & SPM   │
   │      Allocator          │
   └────────┬────────────────┘
            │
            ▼
   ┌─────────────────────────┐
   │    Static Scheduler     │
   └────────┬────────────────┘
            │
            ▼
   ┌─────────────────────────┐
   │      CMDQ Generator     │
   └────────┬────────────────┘
            │
            ▼
   ┌─────────────────────────┐
   │   NPU Simulator (TE/VE) │
   └────────┬────────────────┘
            │
            ▼
   ┌─────────────────────────┐
   │  Trace & Visualization  │
   └─────────────────────────┘

3. 단계별 Dataflow 상세
3.1 ONNX Model

입력은 일반적인 ONNX 그래프이며 다음 정보를 포함한다.

Weight 텐서 (FP32 or FP16)

Activation flow

Layer 구조 (Normalization, Attention, MLP 등)

Attribute: kernel, stride, axis, epsilon 등

Dataflow 관점

단순 참조용 정적 그래프이며 NPU 구조에 맞지 않음

문제: layout 불일치, quantization 정보 없음, tile 구조 없음
→ IR Builder에서 NPU-friendly한 형태로 변환 필요

3.2 IR Builder (NPU IR 생성)

IR Builder는 ONNX → NPU IR 변환을 수행한다.

주요 변환 내용

LayerIR 생성

GEMM, LN, QKV_PROJ, SOFTMAX, GELU 등 NPU-friendly layer로 재정의

attributes 정규화

TensorIR 생성

activation/weight/KV 텐서를 구조화

shape/layout을 TE/VE-friendly 형태로 정규화

Quantization Annotation

Layer별: W-bit / A-bit / KV-bit 적용

bitwidth = memory traffic & compute cycle에 직접 반영됨

Graph 정규화

fusion: MatMul + BiasAdd

LN/RMSNorm normalization

shape propagation

3.3 Quantization Annotation (Mixed Precision)

Dataflow 상에서 매우 중요한 단계.

목적

bitwidth → byte traffic → bandwidth → latency 로 이어지는 전체 흐름을 결정

Layer별 mixed precision 설정 (W/A/KV 각각 독립)

에너지/성능/정확도 트레이드오프 분석 가능

데이터 흐름 영향

bitwidth는 다음에서 사용됨:

DMA_LOAD/STORE tile당 total bytes 계산

SPM allocation 크기 계산

TE/VE 계산 latency (가중치 압축 등)

DRAM bandwidth occupancy

즉, quantization은 단순히 데이터 타입이 아니라 모든 downstream 단계에 직접적인 영향을 미친다.

3.4 Tiling Planner & SPM Allocator

IR 기반으로 Layer를 tile 단위로 나누고,
SPM(Scratchpad Memory)에 allocation 한다.

3.4.1 TileGraph 생성

각 LayerIR → 여러 TileNode로 분해됨.

GEMM: (M_tile, N_tile, K_tile)

LN: (length_tile)

Softmax: (seq_tile)

Attention: head dimension 단위 tile

KV cache: seq 증가에 맞춘 append tile

TileGraph는 tile-level DAG이며 CMDQ 생성의 기반이 된다.

3.4.2 SPM Allocation

각 tile에 대해 SPM bank/offset을 배정:

Tile → SPM bank (0~N-1)
     → IFM offset
     → WGT offset
     → OFM offset


SPM 모델 요소:

multi-bank 구조

port conflict

bank conflict

bitwidth-aware capacity

Dataflow 영향

SPM allocation이 수행되어야:

DMA generator가 정확한 DRAM→SPM 주소를 생성

TE/VE가 tile input/output 주소를 참조

SPM conflict 모델이 timing에 반영됨

3.5 Static Scheduler (정적 스케줄러)

TileGraph + SPM info + TE/VE resource info를 기반으로
정적 스케줄을 생성한다.

역할

tile 간 데이터 의존성 분석

DMA → TE/VE → DMA 흐름 생성

multi-TE/VE 병렬 처리 고려

SPM conflict 회피를 위한 ordering

barrier / deps_before 관계 생성

산출물

스케줄러는 다음 형태의 tile-level sequence를 생성한다.

LOAD tile0
LOAD tile1
TE_GEMM_TILE tile0
TE_GEMM_TILE tile1 (in parallel on TE1)
STORE tile0
VE_LAYERNORM tile0
...


모든 결과는 CMDQ Generator가 사용할 dependency graph 형태로 넘겨진다.

3.6 CMDQ Generator

Static Scheduler의 tile-level DAG →
실제 CMDQ JSON 문서로 변환한다.

핵심 역할

DMA_LOAD_TILE / DMA_STORE_TILE 생성

TE_GEMM_TILE / VE_LN_TILE / VE_SOFTMAX_TILE 생성

deps_before/deps_after를 ID 기반으로 치환

END 명령 생성

Layer-level → tile-level → CMDQ-entry-level flattening 수행

데이터 출력 예시
CMDQ[0] = DMA_LOAD_TILE (ifm)
CMDQ[1] = DMA_LOAD_TILE (wgt)
CMDQ[2] = TE_GEMM_TILE (tile0)
CMDQ[3] = TE_GEMM_TILE (tile1)
CMDQ[4] = DMA_STORE_TILE (ofm)
CMDQ[5] = END


CMDQ는 시뮬레이터의 유일한 입력이다.

3.7 NPU Simulator

시뮬레이터는 cycle-based global loop로 동작하며,
CMDQ의 명령을 fetch/issue/execute 한다.

Simulator Dataflow

CMDQ Fetch

opcode → DMA/TE/VE 엔진 선택

deps_before 조건 검사

Job Issue

해당 엔진의 job queue에 push

engine busy/free 상태 추적

Job Execute

DMA: qbits, num_elements 기반 DRAM traffic 계산

TE: m×n×k MAC ops → latency

VE: vector length 기반 latency

Trace 기록

start_cycle / end_cycle

busy ratio

bandwidth usage

SPM conflict count

Next CMDQ entry

3.8 Trace & Visualization
Trace Engine 데이터

timeline events

dram bandwidth occupancy

te/ve utilization

spm_bank_conflict heatmap

per-layer latency breakdown

quantization sensitivity plot

Visualization Output

Gantt chart

Bandwidth Heatmap

TE/VE Utilization Bars

Memory Traffic Graph

KV Cache Growth Graph (LLM-only)

4. LLM-Oriented Dataflow

LLM의 경우 Dataflow가 매우 중요하게 변한다.

4.1 Q/K/V Projection
input → GEMM (Q)
input → GEMM (K)
input → GEMM (V)


세 GEMM tile이 서로 다른 weight/qbits일 수 있으므로
IR 및 CMDQ 레벨에서 별도 연산으로 분리한다.

4.2 Attention

Q @ K^T

Softmax

Attention @ V

TileGraph에서는 head dimension과 seq dimension을 기준으로 타일링한다.

4.3 KV Cache

KV Cache는:

activation과 bitwidth가 다르고

DRAM residency가 있고

append/concat 형태로 seq 증가하는 특성을 가진다.

KV Cache tile은 다음 시나리오를 따른다.

Seq old N → append tile (N+1)
DMA_LOAD_TILE (past K/V)
TE_GEMM_TILE (compute)
DMA_STORE_TILE (new K/V)


이는 CMDQ에 명확하게 표현된다.

5. Dataflow Summary Diagram (Text-based)
                    ┌────────────────────────┐
                    │        ONNX           │
                    └───────────┬───────────┘
                                ▼
                    ┌────────────────────────┐
                    │        IR Builder      │
                    │ (LayerIR, TensorIR)    │
                    └───────────┬───────────┘
         (W/A/KV bit annotation)│
                                ▼
                    ┌────────────────────────┐
                    │ Tiling Planner / SPM   │
                    │   (TileGraph Build)    │
                    └───────────┬───────────┘
                                ▼
                    ┌────────────────────────┐
                    │    Static Scheduler    │
                    │  (deps & ordering)     │
                    └───────────┬───────────┘
                                ▼
                    ┌────────────────────────┐
                    │     CMDQ Generator     │
                    └───────────┬───────────┘
                                ▼
                    ┌────────────────────────┐
                    │   NPU Simulator Core   │
                    │ (DMA/TE/VE Pipeline)   │
                    └───────────┬───────────┘
                                ▼
                    ┌────────────────────────┐
                    │ Trace / Visualization  │
                    └────────────────────────┘

6. 설계 철학과 연계
6.1 정적 스케줄 기반

CMDQ는 완전히 offline 결정

runtime 제어 flow 없음

dataflow는 항상 “deterministic"

6.2 Engine-Aware Dataflow

TileGraph → multi-TE/VE mapping

load-balance를 고려한 scheduler 설계

6.3 Bitwidth-aware Dataflow

bitwidth가 dataflow의 모든 단계에 반영된다:

SPM capacity

DMA bytes

TE ops

DRAM bandwidth

latency

6.4 LLM-friendly Dataflow

KV cache와 attention 타일의 dataflow는
Transformer 구조에 최적화된 정보 흐름을 제공한다.

7. 결론 (Summary)

본 Dataflow Overview 문서는
시스템 전체의 데이터 처리 흐름을 상위 수준에서 정의한다.

이 문서의 목표:

단계 간 데이터 형식/의미 명확화

IR → TileGraph → CMDQ 전환 과정 이해

Simulator의 input/output relation 이해

Mixed precision / multi-engine / KV cache 등의 복잡한 흐름을 단순화

팀원/리뷰어의 전체 아키텍처 빠른 이해 보조

본 문서는 system_architecture.md와 함께
전체 Spec-driven 개발의 최상위 설계 문서로 사용된다.