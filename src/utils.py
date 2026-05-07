import sys
import os
import yaml
from loguru import logger
from pathlib import Path
import ezkfg as ez
import urllib.parse
import requests
import json
import time
import random
import re
import difflib


def init_log():
    """Initialize loguru log information"""
    event_logger_format = (
        "<g>{time:YYYY-MM-DD HH:mm:ss}</g> | "
        "<lvl>{level}</lvl> - "
        # "<c><u>{name}</u></c> | "
        "{message}"
    )
    logger.remove()
    logger.add(
        sink=sys.stdout,
        colorize=True,
        level="DEBUG",
        format=event_logger_format,
        diagnose=False,
    )

    return logger


def init_path(cfg):
    cfg["cache_path"] = Path("./../cached")
    cfg["cache_path"].mkdir(parents=True, exist_ok=True)

    return cfg


def init(cfg_path: str):
    cfg = ez.Config().load(cfg_path)
    cfg = init_path(cfg)
    init_log()
    return cfg


def get_item_info(item, key):
    try:
        return item[key]
    except KeyError:
        return ""


def filter_items_by_year(items, current_year):
    """按年份过滤论文列表，只保留近三年及未来一年的数据"""
    min_year = current_year - 3
    max_year = current_year + 1
    filtered = []
    for item in items:
        year_str = item.get("year", "")
        if not year_str:
            continue
        try:
            year = int(year_str)
        except ValueError:
            continue
        # 仅保留在 [current_year-3, current_year+1] 范围内的论文
        if min_year <= year <= max_year:
            filtered.append(item)
    return filtered


def deduplicate_items_by_ee(items):
    """根据 ee 字段对论文列表进行去重，保留第一条记录"""
    seen_ee = set()
    res = []
    for item in items:
        ee = item.get("ee", "")
        # 若 ee 存在且已出现过，则跳过该条记录（视为重复论文）
        if ee and ee in seen_ee:
            continue
        if ee:
            seen_ee.add(ee)
        res.append(item)
    return res


def deduplicate_items_by_title(items):
    """根据 title 字段对论文列表进行去重，保留第一条记录"""
    seen_title = set()
    res = []
    for item in items:
        title = item.get("title", "").strip()
        # 若 title 存在且已出现过，则跳过该条记录（视为重复论文）
        if title and title in seen_title:
            continue
        if title:
            seen_title.add(title)
        res.append(item)
    return res


def get_dblp_items(dblp_data):
    try:
        items = dblp_data["result"]["hits"]["hit"]
    except KeyError:
        items = []

    # item{'author', 'title', 'venue', 'year', 'type', 'access', 'key', 'doi', 'ee', 'url'}
    res_items = []

    for item in items:
        res_item = {}
        # format author
        authors = get_item_info(item["info"], "authors")
        try:
            authors = [author["text"] for author in authors["author"]]
        except TypeError:
            if "author" not in authors:
                continue
            if "text" not in authors["author"]:
                continue

            authors = [authors["author"]["text"]]

        # logger.info(f"authors: {authors}")

        res_item["author"] = ", ".join(authors)
        needed_keys = [
            "title",
            "venue",
            "year",
            "type",
            "access",
            "key",
            "doi",
            "ee",
            "url",
            "abstract",
        ]
        for key in needed_keys:
            key_temp = get_item_info(item["info"], key)
            res_item[key] = key_temp if key_temp else ""

        res_items.append(res_item)

    return res_items


def get_topic_short_name(topic):
    """提取 topic 的简称，取 '/' 分隔后的最后一段"""
    string_topic = urllib.parse.unquote(topic)
    name_topic = string_topic.split(":")[-2]
    return name_topic.split("/")[-1]


def format_title_topics(topics, max_len=80):
    """将 topic 列表格式化为标题字符串，超长时自动截断为 'a, b, c 等N个'"""
    if not topics:
        return ""
    full = ", ".join(topics)
    if len(full) <= max_len:
        return full
    # 从后往前尝试去掉一些 topic，确保加上"等N个"后不超长度
    for i in range(len(topics) - 1, 0, -1):
        prefix = ", ".join(topics[:i])
        suffix = f"等{len(topics) - i}个"
        candidate = f"{prefix} {suffix}"
        if len(candidate) <= max_len:
            return candidate
    # 如果连第一个 topic + 等N个 都太长
    return f"{topics[0]} 等{len(topics) - 1}个"


def get_msg(items, topic, aggregated=False):
    # 将 URL 编码的 topic 转回可读字符串
    string_topic = urllib.parse.unquote(topic)
    # 提取 topic 名称（取倒数第二个冒号分隔的部分）
    name_topic = string_topic.split(":")[-2]

    # 输出 topic 名称及新增条目数，如 "TopicName [+5]"
    msg = f"## [{name_topic}](https://dblp.org/search?q={topic}) [+{len(items)}]\\n\\n"

    # 仅在非聚合模式下输出无序列表详情
    if aggregated == False:
        for item in items:
            ee = item.get("ee", "")
            if ee:
                # 格式：- title. [PUB](ee超链接)
                msg += f"- {item['title']}. [[PUB]({ee})]\\n"
            else:
                msg += f"- {item['title']}.\\n"
        msg += "\\n"

    msg = msg.replace("'", "")
    return msg

def request_data(url, retry=10, sleep_time=5):
    try:
        time.sleep(sleep_time + random.random() * 3)
        response = requests.get(url)
        response.raise_for_status()  # 如果响应状态不是200，将引发HTTPError异常
        data = response.json()
    # deal with errors
    except Exception as e:
        logger.error(f"Exception: {e}")
        if retry > 0:
            logger.info(f"retrying {url}")
            return request_data(url, retry - 1)
        else:
            logger.error(f"Failed to request {url}")
        return None
    else:
        return data

def _rate_limited_request(url, last_request_time, min_interval=1.0, timeout=10, **kwargs):
    """发送限速 HTTP 请求，确保两次请求间隔至少 min_interval 秒。
    返回 (response, new_last_request_time)。"""
    now = time.time()
    elapsed = now - last_request_time
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    resp = requests.get(url, timeout=timeout, **kwargs)
    return resp, time.time()


def clean_abstract(text: str) -> str:
    """清洗 abstract 文本：去除 XML 标签、合并不合理换行、压缩空白。"""
    if not text:
        return ""
    # 去除 Crossref 残留的 XML 标签（保留标签内文本）
    text = re.sub(r"<jats:p>(.*?)</jats:p>", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    # 去除首尾空白
    text = text.strip()
    # 处理连字符换行（hyphenated line break）
    text = re.sub(r"-\n\s*", "", text)
    text = re.sub(r"-\r\n\s*", "", text)
    # 合并句子内硬换行：换行后下一行以小写字母或数字开头
    text = re.sub(r"\n\s*([a-z0-9])", r" \1", text)
    text = re.sub(r"\r\n\s*([a-z0-9])", r" \1", text)
    # 将连续空白（含制表符、换行）替换为单个空格
    text = re.sub(r"[\s\t]+", " ", text)
    return text.strip()


def is_title_match(api_title: str, paper_title: str, threshold: float = 0.70) -> bool:
    """基于标题模糊匹配的二次验证。

    先进行包含检测（去除标点后一个标题是否包含另一个），
    若不通过则回退到 difflib 相似度比对。
    """
    if not api_title or not paper_title:
        return False
    # 规范化：小写并去除标点/空白，保留 Unicode 词字符（字母数字及下划线）
    norm = lambda t: re.sub(r"[^\w]+", "", t.strip().lower(), flags=re.UNICODE)
    n_api = norm(api_title)
    n_paper = norm(paper_title)
    # 若规范化后为空，无法进行可靠匹配（避免 "" in "" 误判）
    if not n_api or not n_paper:
        return False
    # 包含检测：允许大小写、标点、副标题差异
    if n_api in n_paper or n_paper in n_api:
        return True
    # 回退到相似度阈值
    ratio = difflib.SequenceMatcher(None, n_api, n_paper).ratio()
    return ratio >= threshold


def _fetch_crossref_abstract(doi: str, last_request_time: float, min_interval: float = 1.0, max_retries: int = 3, contact_email: str = ""):
    """通过 Crossref 获取 abstract，返回 (abstract_or_None, api_title_or_None, last_request_time)。"""
    url = f"https://api.crossref.org/works/{doi}"
    agent = f"FL-paper-update-tracker/1.0 (mailto:{contact_email})" if contact_email else "FL-paper-update-tracker/1.0"
    headers = {"User-Agent": agent}
    for attempt in range(1, max_retries + 1):
        try:
            resp, last_request_time = _rate_limited_request(
                url, last_request_time, min_interval=min_interval, timeout=10, headers=headers
            )
            if resp.status_code in (404, 403):
                return None, None, last_request_time
            if resp.status_code == 429:
                wait = 2 ** attempt
                logger.warning(f"Rate limited (Crossref), waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            item = data.get("message", {})
            # 提取返回的标题（Crossref 的 title 通常为列表）
            raw_title = item.get("title")
            if isinstance(raw_title, list) and raw_title:
                api_title = str(raw_title[0]).strip() or None
            elif raw_title:
                api_title = str(raw_title).strip() or None
            else:
                api_title = None
            abstract = item.get("abstract")
            if abstract and isinstance(abstract, str):
                cleaned = clean_abstract(abstract)
                if cleaned:
                    return cleaned, api_title, last_request_time
            return None, api_title, last_request_time
        except requests.exceptions.Timeout:
            logger.warning(f"Crossref timeout for {doi}, attempt {attempt}")
            if attempt < max_retries:
                time.sleep(2 ** attempt)
        except Exception as e:
            logger.warning(f"Crossref attempt {attempt} failed for {doi}: {e}")
            if attempt < max_retries:
                time.sleep(2 ** attempt)
    return None, None, last_request_time


def _fetch_semantic_scholar_abstract(doi: str, last_request_time: float, min_interval: float = 1.0, max_retries: int = 3):
    """通过 Semantic Scholar 获取 abstract，返回 (abstract_or_None, api_title_or_None, last_request_time)。"""
    url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"
    params = {"fields": "abstract,title"}
    for attempt in range(1, max_retries + 1):
        try:
            resp, last_request_time = _rate_limited_request(
                url, last_request_time, min_interval=min_interval, timeout=10, params=params
            )
            if resp.status_code in (404, 403):
                return None, None, last_request_time
            if resp.status_code == 429:
                wait = 2 ** attempt
                logger.warning(f"Rate limited (SS), waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            api_title = data.get("title")
            if api_title:
                api_title = str(api_title).strip() or None
            abstract = data.get("abstract")
            if abstract and abstract.strip():
                return clean_abstract(abstract), api_title, last_request_time
            return None, api_title, last_request_time
        except requests.exceptions.Timeout:
            logger.warning(f"SS timeout for {doi}, attempt {attempt}")
            if attempt < max_retries:
                time.sleep(2 ** attempt)
        except Exception as e:
            logger.warning(f"SS attempt {attempt} failed for {doi}: {e}")
            if attempt < max_retries:
                time.sleep(2 ** attempt)
    return None, None, last_request_time


def _fetch_arxiv_abstract(title: str, last_request_time: float, min_interval: float = 1.0, max_retries: int = 3):
    """通过 arXiv API 获取 abstract，返回 (abstract_or_None, api_title_or_None, last_request_time)。"""
    import xml.etree.ElementTree as ET

    # arXiv API 建议至少 3 秒间隔
    effective_interval = max(min_interval, 3.0)
    encoded_title = urllib.parse.quote(title)
    url = f"http://export.arxiv.org/api/query?search_query=ti:{encoded_title}&max_results=1"
    ns = {"atom": "http://www.w3.org/2005/Atom"}

    for attempt in range(1, max_retries + 1):
        try:
            resp, last_request_time = _rate_limited_request(
                url, last_request_time, min_interval=effective_interval, timeout=10
            )
            if resp.status_code in (404, 403):
                return None, None, last_request_time
            if resp.status_code == 429:
                wait = 2 ** attempt
                logger.warning(f"Rate limited (arXiv), waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()

            root = ET.fromstring(resp.text)
            entry = root.find("atom:entry", ns)
            if entry is None:
                return None, None, last_request_time

            api_title = None
            title_elem = entry.find("atom:title", ns)
            if title_elem is not None and title_elem.text:
                api_title = title_elem.text.strip()

            abstract = None
            summary_elem = entry.find("atom:summary", ns)
            if summary_elem is not None and summary_elem.text:
                cleaned = clean_abstract(summary_elem.text)
                if cleaned:
                    abstract = cleaned

            return abstract, api_title, last_request_time
        except requests.exceptions.Timeout:
            logger.warning(f"arXiv timeout for title '{title[:60]}...', attempt {attempt}")
            if attempt < max_retries:
                time.sleep(2 ** attempt)
        except Exception as e:
            logger.warning(f"arXiv attempt {attempt} failed for title '{title[:60]}...': {e}")
            if attempt < max_retries:
                time.sleep(2 ** attempt)
    return None, None, last_request_time


def fetch_abstract_for_papers(papers, sleep_sec=1.0, max_retries=3, contact_email=""):
    """为论文列表批量获取 abstract。

    Args:
        papers: 论文 dict 列表，每个 dict 应包含 doi、title 等字段。
        sleep_sec: 两次请求之间的最小间隔（秒），默认 1.0（即每秒最多 1 次）。
        max_retries: 每个 API 的最大重试次数。
        contact_email: 用于 Crossref User-Agent 的联系邮箱（可选）。

    Returns:
        传入的 papers 列表（原地修改，为每个 dict 添加/更新 abstract 字段）。
    """
    last_request_time = {
        "crossref": 0.0,
        "semanticscholar": 0.0,
        "arxiv": 0.0,
    }
    success = 0
    failed = 0
    skipped = 0

    for i, paper in enumerate(papers, 1):
        doi = (paper.get("doi") or "").strip()
        title = (paper.get("title") or "").strip()

        # 跳过已有非空 abstract 的
        if paper.get("abstract") and str(paper.get("abstract")).strip():
            skipped += 1
            continue

        logger.info(f"[{i}/{len(papers)}] Fetching abstract: {title[:60]}... (DOI: {doi or 'N/A'})")
        abstract = None

        if doi:
            # 优先 Crossref
            abstract, api_title, last_request_time["crossref"] = _fetch_crossref_abstract(
                doi, last_request_time["crossref"], min_interval=sleep_sec, max_retries=max_retries,
                contact_email=contact_email
            )
            if abstract and api_title and not is_title_match(api_title, title):
                logger.warning(
                    f"  -> Crossref title mismatch for DOI {doi}: "
                    f"expected '{title[:80]}...', got '{api_title[:80]}...'"
                )
                abstract = None
            # Crossref 失败则尝试 Semantic Scholar
            if not abstract:
                abstract, api_title, last_request_time["semanticscholar"] = _fetch_semantic_scholar_abstract(
                    doi, last_request_time["semanticscholar"], min_interval=sleep_sec, max_retries=max_retries
                )
                if abstract and api_title and not is_title_match(api_title, title):
                    logger.warning(
                        f"  -> Semantic Scholar title mismatch for DOI {doi}: "
                        f"expected '{title[:80]}...', got '{api_title[:80]}...'"
                    )
                    abstract = None

        # Crossref + SS 都失败，尝试 arXiv 作为最后补充
        if not abstract and title:
            abstract, api_title, last_request_time["arxiv"] = _fetch_arxiv_abstract(
                title, last_request_time["arxiv"], min_interval=max(sleep_sec, 3.0), max_retries=max_retries
            )
            if abstract and api_title and not is_title_match(api_title, title):
                logger.warning(
                    f"  -> arXiv title mismatch: "
                    f"expected '{title[:80]}...', got '{api_title[:80]}...'"
                )
                abstract = None

        if abstract:
            paper["abstract"] = abstract
            success += 1
            logger.info(f"  -> OK ({len(abstract)} chars)")
        else:
            paper["abstract"] = ""
            failed += 1
            logger.info("  -> Failed")

    logger.info(f"Abstract fetch done. Success: {success}, Failed: {failed}, Skipped: {skipped}")
    return papers


def _translate_with_qwen_mt(text: str, client, max_retries: int = 3):
    """调用阿里云百炼 Qwen-MT-plus 将文本翻译为中文，失败返回 None。

    使用 OpenAI 兼容接口（openai SDK）调用，逐条翻译。
    """
    if not text or client is None:
        return None

    for attempt in range(1, max_retries + 1):
        try:
            completion = client.chat.completions.create(
                model="qwen-mt-plus",
                messages=[{"role": "user", "content": text}],
                extra_body={
                    "translation_options": {
                        "source_lang": "auto",
                        "target_lang": "Chinese",
                    }
                },
            )
            content = completion.choices[0].message.content
            if content and content.strip():
                return content.strip()
            return None
        except Exception as e:
            err_str = str(e)
            # 对限流错误做更长的等待
            if "rate limit" in err_str.lower() or "429" in err_str:
                wait = 2 ** attempt
                logger.warning(f"Rate limited (Qwen-MT), waiting {wait}s...")
                time.sleep(wait)
                continue
            logger.warning(f"Qwen-MT attempt {attempt} failed: {e}")
            if attempt < max_retries:
                time.sleep(2 ** attempt)
    return None


def translate_abstracts_for_papers(papers, api_key="", sleep_sec=0.5, max_retries=3):
    """为成功获取英文摘要的论文批量翻译中文摘要（abstract_cn）。

    Args:
        papers: 论文 dict 列表，每个 dict 应包含 abstract 字段。
        api_key: 阿里云百炼 API Key。
        sleep_sec: 两次翻译请求之间的间隔（秒），默认 0.5。
        max_retries: 每个请求的最大重试次数。

    Returns:
        传入的 papers 列表（原地修改，为每个 dict 添加/更新 abstract_cn 字段）。
    """
    if not api_key:
        logger.warning("DASHSCOPE_API_KEY not set, skipping translation.")
        return papers
    try:
        from openai import OpenAI
    except ImportError:
        logger.error("openai package is not installed. Run: pip install openai")
        return papers
    client = OpenAI(
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    targets = []
    for paper in papers:
        abstract = str(paper.get("abstract") or "").strip()
        existing_cn = str(paper.get("abstract_cn") or "").strip()
        if abstract and not existing_cn:
            targets.append(paper)

    if not targets:
        logger.info("No papers need Chinese translation.")
        return papers

    logger.info(f"Starting Chinese translation for {len(targets)} papers...")
    success = 0
    failed = 0

    for i, paper in enumerate(targets, 1):
        abstract = paper["abstract"]
        title = (paper.get("title") or "").strip()
        logger.info(f"[{i}/{len(targets)}] Translating: {title[:60]}...")
        translated = _translate_with_qwen_mt(abstract, client, max_retries=max_retries)
        if translated:
            paper["abstract_cn"] = translated
            success += 1
            logger.info(f"  -> OK ({len(translated)} chars)")
        else:
            paper["abstract_cn"] = ""
            failed += 1
            logger.info("  -> Failed")
        if i < len(targets):
            time.sleep(sleep_sec)

    logger.info(f"Translation done. Success: {success}, Failed: {failed}")
    return papers
