---
description: "Process meeting recording and generate notes (optionally to Notion)"
allowed-tools: Read, Write, Glob, Grep, Bash, Edit, WebSearch, WebFetch, mcp__claude_ai_Notion__notion-fetch, mcp__claude_ai_Notion__notion-update-page, mcp__claude_ai_Notion__notion-create-comment
---

# Process Meeting Command

You are processing a meeting recording. The arguments are: $ARGUMENTS

Expected format: `<date_title> [--notion <page_url>] [--profile <name>]`
Examples:
- `/process-meeting 2026-03-11_lab-standup`
- `/process-meeting 2026-03-11_lab-standup --notion https://notion.so/page-id`
- `/process-meeting 2026-03-11_lab-standup --profile lab-meeting`

## Environment

1. Read `config.yaml` at the project root to load settings.
2. Determine the profile:
   - If `--profile <name>` is specified, use that profile.
   - Otherwise, find a profile with `type: meeting` (default: `lab-meeting`).
3. All Bash commands MUST run inside the conda environment specified in `config.yaml`.

```
conda run -n <conda_env> --no-capture-output <command>
```

## Instructions

### Step 0: Parse Arguments & Validate

1. Parse `$ARGUMENTS` to extract:
   - `date_title`: the folder name (e.g., `2026-03-11_lab-standup`)
   - `--notion <url>`: optional Notion page URL
   - `--profile <name>`: optional profile name
2. Read `config.yaml` and extract profile settings
3. Check that `<data_dir>/<date_title>/` folder exists
4. Check for `transcript.md`. If missing, inform the user:
   > "transcript.md가 없습니다. 먼저 STT를 실행해주세요: `conda run -n <conda_env> python scripts/transcribe.py <date_title> --profile <profile>`"

### Step 1: Generate Meeting Summary

1. Read `<data_dir>/<date_title>/transcript.md`
2. Read the template from the profile's `template` field (default: `.claude/templates/meeting_template.md`)
3. Analyze the transcript and generate `<data_dir>/<date_title>/summary.md` with:

**Meeting notes must include:**

#### Attendees
- Identify speakers from the transcript (if distinguishable)
- List all mentioned participants

#### Agenda / Topics Discussed
- Identify distinct topics or agenda items from the conversation flow
- Summarize each topic with key points

#### Decisions Made
- List any decisions or conclusions reached during the meeting
- Note who made or supported each decision (if clear from transcript)

#### Action Items
- Extract concrete tasks, assignments, or follow-ups mentioned
- Format as a table: | Item | Owner | Deadline |

#### Key Discussion Points
- Important quotes or arguments (paraphrased)
- Disagreements or open questions raised

### Step 2: Save to Notion (if --notion provided)

If a Notion page URL was provided:

1. Use `mcp__claude_ai_Notion__notion-fetch` to read the current page content
2. Format the meeting summary as Notion-compatible content:
   - Use headings, bullet lists, and tables
   - Include a clear separator (---) if appending to existing content
3. Use `mcp__claude_ai_Notion__notion-update-page` to append the meeting notes to the page
   - Preserve existing page content
   - Add the new meeting notes below existing content
   - Add a header with the meeting date and title

If no Notion URL provided, inform the user:
> "summary.md가 생성되었습니다. Notion에 기록하려면 `--notion <url>` 옵션을 사용하세요."

### Language

- Detect the primary language from the transcript
- Write the summary in the same language
- Default to Korean if mixed

### Output

Save the summary to `<data_dir>/<date_title>/summary.md`

After completion, summarize:
- summary.md: number of topics, action items count
- Notion: whether notes were posted (and page title if so)
