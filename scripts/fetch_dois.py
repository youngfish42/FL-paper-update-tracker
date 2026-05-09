#!/usr/bin/env python3
"""
为 cached/dblp.yaml 中缺失 DOI 的论文补充 doi 字段。

用法:
    python scripts/fetch_dois.py              # 默认处理当前年度论文
    python scripts/fetch_dois.py --year all   # 处理所有年份
    python scripts/fetch_dois.py --retry-all  # 对所有论文重新获取 DOI（包括已有 DOI 的）
"""

import argparse
import sys
import datetime
from pathlib import Path

# 将 src 加入路径以便导入 utils
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import fetch_doi_for_papers
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


def run(year: str = None, retry_all: bool = False) -> None:
    if year is None:
        year = str(datetime.datetime.now().year)

    project_root = Path(__file__).parent.parent.resolve()
    cache_path = project_root / "cached" / "dblp.yaml"
    backup_path = project_root / "cached" / "dblp.yaml.bak"

    # 读取 config.yaml 获取 contact_email
    config_path = project_root / "config.yaml"
    contact_email = ""
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            mails = config.get("dblp", {}).get("mails", [])
            contact_email = mails[0] if mails else ""
        except Exception as e:
            logger.warning(f"Failed to load contact_email from config.yaml: {e}")

    dblp_cache = load_yaml(cache_path)
    if not dblp_cache:
        logger.error(f"Failed to load cache from {cache_path}")
        sys.exit(1)

    logger.info(f"Starting DOI backfill. year={year}, retry_all={retry_all}")

    # 收集目标论文
    targets = []
    for topic, items in dblp_cache.items():
        for idx, item in enumerate(items):
            paper_year = str(item.get("year", ""))
            if year != "all" and paper_year != year:
                continue
            existing_doi = (item.get("doi") or "").strip()
            if existing_doi and not retry_all:
                continue
            targets.append((topic, idx, item))

    logger.info(f"Total target papers to process: {len(targets)}")
    if not targets:
        logger.info("No papers need DOI backfill. Exiting.")
        return

    # 提取纯论文 dict 列表供批量获取
    papers = [t[2] for t in targets]
    fetch_doi_for_papers(
        papers,
        sleep_sec=2.0,
        max_retries=4,
        contact_email=contact_email,
        overwrite=retry_all,
    )

    # 写回缓存
    logger.info("Saving results...")
    if cache_path.exists():
        import shutil
        shutil.copy2(cache_path, backup_path)
    save_yaml(cache_path, dblp_cache)
    logger.info("Done.")


if __name__ == "__main__":
    default_year = str(datetime.datetime.now().year)
    parser = argparse.ArgumentParser(description="Fetch DOIs for papers in cached/dblp.yaml")
    parser.add_argument(
        "--year",
        type=str,
        default=default_year,
        help=f"Year to process (default: {default_year}, use 'all' for all years)",
    )
    parser.add_argument(
        "--retry-all",
        action="store_true",
        help="Retry all papers, including those that already have a DOI",
    )
    args = parser.parse_args()
    run(year=args.year, retry_all=args.retry_all)
