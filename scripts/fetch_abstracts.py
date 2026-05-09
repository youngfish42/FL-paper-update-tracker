#!/usr/bin/env python3
"""
为 cached/dblp.yaml 中的论文补充 abstract 字段。

用法:
    python scripts/fetch_abstracts.py              # 默认处理当前年度论文
    python scripts/fetch_abstracts.py --year all   # 处理所有年份
    python scripts/fetch_abstracts.py --retry-failed # 重试之前失败的条目（为空 abstract 重新获取）
"""

import argparse
import sys
import datetime
from pathlib import Path

# 将 src 加入路径以便导入 utils
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import fetch_abstract_for_papers, clean_abstract, translate_abstracts_for_papers
from loguru import logger
import yaml
import os

# 本地开发时从 .env 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def load_yaml(path: Path):
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_yaml(path: Path, data):
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, indent=2, allow_unicode=True)


def run(year: str = None, retry_failed: bool = False, clean_only: bool = False) -> None:
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

    if clean_only:
        logger.info("Starting abstract clean-only pass...")
        changed = 0
        total = 0
        for topic, items in dblp_cache.items():
            for item in items:
                raw = item.get("abstract")
                if not raw or not str(raw).strip():
                    continue
                total += 1
                cleaned = clean_abstract(raw)
                if cleaned != raw:
                    item["abstract"] = cleaned
                    changed += 1
        logger.info(f"Cleaned {changed}/{total} abstracts.")
        if changed > 0:
            if cache_path.exists():
                import shutil
                shutil.copy2(cache_path, backup_path)
            save_yaml(cache_path, dblp_cache)
            logger.info("Cache saved.")
        return

    logger.info(f"Starting abstract fetch. year={year}, retry_failed={retry_failed}")

    # 收集目标论文（增量）：
    # - 缺失 abstract 的论文需要获取摘要
    # - 缺失 abstract_cn 的论文需要翻译（前提是有 abstract）
    targets = []
    for topic, items in dblp_cache.items():
        for idx, item in enumerate(items):
            paper_year = str(item.get("year", ""))
            if year != "all" and paper_year != year:
                continue
            abstract = (item.get("abstract") or "").strip()
            abstract_cn = (item.get("abstract_cn") or "").strip()
            needs_abstract = (not abstract) or retry_failed
            needs_translation = False
            if not needs_abstract:
                needs_translation = not abstract_cn
            if not needs_abstract and not needs_translation:
                continue
            targets.append((topic, idx, item))

    logger.info(f"Total target papers to process: {len(targets)}")
    if not targets:
        logger.info("No papers need abstract. Exiting.")
        return

    # 提取纯论文 dict 列表供批量获取
    papers = [t[2] for t in targets]
    fetch_abstract_for_papers(papers, sleep_sec=2.0, max_retries=4, contact_email=contact_email)
    api_key = os.getenv("DASHSCOPE_API_KEY", "")
    translate_abstracts_for_papers(papers, api_key=api_key, sleep_sec=0.5, max_retries=3)

    # 写回缓存
    logger.info("Saving results...")
    if cache_path.exists():
        import shutil
        shutil.copy2(cache_path, backup_path)
    save_yaml(cache_path, dblp_cache)
    logger.info("Done.")


if __name__ == "__main__":
    default_year = str(datetime.datetime.now().year)
    parser = argparse.ArgumentParser(description="Fetch abstracts for papers in cached/dblp.yaml")
    parser.add_argument(
        "--year",
        type=str,
        default=default_year,
        help=f"Year to process (default: {default_year}, use 'all' for all years)",
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Retry previously failed entries (re-fetch for empty abstracts)",
    )
    parser.add_argument(
        "--clean-only",
        action="store_true",
        help="Only re-clean existing abstracts without fetching new ones",
    )
    args = parser.parse_args()
    run(year=args.year, retry_failed=args.retry_failed, clean_only=args.clean_only)
