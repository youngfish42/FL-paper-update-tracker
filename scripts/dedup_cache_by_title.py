#!/usr/bin/env python3
"""One-off script to deduplicate existing cached/dblp.yaml by title."""

import yaml
from pathlib import Path
from collections import defaultdict


def deduplicate_items_by_title(items):
    """根据 title 字段对论文列表进行去重，保留第一条记录"""
    seen_title = set()
    res = []
    dup_count = 0
    for item in items:
        title = item.get("title", "").strip()
        if title and title in seen_title:
            dup_count += 1
            continue
        if title:
            seen_title.add(title)
        res.append(item)
    return res, dup_count


def main():
    repo_root = Path(__file__).resolve().parent.parent
    cache_path = repo_root / "cached" / "dblp.yaml"

    with open(cache_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    total_before = 0
    total_after = 0
    total_dups = 0
    topic_dups = defaultdict(int)

    for topic, papers in data.items():
        if not isinstance(papers, list):
            continue
        before = len(papers)
        papers_deduped, dups = deduplicate_items_by_title(papers)
        after = len(papers_deduped)
        data[topic] = papers_deduped

        total_before += before
        total_after += after
        total_dups += dups
        if dups > 0:
            topic_dups[topic] = dups

    with open(cache_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, indent=2, allow_unicode=True)

    print(f"Total papers before dedup: {total_before}")
    print(f"Total papers after dedup:  {total_after}")
    print(f"Duplicate titles removed:  {total_dups}")
    if topic_dups:
        print("\nDuplicates by topic:")
        for topic, dups in sorted(topic_dups.items(), key=lambda x: -x[1]):
            print(f"  {topic}: {dups}")


if __name__ == "__main__":
    main()
