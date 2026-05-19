#!/usr/bin/env python3
"""
为 cached/dblp.yaml 中的论文补充 related_code 字段（从 abstract 中提取 GitHub 链接）。

用法:
    python scripts/fetch_related_code.py              # 默认处理当前年度论文
    python scripts/fetch_related_code.py --year all   # 处理所有年份
    python scripts/fetch_related_code.py --retry-failed # 重试之前失败的条目（为空 related_code 重新提取）
"""

import argparse
import sys
import datetime
from pathlib import Path

# 将 src 加入路径以便导入 utils
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import extract_github_links
from loguru import logger
import yaml


def load_yaml(path: Path):
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_yaml(path: Path, data):
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, indent=2, allow_unicode=True)


def run(year: str = None, retry_failed: bool = False) -> None:
    if year is None:
        year = str(datetime.datetime.now().year)

    project_root = Path(__file__).parent.parent.resolve()
    cache_path = project_root / "cached" / "dblp.yaml"
    backup_path = project_root / "cached" / "dblp.yaml.bak"

    dblp_cache = load_yaml(cache_path)
    if not dblp_cache:
        logger.error(f"Failed to load cache from {cache_path}")
        sys.exit(1)

    logger.info(f"Starting related_code extraction. year={year}, retry_failed={retry_failed}")

    targets = []
    for topic, items in dblp_cache.items():
        for idx, item in enumerate(items):
            paper_year = str(item.get("year", ""))
            if year != "all" and paper_year != year:
                continue
            abstract = (item.get("abstract") or "").strip()
            if not abstract:
                continue
            related_code = (item.get("related_code") or "").strip()
            # 默认情况下：若已有 related_code 字段（无论是否为空），则跳过
            if not retry_failed:
                if "related_code" in item:
                    continue
            # 重试失败时：仅处理 related_code 缺失或为空字符串的条目
            else:
                if "related_code" in item and related_code:
                    continue
            targets.append((topic, idx, item))

    logger.info(f"Total target papers to process: {len(targets)}")
    if not targets:
        logger.info("No papers need related_code extraction. Exiting.")
        return

    found = 0
    unchanged = 0
    for i, (topic, idx, item) in enumerate(targets, 1):
        title = (item.get("title") or "").strip()
        abstract = item["abstract"]
        logger.info(f"[{i}/{len(targets)}] Extracting: {title[:60]}...")
        new_code = extract_github_links(abstract)
        if new_code:
            item["related_code"] = new_code
            found += 1
            logger.info(f"  -> Found: {new_code}")
        else:
            item["related_code"] = ""
            unchanged += 1
            logger.info("  -> Not found")

    logger.info(f"Extraction done. Found: {found}, Not found: {unchanged}")

    # 写回缓存
    logger.info("Saving results...")
    if cache_path.exists():
        import shutil
        shutil.copy2(cache_path, backup_path)
    save_yaml(cache_path, dblp_cache)
    logger.info("Done.")


if __name__ == "__main__":
    default_year = str(datetime.datetime.now().year)
    parser = argparse.ArgumentParser(description="Extract GitHub links from abstracts in cached/dblp.yaml")
    parser.add_argument(
        "--year",
        type=str,
        default=default_year,
        help=f"Year to process (default: {default_year}, use 'all' for all years)",
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Retry previously failed entries (re-extract for empty related_code)",
    )
    args = parser.parse_args()
    run(year=args.year, retry_failed=args.retry_failed)
