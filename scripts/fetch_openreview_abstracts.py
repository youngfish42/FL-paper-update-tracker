#!/usr/bin/env python3
"""仅针对 ee 指向 openreview.net 的论文做 abstract 专项补全（OpenReview-only）。

与 scripts/fetch_abstracts.py 的区别：
- 本脚本只走 OpenReview v2 批量 API（命中率最高、最快、最稳），默认不调用
  Crossref/SS/arXiv/OpenAlex 兜底，适用于已知论文来源为 OpenReview 的批量回填场景。
- 仍然会自动抽取 related_code（GitHub 链接）并尝试 Chinese 翻译
  （若 DASHSCOPE_API_KEY 存在）。

用法:
    python scripts/fetch_openreview_abstracts.py              # 处理所有年份的空 abstract
    python scripts/fetch_openreview_abstracts.py --year 2025  # 只处理指定年份
    python scripts/fetch_openreview_abstracts.py --retry-failed  # 重试空 abstract
    python scripts/fetch_openreview_abstracts.py --enable-fallback  # 启用 v1/v2 单条兜底
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import yaml  # noqa: E402
from loguru import logger  # noqa: E402

from utils import (  # noqa: E402
    _prefill_openreview_abstracts,
    translate_abstracts_for_papers,
)

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


def run(year: str = "all", retry_failed: bool = False,
        enable_fallback: bool = False) -> None:
    project_root = Path(__file__).parent.parent.resolve()
    cache_path = project_root / "cached" / "dblp.yaml"
    backup_path = project_root / "cached" / "dblp.yaml.bak"

    # 单独写一份日志文件，避免 PowerShell 重定向丢失输出
    log_path = project_root / "_or_run.log"
    logger.remove()
    logger.add(sys.stdout, level="INFO",
               format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")
    logger.add(str(log_path), level="DEBUG", encoding="utf-8",
               format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")

    if enable_fallback:
        logger.info("Single-note fallback ENABLED (v1/v2 per-id queries).")

    dblp_cache = load_yaml(cache_path)
    if not dblp_cache:
        logger.error(f"Failed to load cache from {cache_path}")
        sys.exit(1)

    targets = []  # 直接传引用即可，_prefill_openreview_abstracts 会原地修改
    for topic, items in dblp_cache.items():
        if not isinstance(items, list):
            continue
        for item in items:
            ee = (item.get("ee") or "").strip()
            if "openreview.net" not in ee:
                continue
            paper_year = str(item.get("year", ""))
            if year != "all" and paper_year != str(year):
                continue
            abstract = (item.get("abstract") or "").strip()
            if abstract and not retry_failed:
                continue
            if retry_failed and abstract:
                # 显式重试模式：清空旧 abstract 以触发预填重写
                item["abstract"] = ""
            targets.append(item)

    logger.info(f"OpenReview-only backfill targets: {len(targets)} papers (year={year})")
    if not targets:
        logger.info("Nothing to fill. Exit.")
        return

    # 备份一次原始 cache（写回前）
    if cache_path.exists():
        shutil.copy2(cache_path, backup_path)

    # 阶段 1：OpenReview 批量预填 + related_code 抽取（在 _prefill 内已完成）
    try:
        filled, attempted = _prefill_openreview_abstracts(
            targets, min_interval=0.5, chunk=100, max_retries=3,
            enable_single_fallback=enable_fallback,
        )
        logger.info(f"Prefill result: filled {filled}/{attempted}")
    except Exception as e:
        logger.warning(f"Prefill aborted by exception: {e}")

    # 立即落盘一次（即便后续翻译失败也保住成果）
    save_yaml(cache_path, dblp_cache)
    logger.info(f"Cache checkpoint saved after prefill -> {cache_path}")

    # 阶段 2：中文翻译（若环境变量存在）
    api_key = os.getenv("DASHSCOPE_API_KEY", "")
    if api_key:
        try:
            translate_abstracts_for_papers(
                targets, api_key=api_key, sleep_sec=0.5, max_retries=3
            )
        except Exception as e:
            logger.warning(f"Translation aborted by exception: {e}")
    else:
        logger.warning("DASHSCOPE_API_KEY not set; skip Chinese translation.")

    # 最终落盘
    save_yaml(cache_path, dblp_cache)
    logger.info("Cache saved (final).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="OpenReview-only abstract backfill for cached/dblp.yaml"
    )
    parser.add_argument(
        "--year",
        type=str,
        default="all",
        help="Year to process (default: all, e.g. 2025)",
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Force re-fetch even for entries that already have a non-empty abstract",
    )
    parser.add_argument(
        "--enable-fallback",
        action="store_true",
        help="Enable v1/v2 single-note per-id fallback after batch (slower, may be rate-limited)",
    )
    args = parser.parse_args()
    run(year=args.year, retry_failed=args.retry_failed,
        enable_fallback=args.enable_fallback)
