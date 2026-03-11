# Scribbr

녹음 및 자료를 정리하여 리포트/회의록을 생성하는 파이프라인.
수업 강의와 미팅 녹음 모두 지원하며, 미팅의 경우 Notion 연동이 가능합니다.

## Project Structure

```
Scribbr/
├── config.yaml                    # 프로젝트 설정 (프로필, 모델, 경로)
├── README.md
├── requirements.txt
├── scripts/
│   └── transcribe.py              # STT (mlx-whisper)
├── data/
│   ├── lectures/                  # 수업 데이터
│   │   └── {YYYY-MM-DD}/
│   │       ├── *.m4a              # 녹음 (입력)
│   │       ├── *.pdf              # 교안 (입력)
│   │       ├── transcript.md      # STT 결과
│   │       ├── slides.md          # 교안 정리
│   │       └── report.md          # 최종 리포트
│   └── meetings/                  # 미팅 데이터
│       └── {YYYY-MM-DD}_{title}/
│           ├── *.m4a              # 녹음 (입력)
│           ├── transcript.md      # STT 결과
│           └── summary.md         # 회의록
└── .claude/
    ├── commands/
    │   ├── process-lecture.md     # 수업 처리 커맨드
    │   └── process-meeting.md    # 미팅 처리 커맨드
    ├── knowledge/
    │   └── Schedule.pdf           # 세미나 일정표
    └── templates/
        ├── report_template.md     # 수업 리포트 템플릿
        └── meeting_template.md    # 미팅 회의록 템플릿
```

## Prerequisites

- Python 3.11+
- [ffmpeg](https://ffmpeg.org/) (`brew install ffmpeg`)
- Apple Silicon Mac (mlx-whisper 필수)
- [Conda](https://docs.conda.io/)

```bash
conda create -n cse python=3.11
conda activate cse
pip install -r requirements.txt
```

## Configuration

`config.yaml`에서 프로필별 설정을 관리합니다:

```yaml
default:
  stt_model: "mlx-community/whisper-large-v3-mlx"
  chunk_duration: 300
  conda_env: "cse"

profiles:
  cse-seminar:
    type: lecture
    name: "CSE Graduate Seminar (ESW5060)"
    data_dir: "data/lectures"
    schedule: ".claude/knowledge/Schedule.pdf"
    template: ".claude/templates/report_template.md"

  lab-meeting:
    type: meeting
    name: "Lab Weekly Meeting"
    data_dir: "data/meetings"
    template: ".claude/templates/meeting_template.md"
    notion_page: ""
```

새로운 수업이나 미팅을 추가하려면 `profiles` 섹션에 새 프로필을 추가하세요.

## Usage

### Lecture (수업)

#### 1. 파일 배치

`data/lectures/{YYYY-MM-DD}/` 폴더에 녹음 파일(m4a)과 교안(PDF)을 넣는다.

#### 2. STT 실행

```bash
conda run -n cse python scripts/transcribe.py 2026-03-04 --profile cse-seminar
```

| Option | Default | Description |
|--------|---------|-------------|
| `--profile` | - | config.yaml 프로필명 |
| `--model` | config의 `stt_model` | HuggingFace 모델 ID (오버라이드) |
| `--output` | `transcript.md` | 출력 파일명 |
| `--config` | `config.yaml` | 설정 파일 경로 |

#### 3. PDF 정리 + Report 생성 (Claude Code)

```
/process-lecture 2026-03-04
```

수행 내용:
1. 교안 PDF를 `slides.md`로 변환 (웹 검색으로 논문 인용/개념 보충)
2. `transcript.md` + `slides.md`를 기반으로 `report.md` 생성

#### Report 구조

| Section | Content |
|---------|---------|
| Research Motivation & Problem | 연구 배경, 핵심 문제, 기존 접근법의 한계 |
| Methodology & Contributions | 제안 방법론, 핵심 기여점, 실험 결과 |
| Limitations & Open Questions | 한계, 미해결 문제, 향후 연구 방향 |

### Meeting (미팅)

#### 1. 파일 배치

`data/meetings/{YYYY-MM-DD}_{title}/` 폴더에 녹음 파일을 넣는다.

```
data/meetings/2026-03-11_lab-standup/
└── recording.m4a
```

#### 2. STT 실행

```bash
conda run -n cse python scripts/transcribe.py 2026-03-11_lab-standup --profile lab-meeting
```

#### 3. 회의록 생성 (Claude Code)

```
/process-meeting 2026-03-11_lab-standup
```

Notion에 기록하려면:
```
/process-meeting 2026-03-11_lab-standup --notion https://notion.so/your-page-id
```

수행 내용:
1. `transcript.md` 기반으로 `summary.md` 생성 (참석자, 안건, 액션아이템 등)
2. `--notion` 옵션 시 해당 Notion 페이지에 회의록 추가

## Tech Stack

| Component | Tool |
|-----------|------|
| STT | [mlx-whisper](https://github.com/ml-explore/mlx-examples) + whisper-large-v3 |
| Audio conversion | ffmpeg |
| PDF/Report | Claude Code |
| Meeting notes | Claude Code + Notion MCP |
| Configuration | YAML |
