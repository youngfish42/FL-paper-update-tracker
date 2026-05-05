# Agent Guidance for FL-paper-update-tracker

> This file is intended for automated coding agents (and human maintainers) who need to understand, modify, or extend the project. Keep it up-to-date whenever architecture, logic, or conventions change.

## Project Overview

**FL-paper-update-tracker** is an automated bot that tracks new Federated Learning (FL) papers published in 40+ top-tier computer-science conferences and journals. It is a satellite project of [Awesome-FL](https://github.com/youngfish42/Awesome-FL).

### High-Level Workflow
1. GitHub Actions runs the tracker once per day (cron: `0 0 * * *`) and on every push to `main`.
2. `src/main.py` reads `config.yaml` → takes `dblp.keyword` (e.g. `federate`) and `dblp.queries` (plain venue restrictions), assembles fully URL-encoded DBLP search topics, and queries the DBLP search API.
3. Extracted paper metadata is **filtered by year** (last 3 years + next 1 year) and **deduplicated by `ee` field**.
4. New papers (not yet in `cached/dblp.yaml`) are collected, formatted as Markdown, and written to the `GITHUB_ENV` variable `MSG`.
5. `scripts/convert_cache_to_md.py` regenerates `FL-Papers.md` from the updated cache.
6. If new papers exist, the action `JasonEtco/create-an-issue@v2` creates a GitHub Issue using `.github/issue-template.md`.
7. Both `cached/dblp.yaml` and `FL-Papers.md` are committed back to the repo so that subsequent runs know what has already been reported.

## Tech Stack

- **Language**: Python 3.8+
- **Core Dependencies** (see `requirements.txt`):
  - `fire` – CLI scaffolding
  - `requests` – HTTP calls to DBLP API
  - `loguru` – structured logging
  - `ezkfg` – lightweight config loader
  - `pyyaml` – cache read/write
- **CI/CD**: GitHub Actions (Ubuntu runner)
- **License**: Apache 2.0

## Directory Structure

```
.
├── .github/
│   ├── workflows/watch.yml          # GitHub Actions workflow definition
│   └── issue-template.md            # Nunjucks template for auto-created issues
├── cached/
│   └── dblp.yaml                    # Persistent cache of already-reported papers
├── scripts/
│   └── convert_cache_to_md.py       # Converts cache to structured Markdown (domain-specific maps)
├── src/
│   ├── main.py                      # Entry point: assembles topics from keyword+queries, orchestrates API calls
│   └── utils.py                     # Helper functions: API call, parsing, formatting, dedup
├── config.yaml                      # keyword, plain queries (venues), and mail targets
├── FL-Papers.md                     # Structured Markdown output of all tracked papers
├── requirements.txt                 # Python dependencies
├── README.md                        # Human-facing documentation (EN + CN)
├── TECHNICAL.md                     # Deployment and configuration guide
└── AGENTS.md                        # This file
```

## Key Logic & Conventions

### 1. Year Filtering
- Location: `src/main.py` (calls `filter_items_by_year` in `src/utils.py`)
- Rule: Only papers whose `year` falls in `[current_year - 3, current_year + 1]` are kept.
- Example: In 2026, valid years are 2023–2027.
- **Agent Note**: If you change this window, update both the implementation **and** this document.

### 2. Deduplication
- Location: `src/utils.py` (`deduplicate_items_by_ee`)
- Rule: Two papers are considered the same if their `ee` (electronic edition URL) strings match exactly.
- Rationale: DBLP sometimes returns multiple records for the same paper with minor author-name differences (e.g., `Ming Hu 0003` vs `Ming Hu`). The `ee` field is stable and unique.
- **Agent Note**: Do **not** switch back to full-dict comparison (`item not in cached_items`) unless you also normalize author names.

### 3. Cache Format (`cached/dblp.yaml`)
- Top-level keys: URL-encoded DBLP search topics (e.g., `federate%20venue%3ADAC%3A:`).
- Each key maps to a list of paper dicts with fields: `author`, `title`, `venue`, `year`, `type`, `access`, `key`, `doi`, `ee`, `url`.
- The file is overwritten after every successful run.
- **Agent Note**: If you add new fields to the paper dict, ensure backward compatibility; old cache entries missing the new field should be handled gracefully.

### 4. Message Formatting (`get_msg`)
- Location: `src/utils.py`
- `aggregated=True`: Returns only the topic heading with a `[+N]` count. Used to build the summary portion of the issue body.
- `aggregated=False`: Returns the topic heading **plus** an unordered list of papers in the form:
  ```markdown
  - {title}. [PUB]({ee})
  ```
- `get_topic_short_name` extracts the venue short name (the segment after the last `/`, or the whole name if no `/`) from a topic URL. Used for the Issue title.
- `format_title_topics` joins short names with `, ` and truncates to ≤80 characters, appending `等N个` when truncated.

### 5. Issue Title Construction
- Template: `.github/issue-template.md`
- Title: `Paper Update [{{ env.ISSUE_TITLE_TOPICS }}] @ {{ date | date('YYYY-MM-DD') }}`
- The environment variable `ISSUE_TITLE_TOPICS` is populated in `src/main.py` and passed through the workflow `env` block.

### 6. Configuration (`config.yaml`)
```yaml
dblp:
  url: https://dblp.org/search/publ/api?q={}&format=json&h=1000
  topics:
    - "federate%20venue%3AIJCAI%3A"
    - ...
  mails:
    - "im.young@foxmail.com"
```
- `topics`: Each topic is a URL-encoded DBLP search query. The first word (`federate`) is the keyword; the rest restricts the venue.
- `mails`: Currently reserved; not actively used in the code but kept for future mail-notification features.
- **Agent Note**: When adding a new venue, find its DBLP query syntax (venue code or stream ID) and URL-encode it.

## Maintenance Notes

### Adding a New Venue
1. Find the DBLP venue code (e.g., `venue:ICML` or `streamid:journals/pami`).
2. Append the **plain** query string to `config.yaml` under `dblp.queries` (e.g., `venue:ICML:`). The runner handles URL encoding automatically.
3. Update `scripts/convert_cache_to_md.py` if you want the new venue mapped to a specific category in `FL-Papers.md`.
4. Update `README.md` (both EN and CN sections) to list the new venue.
5. Update this `AGENTS.md` if the change affects architecture or conventions.

### Switching to a Different Research Domain
The tracker is domain-agnostic. To pivot from Federated Learning to any other field (e.g., diffusion models, LLMs, reinforcement learning):

1. **Change the keyword** in `config.yaml`:
   ```yaml
   dblp:
     keyword: diffusion   # or LLM, "reinforcement learning", etc.
   ```
2. **Adjust the venue list** under `dblp.queries` to match the venues relevant to the new domain.
3. **Update `scripts/convert_cache_to_md.py`**:
   - `VENUE_MAP` — map DBLP raw venue names to your preferred display names.
   - `CATEGORY_MAP` — assign each display name to a category.
   - `CATEGORY_ORDER` and `VENUE_ORDER` — control the output ordering.
4. **Reset the cache** by deleting or renaming `cached/dblp.yaml` so the next run treats all fetched papers as new.
5. (Optional) Update `README.md` and `TECHNICAL.md` to reflect the new domain.

No changes to `src/main.py` or the GitHub Actions workflow are required.

### Changing Message Format
- Edit `src/utils.py` → `get_msg`.
- If you modify the Markdown structure, verify that the issue template renders correctly in GitHub.
- Keep the `aggregated` parameter behavior: `True` = heading only, `False` = heading + list.

### Changing Issue Template
- Edit `.github/issue-template.md`.
- The template engine is Nunjucks (via `JasonEtco/create-an-issue@v2`). Available variables:
  - `{{ date }}`
  - `{{ env.MSG }}`
  - `{{ env.ISSUE_TITLE_TOPICS }}`
- If you introduce a new `env` variable, also update `.github/workflows/watch.yml` to pass it through.

### Changing Workflow Schedule
- Edit `.github/workflows/watch.yml` → `schedule.cron`.
- Default is daily at 00:00 UTC+8 (`0 0 * * *`).

### Cache Corruption / Manual Reset
- Simply delete `cached/dblp.yaml` (or remove specific topic keys).
- The next run will treat all papers as "new" and recreate the cache.

## Testing Locally

```bash
cd src
python main.py run --env=dev
```

In `dev` mode the script will:
- Load the cache
- Query DBLP
- Print logs to stdout
- **Not** write to `GITHUB_ENV`

You can inspect `aggregated_msg` and `msg` in the logs to preview the issue content.

## Common Pitfalls

1. **Rate Limiting**: DBLP does not publish explicit rate limits, but the code already sleeps `5 + random(0,3)` seconds between requests. Do not remove this.
2. **YAML Encoding**: `cached/dblp.yaml` is written with `allow_unicode=True`. Editing it manually with an editor that strips Unicode may corrupt author names.
3. **Empty `ee` Field**: Some older DBLP entries lack an `ee`. The deduplication logic skips empty `ee` values, so those papers are always retained. This is intentional to avoid data loss.
4. **Topic String Parsing**: `get_topic_short_name` relies on `split(":")[-2]` followed by `split("/")[-1]`. If DBLP changes its topic URL format, this will break.

## Contact & References

- Parent project: [Awesome-FL](https://github.com/youngfish42/Awesome-FL)
- Upstream inspiration: [dblp-watcher](https://github.com/beiyuouo/dblp-watcher/)
- DBLP API docs: https://dblp.org/faq/How+to+use+the+dblp+search+API.html
