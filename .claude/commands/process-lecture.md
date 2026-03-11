---
description: "Process lecture slides (PDF->MD) and generate report"
allowed-tools: Read, Write, Glob, Grep, Bash, Edit, WebSearch, WebFetch
---

# Process Lecture Command

You are processing a lecture recording. The date argument is: $ARGUMENTS

## Environment

1. Read `config.yaml` at the project root to load settings.
2. Determine the profile to use:
   - If `$ARGUMENTS` contains `--profile <name>`, use that profile.
   - Otherwise, find a profile with `type: lecture` (default: `cse-seminar`).
3. All Bash commands MUST run inside the conda environment specified in `config.yaml` (`default.conda_env`).

```
conda run -n <conda_env> --no-capture-output <command>
```

## Instructions

### Step 0: Validate

1. Read `config.yaml` and extract the profile settings (data_dir, template, etc.)
2. Check that `<data_dir>/$ARGUMENTS/` folder exists
3. Check for `transcript.md` in the folder. If missing, inform the user:
   > "transcript.md가 없습니다. 먼저 STT를 실행해주세요: `conda run -n <conda_env> python scripts/transcribe.py $ARGUMENTS --profile <profile>`"
4. Find PDF file(s) in `<data_dir>/$ARGUMENTS/`

### Step 1: PDF -> slides.md (with Web Research)

1. Read each PDF file in `<data_dir>/$ARGUMENTS/` using the Read tool
2. **Identify key topics** from the slides: paper titles, author names, technical terms, systems/tools mentioned
3. **Web research** using WebSearch and WebFetch to gather supplementary information:
   - Search for the **original papers** cited in the slides (e.g., paper title + author + venue) and add:
     - Full citation (authors, title, venue, year)
     - DOI or URL link when available
   - Search for **key technical concepts** mentioned in the slides and add:
     - Brief definitions or explanations not covered in the slides
     - Related work or context that helps understanding
   - Search for the **speaker's profile** and recent publications if relevant
   - Search for **follow-up work** or recent developments related to the topic
4. Convert the PDF content into a well-structured markdown file with:
   - Slide-by-slide sections (## Slide N: {title})
   - All text content preserved
   - Mathematical formulas in LaTeX notation ($..$ or $$..$$)
   - Tables preserved in markdown table format
   - Diagrams/figures described textually
   - Key concepts and definitions highlighted in **bold**
   - Code snippets in proper code blocks
   - **> Note:** blocks for supplementary information found via web research
   - **References section** at the end with full citations and links
5. Save as `<data_dir>/$ARGUMENTS/slides.md`

**Web Research Guidelines:**
- Focus on the **3-5 most important topics** from the slides, not every minor term
- Prioritize academic sources (ACM DL, IEEE Xplore, arXiv, USENIX) over general web pages
- Add supplementary info as blockquotes (`> Note:`) to clearly distinguish from original slide content
- If a search yields no useful results, skip it and move on

### Step 2: Generate Report

1. Read `<data_dir>/$ARGUMENTS/transcript.md` (STT result)
2. Read `<data_dir>/$ARGUMENTS/slides.md` (just created)
3. Read the template file specified in the profile's `template` field
4. Generate `<data_dir>/$ARGUMENTS/report.md` following the template structure

**Report must compose these 3 sections:**

#### 1. Research Motivation & Problem
Based on both the slides and transcript:
- What is the research background and motivation?
- What core problem is being addressed?
- What are the limitations of existing approaches?

#### 2. Methodology & Contributions
Based on both the slides and transcript:
- What methodology/technique is proposed?
- What are the key contributions (theoretical and practical)?
- Summarize experimental design and results
- How does this improve upon existing methods?

#### 3. Limitations & Open Questions
Based on both the slides and transcript:
- What are the limitations of the current approach?
- What open problems remain?
- What future research directions are suggested?
- Include notable points from Q&A if present in the transcript

### Language

- Detect the primary language from the slides and transcript
- Write the report in the same language as the lecture materials
- If mixed language, default to the language used more in the slides

### Output

Save the report to `<data_dir>/$ARGUMENTS/report.md`

After completion, summarize what was generated:
- slides.md: number of slides processed
- report.md: brief overview of each section
