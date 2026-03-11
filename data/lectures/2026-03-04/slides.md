# Log-Structured Filesystem in the Era of AI

**Speaker**: Professor Youjip Won | **Affiliation**: KAIST | **Date**: Mar 4 (Wed), 2026
**Time**: 16:00 - 17:00 | **Location**: Chemistry Bldg, Room 330118

---

## Slide 1: Title & Speaker Introduction

- **Title**: Log-Structured Filesystem in the Era of AI
- **Speaker**: Professor Youjip Won, KAIST
- ICT Endowed Chair Professor, School of Electrical Engineering, KAIST
- Former department head and director of Center for File and Storage Systems Technology (CFSR) at Hanyang University
- Moved to KAIST after 20 years at Hanyang University
- **Awards**:
  - USENIX ATC 2013 Best Paper Award (IO stack optimization in Android platform)
  - USENIX FAST 2018 Best Paper Award (IO stack design on Flash Storage)
- **Research Interests**: Operating Systems, Distributed Systems, Storage Systems, Software support for byte-addressable NVRAM
- Served as president of Korean Institute of Information and Science
- General Chair of SOSP; Program Chair of USENIX ATC 2023

---

## Slide 2: Abstract / Talk Overview

In this talk, we will review how the **log-structured filesystem** evolves in the era of AI. Log-structured filesystem is a write-optimized filesystem that has primarily been proposed to efficiently handle the random write workload from the application. It clusters the metadata and data together and transforms the random writes into a sequential one. Despite its benefits, it had not been well adopted in the production environment. The prime reason is that the log-structured filesystem needs to **consolidate the valid blocks and reclaims the invalidated filesystem regions** -- this activity is called **garbage collection**. During garbage collection, the filesystem blocks all foreground write requests.

For the past years, we developed a number of techniques that mitigate or eliminate the garbage collection overhead from the host. We will mainly deal with two issues:
1. Ways to **mitigate the filesystem garbage collection overhead** from the host
2. **Performance limitations** which the modern log-structured filesystem faces

---

## Slide 3: Computer System Architecture (IO Stack)

- **Application Layer**: IoT, AI, Mobile, Autonomous Car
- **Data Layer**: RocksDB, MongoDB, Spark
- **OS Kernel / File System**: EXT4, XFS, F2FS
- **Block Layer**
- **Flash Memory-based Storage Systems**

Another view:
- CPU Cores (top)
- File System + **Page Cache** (middle)
- Block Device + Storage (bottom)

**Page Cache**: temporarily caches contents from storage
- **Read path**: Storage -> Page Cache -> Application
- **Write path**: Application -> Page Cache -> (flush) -> Storage

---

## Slide 4: Log-Structured File System (LFS) Basics

- Invented by **Rosenblum & Ousterhout**, published in **SOSP 1991**
- Rosenblum is co-founder of **VMware**
- **Write-optimized** file system: treats the entire partition as a single **log**

**Core Mechanism**:
- Instead of **overwriting** blocks in-place, LFS **appends** new versions at the end
- Old versions are **invalidated**
- **Random writes** are transformed into **sequential writes** (append-only)

**Example**:
| Operation | Action |
|-----------|--------|
| Write D (new) | Append D |
| Update A -> A' | Invalidate A, Append A' |
| Write E (new) | Append E |
| Update B -> B' | Invalidate B, Append B' |

**Benefits**: Sequential write is significantly faster than random write

---

## Slide 5: LFS Adoption History

- Debuted at **SOSP 1991**
- First deployed in real production system in **2018** (F2FS on Android)
- **~27 years** until real-world adoption
- **Reason for slow adoption**: Garbage Collection overhead

---

## Slide 6: Garbage Collection (GC) Problem

**Why GC is needed**:
- As LFS keeps appending, free blocks eventually run out
- Invalid blocks must be reclaimed to make room for new writes

**GC Process**:
1. Select a **victim segment**
2. Read valid blocks from victim segment
3. Copy valid blocks to a new segment
4. Free the victim segment

**GC Impact**:
- **Unpredictable performance** -- nightmare for system administrators
- **Tail latency** becomes uncontrollable

---

## Slide 7: Dual Garbage Collection Problem

- **Flash storage** also performs its own GC internally (append-only nature of flash)
- Running LFS on top of flash storage = **dual GC effort**
  - File system GC (F2FS level)
  - Device GC (Flash Translation Layer)
- **Android smartphones** (Galaxy) use F2FS + flash storage = both GCs active

**Experiment Result**:
- File system GC (blue line) is **far more detrimental** to application performance than device GC (red line)
- Priority: Eliminate **file system GC** first

---

## Slide 8: Episode 1 - IPLFS (Infinite Partition LFS, 2022)

**Key Insight**: File system runs GC because **partition size is limited**

**Idea**: Make the file system partition **virtually infinite**
- Analogous to **virtual memory**: physical DRAM is limited, but virtual address space is huge
- Separate file system partition size from physical storage capacity
- Use **64-bit LBA addressing** -> $2^{64}$ sectors = **8 Zettabytes** (virtually infinite)

**Mechanism**:
- Active region of valid blocks migrates forward in LBA space
- Invalid blocks are left behind -- no need to reclaim them
- GC is **entirely eliminated** from the file system

**Metadata Optimization**:
- Block bitmap and reverse map are only needed for GC
- If GC is removed, these metadata structures are unnecessary
- Use **interval mapping** (tree-based) instead of flat table for 8ZB partition

**Result**: Performance degradation reduced to only **~40%** variance (much more stable)

---

## Slide 9: Episode 2 - D2FS (Device-Driven File System GC, 2025)

**Different Approach**: Instead of eliminating GC, let the **storage device** perform file system GC

**IO Stack Mapping**:
- **F2L mapping** (host): File (inode + offset) -> LBA
- **L2P mapping** (device): LBA -> Physical Page Address (PPA)

**Mechanism**:
1. Device performs its own GC (migrates flash pages, updates PPA)
2. Device **also** consolidates logical blocks (updates LBA mapping)
3. Updated mapping is **synchronized to the host** (migration upcall)
4. Host updates F2L mapping based on device-supplied information

**Three Key Techniques**:
1. **Coupled Garbage Collection**: Couples device GC and file system GC into a single operation
2. **Migration Upcall**: Delivers updated F2L mapping from device to host
3. **Virtual Overprovisioning**: Extends file system partition to prevent running out of free segments

**Challenges Addressed**:
- Device must update F2L mapping without interfering with host file system activity
- Information flow reversal (device -> host, vs. legacy host -> device)
- Device must trigger GC on time before file system runs out of free segments

**Result**: Stock F2FS performance **crashes** during GC; D2FS maintains **steady performance** with no visible GC overhead

**Advantage over Episode 1 (IPLFS)**:
- IPLFS requires device to handle 8ZB logical partition (expensive tree-based L2P mapping)
- D2FS only needs partition ~**1.2x** larger than storage capacity

---

## Slide 10: Episode 3 - AI Workload & Zoned Storage

**AI Workload IO Pattern**:
- **KV Cache** management for LLM inference
- New query -> existing KV Cache spilled to flash (**sequential write**)
- Inference at edge -> load from KV Cache (**random read**)
- Perfect fit for flash: good at sequential write + fast random read

**Edge Device Constraints**:
- Very small **SRAM** in mobile storage devices
- Cannot use page mapping or block mapping
- Natural choice: **Zone mapping** (larger unit)
- Google pushing for **Zoned UFS** for mobile devices

**IO Pattern Analysis** (A100 GPU + NVMe, LLaMA 6.7B):
- Write: sequential
- Read: appears sequential at macro level, but **random at micro level**

**New Problem**:
- Zoned SSD zone size = **1 GB**
- GC latency for 1 GB zone is **extremely long** compared to 2 MB segment
- Challenge: How to efficiently clean 1 GB file system region per GC run

---

## Slide 11: Future Research Directions

- **Metadata scalability** for AI workloads
- **GPU-SSD direct access**
- IO handling at **edge devices**
- **HBF (High Bandwidth Flash)**: new research opportunity
  - HBF chip + HBM chip on the **same die**
  - Unified memory address space
  - Caching vs. Tiering organization
  - Correct mapping unit for HBF

---

## Slide 12: Conclusion

1. Log-structured file system has suffered from **garbage collection for over 30 years**
2. We can now carefully believe that **GC can be removed** from LFS
3. To maximize hardware utilization, proper **GC definition and deployment** of file system technology is essential
4. New challenges emerge from **AI workloads** and **zoned storage**
