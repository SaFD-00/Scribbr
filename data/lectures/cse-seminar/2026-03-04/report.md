# Log-Structured Filesystem in the Era of AI - Seminar Report

**Speaker**: Youjip Won | **Affiliation**: KAIST (School of Electrical Engineering) | **Date**: 2026-03-04
**Research Area**: Operating Systems, Storage Systems

---

## 1. Research Motivation & Problem

### 연구 배경 및 동기

Log-Structured File System (LFS)은 1991년 Rosenblum과 Ousterhout에 의해 SOSP에서 처음 발표된 write-optimized file system이다. LFS의 핵심 아이디어는 random write를 sequential write로 변환하는 것으로, 새로운 데이터를 기존 위치에 overwrite하지 않고 log의 끝에 append하는 방식이다. Sequential write는 random write보다 훨씬 빠르기 때문에, 이 접근법은 이론적으로 매우 우수한 성능을 제공한다.

### 핵심 문제: Garbage Collection

LFS의 가장 큰 문제는 **garbage collection (GC)**이다. 지속적인 append 방식으로 인해 invalidated block이 누적되고, 결국 free block이 고갈되면 이를 정리하는 GC가 필수적이다. GC 과정에서 victim segment를 선택하고, valid block을 새 위치로 복사한 뒤 기존 segment를 해제해야 하는데, 이 과정이 foreground write를 차단하여 **성능의 예측 불가능성(unpredictable tail latency)**을 초래한다.

### 기존 접근법의 한계

- LFS는 발표 후 **약 27년(1991~2018)**이 지나서야 Android의 F2FS로 처음 실제 production에 배포됨
- Flash storage 자체도 내부적으로 GC를 수행하므로, F2FS + Flash storage 조합은 **이중 GC (dual GC)** 문제를 야기
- 실험 결과, file system GC가 device GC보다 application 성능에 **훨씬 더 치명적**인 영향을 미침
- 기존 연구들은 주로 storage device의 GC를 host가 대신 수행하도록 하는 데 집중했으나, 더 영향이 큰 file system GC를 제거하는 연구는 부족했음

---

## 2. Methodology & Contributions

발표자는 file system GC를 제거하거나 완화하기 위한 세 가지 접근법(Episode 1~3)을 시간순으로 소개하였다.

### Episode 1: IPLFS - Infinite Partition LFS (2022)

**핵심 아이디어**: File system GC가 발생하는 근본 원인은 partition 크기가 제한적이기 때문이다. Virtual memory가 제한된 물리 DRAM 위에 거대한 가상 주소 공간을 제공하듯, **file system partition을 가상적으로 무한하게 확장**한다.

- 64-bit LBA 주소 체계를 활용하여 $2^{64}$ sectors = **8 Zettabyte** partition 정의
- Active valid block이 LBA 공간에서 계속 전진하므로, invalidated block을 정리할 필요가 없음
- GC 전용 metadata (block bitmap, reverse map)가 불필요해지므로 metadata도 절감
- 8ZB partition 매핑을 위해 flat table 대신 **interval mapping (tree 기반)** 구조 사용

**실험 결과**: 성능 변동이 약 40% 수준으로 안정화 (GC로 인한 급격한 성능 저하 제거)

### Episode 2: D2FS - Device-Driven File System GC (2025)

**핵심 아이디어**: GC를 완전히 제거하는 대신, **storage device가 file system의 GC를 대신 수행**하도록 한다.

IO stack에서 두 단계의 매핑이 존재한다:
- **F2L mapping** (host): File inode + offset → LBA
- **L2P mapping** (device): LBA → Physical Page Address (PPA)

Device가 자체 GC 수행 시, 동시에 file system의 logical block도 재배치하고, 변경된 매핑 정보를 host에 동기화한다.

**세 가지 핵심 기법**:
1. **Coupled Garbage Collection**: Device GC와 file system GC를 하나의 연산으로 결합
2. **Migration Upcall**: Device → Host 방향으로 갱신된 F2L mapping 정보 전달 (기존 IO stack의 정보 흐름 방향을 역전)
3. **Virtual Overprovisioning**: File system partition을 물리 용량의 약 1.2배로 확장하여 free segment 고갈 방지

**IPLFS 대비 장점**: IPLFS는 8ZB partition을 device가 관리해야 하므로 tree 기반 L2P mapping의 merge/split 오버헤드가 크지만, D2FS는 partition을 storage 용량의 1.2배 수준으로만 설정하면 충분

**실험 결과**: 기존 F2FS는 GC 시작 시 성능이 급락하지만, D2FS는 **GC overhead가 보이지 않을 정도로 안정적인 성능** 유지

### Episode 3: AI 시대의 새로운 과제 (Zoned Storage)

AI workload의 IO 패턴 분석 (A100 GPU + NVMe, LLaMA 6.7B):
- LLM inference의 KV Cache: **sequential write + random read** 패턴
- Flash device에 최적화된 패턴이지만, edge device의 제한된 SRAM으로 인해 page/block mapping이 불가
- **Zone mapping**이 자연스러운 선택 → Google이 Zoned UFS를 추진하는 이유

**새로운 문제**: Zone 크기가 **1GB**로 매우 크기 때문에, 단일 zone의 GC latency가 2MB segment 대비 극도로 김 → 효율적인 1GB region cleaning이 현재 해결해야 할 핵심 과제

---

## 3. Limitations & Open Questions

### 현재 접근법의 한계

- **IPLFS (Episode 1)**: 8ZB 가상 partition으로 인해 storage device의 L2P mapping table이 tree 구조를 사용해야 하며, merge/split 연산의 오버헤드가 큼
- **D2FS (Episode 2)**: Legacy IO stack의 정보 흐름(host → device)을 역전시키므로, device-host 간 동기화 메커니즘이 필요하며, device가 file system의 free segment 상태를 알 수 없어 적시에 GC를 트리거하기 어려움
- **Zoned Storage (Episode 3)**: 1GB zone의 GC latency 문제는 아직 미해결

### 미해결 문제 및 향후 연구 방향

1. **Metadata scalability**: AI workload 증가에 따른 file system metadata 확장 문제
2. **GPU-SSD direct access**: GPU에서 SSD로의 직접 접근 경로 최적화
3. **Edge device IO 처리**: 모바일/edge 환경에서의 효율적 IO 관리
4. **HBF (High Bandwidth Flash)**: HBF와 HBM 칩을 동일 die에 탑재하여 unified memory space로 운용하는 새로운 아키텍처
   - Tiering vs. Caching 구성 방식 선택
   - HBF에 적합한 mapping unit 결정
5. **30년 이상 지속된 LFS의 GC 문제**: 발표자는 이제 LFS에서 GC를 제거할 수 있다고 조심스럽게 전망하며, 기존 하드웨어를 최대한 활용하기 위해 적절한 GC 정의와 file system 기술 배포가 필요하다고 강조

### 주요 시사점

- Computer systems 분야는 "아이디어를 떠올리기는 어렵지만, 구현은 쉬운" 특성이 있음 (자연과학/반도체와 반대)
- LFS의 GC 문제는 file system과 storage device 두 계층에 걸쳐 있으며, 이를 통합적으로 해결하는 cross-layer 접근이 핵심
- AI 시대의 새로운 workload 패턴 (sequential write + random read)은 flash storage에 적합하지만, zoned storage의 대용량 zone GC라는 새로운 도전을 제시함
