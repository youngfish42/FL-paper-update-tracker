#!/usr/bin/env python3
"""One-off script to globally deduplicate cached/dblp.yaml by ee and title.

Removes duplicate papers that appear under multiple topic keys, keeping the
first occurrence.
"""

import yaml
from pathlib import Path
from collections import defaultdict


def main():
    repo_root = Path(__file__).resolve().parent.parent
    cache_path = repo_root / "cached" / "dblp.yaml"

    with open(cache_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    seen_ee = set()
    seen_title = set()
    total_before = 0
    total_after = 0
    removed_by_topic = defaultdict(int)

    # Preserve topic order from the original file
    for topic in list(data.keys()):
        papers = data[topic]
        if not isinstance(papers, list):
            continue

        total_before += len(papers)
        cleaned = []
        for paper in papers:
            ee = paper.get("ee", "").strip()
            title = paper.get("title", "").strip()

            # Skip if ee already seen globally (and ee is not empty)
            if ee and ee in seen_ee:
                removed_by_topic[topic] += 1
                continue

            # Skip if title already seen globally (and title is not empty)
            if title and title in seen_title:
                removed_by_topic[topic] += 1
                continue

            if ee:
                seen_ee.add(ee)
            if title:
                seen_title.add(title)
            cleaned.append(paper)

        data[topic] = cleaned
        total_after += len(cleaned)

    with open(cache_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, indent=2, allow_unicode=True)

    print(f"Total papers before global dedup: {total_before}")
    print(f"Total papers after global dedup:  {total_after}")
    print(f"Removed duplicates: {total_before - total_after}")
    if removed_by_topic:
        print("\nRemoved by topic:")
        for topic, count in sorted(removed_by_topic.items(), key=lambda x: -x[1]):
            print(f"  {topic}: {count}")


if __name__ == "__main__":
    main()
