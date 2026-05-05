# Technical Details

> Deployment, configuration, and workflow documentation for maintainers and developers.

## Table of Contents

- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Workflow](#workflow)
- [Project Structure](#project-structure)
- [Common Tasks](#common-tasks)

---

## Quick Start

### Prerequisites

- Python 3.8+
- pip

### Installation

```bash
git clone https://github.com/youngfish42/FL-paper-update-tracker.git
cd FL-paper-update-tracker
pip install -r requirements.txt
```

### Local Run

```bash
cd src
python main.py run --env=dev
```

In `dev` mode the script will:
- Load the cache from `cached/dblp.yaml`
- Query DBLP for all configured topics
- Print logs to stdout
- **Not** write to `GITHUB_ENV`

You can inspect `aggregated_msg` and `msg` in the logs to preview the issue content.

---

## Configuration

All behavior is controlled by `config.yaml` in the project root.

```yaml
dblp:
  url: https://dblp.org/search/publ/api?q={}&format=json&h=1000
  keyword: federate
  queries:
    - "venue:IJCAI:"
    - "venue:NeurIPS:"
    # ... add more queries here
  mails:
    - "im.young@foxmail.com"
```

### Fields

| Field | Description |
|-------|-------------|
| `dblp.url` | DBLP search API endpoint. `{}` is replaced by the fully-encoded topic query. `h=1000` requests up to 1000 hits. |
| `dblp.keyword` | The research-domain keyword (e.g. `federate`). This is the **only** field you need to change when switching to a different domain. |
| `dblp.queries` | List of plain-text DBLP venue restrictions. The runner automatically URL-encodes each query and prepends `keyword%20` before calling the API. |
| `dblp.mails` | Reserved for future mail-notification features. Currently unused. |

### Adding a New Venue

1. Find the DBLP venue code (e.g., `venue:ICML` or `streamid:journals/pami`).
2. Append the plain query string to `dblp.queries`. For example:
   - `venue:ICML:`
   - `streamid:journals/pami:`
3. Update `scripts/convert_cache_to_md.py` if you want the new venue to appear under a specific category in `FL-Papers.md`.
4. Update `README.md` (both English and Chinese sections) to list the new venue.

---

## Workflow

This repository uses [GitHub Actions](.github/workflows/watch.yml) to run the tracker automatically.

### Triggers

| Trigger | Description |
|---------|-------------|
| **Schedule** | Every day at 00:00 UTC+8 (`cron: 0 0 * * *`) |
| **Push** | On every push to the `main` branch |
| **Manual** | Via `workflow_dispatch` in the Actions tab |

### Execution Steps

1. **Checkout** – Clones the repository.
2. **Setup Python** – Installs Python 3.8.
3. **Install Dependencies** – Runs `pip install -r requirements.txt`.
4. **Run Tracker** – Executes `src/main.py` with `--env=prod`. It assembles each API query from `keyword` + `queries`, fetches results, filters by year, deduplicates by `ee` and by `title`, and updates `cached/dblp.yaml`.
5. **Update FL-Papers.md** – Runs `scripts/convert_cache_to_md.py` to regenerate the categorized Markdown paper list from the updated cache.
6. **Setup Var** – Escapes the generated Markdown message for GitHub Actions.
7. **Push Done Work** – Commits `cached/dblp.yaml` and `FL-Papers.md` back to the `main` branch.
8. **Create Issue** – If new papers were found, opens a GitHub Issue using `.github/issue-template.md`.

### Issue Format

The issue title follows this pattern:

```
Paper Update [Venue1, Venue2, ...] @ YYYY-MM-DD
```

The issue body contains:
- A summary header for each venue with new papers
- An unordered list of paper titles with `[PUB]` hyperlinks pointing to the DBLP `ee` field

---

## Project Structure

```
.
├── .github/
│   ├── workflows/
│   │   └── watch.yml          # GitHub Actions workflow
│   └── issue-template.md      # Issue template (Nunjucks)
├── cached/
│   └── dblp.yaml              # Persistent cache of reported papers
├── src/
│   ├── main.py                # Entry point and orchestration
│   └── utils.py               # API calls, parsing, formatting, dedup logic
├── config.yaml                # Venue list and settings
├── requirements.txt           # Python dependencies
├── README.md                  # User-facing documentation
├── TECHNICAL.md               # This file
└── AGENTS.md                  # Maintenance guide for agents
```

### Key Modules

- **`src/main.py`** – Loads cache, iterates over topics, queries DBLP, filters by year, deduplicates by `ee` and by `title`, compares against cache, and writes new papers to `GITHUB_ENV`.
- **`src/utils.py`** – Contains `get_dblp_items` (JSON parsing), `deduplicate_items_by_ee` / `deduplicate_items_by_title` (two-stage dedup logic), `filter_items_by_year` (year window filter), `get_msg` (Markdown formatting), and helpers for topic short-name extraction.
- **`cached/dblp.yaml`** – YAML mapping of topic → list of paper dicts. Serves as the source of truth for what has already been reported.

---

## Common Tasks

### Reset the Cache

If the cache becomes corrupted or you want to re-report all papers:

```bash
rm cached/dblp.yaml
```

The next run will treat every paper as new and recreate the cache.

### Change the Issue Schedule

Edit `.github/workflows/watch.yml`:

```yaml
schedule:
  - cron: '0 0 * * *'  # Change this cron expression
```

### Change the Message Format

Edit `src/utils.py` → `get_msg`. Keep the `aggregated` parameter behavior intact:
- `aggregated=True` → returns only the venue heading with `[+N]` count.
- `aggregated=False` → returns the heading plus the unordered paper list.

### Change the Year Window

Edit `src/utils.py` → `filter_items_by_year`:

```python
min_year = current_year - 3
max_year = current_year + 1
```

Adjust the offsets as needed.
