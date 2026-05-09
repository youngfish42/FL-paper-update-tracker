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


DBLP_SEARCH_RETRY_BASE_SECONDS = 4.0
DBLP_SEARCH_RETRY_CAP_SECONDS = 120.0
DBLP_SEARCH_JITTER_MIN_SECONDS = 0.5
DBLP_SEARCH_JITTER_MAX_SECONDS = 2.5


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

def _parse_retry_after_seconds(retry_after_value):
    """解析 Retry-After 头（秒），失败则返回 None。"""
    if not retry_after_value:
        return None
    try:
        wait_seconds = float(retry_after_value)
    except (TypeError, ValueError):
        return None
    return wait_seconds if wait_seconds > 0 else None


def _compute_backoff_seconds(attempt: int, base: float = 2.5, cap: float = 90.0, jitter_ratio: float = 0.3):
    """计算指数退避时长（秒），带轻微随机抖动。

    这里的 attempt 是从 1 开始的重试序号：等待序列为
    base, 2*base, 4*base, 8*base ...，直到 cap 为止。
    """
    exp_wait = min(cap, base * (2 ** max(0, attempt - 1)))
    jitter = exp_wait * jitter_ratio * random.random()
    return min(cap, exp_wait + jitter)


def _sleep_for_retry(source: str, attempt: int, response=None, base: float = 2.5, cap: float = 90.0):
    """统一退避等待：优先 Retry-After，否则指数退避+抖动。"""
    retry_after = None
    if response is not None:
        retry_after = _parse_retry_after_seconds(response.headers.get("Retry-After"))
    if retry_after is not None:
        wait = min(cap, retry_after)
    else:
        wait = _compute_backoff_seconds(attempt, base=base, cap=cap)
    wait = max(wait, 1.0)
    logger.warning(f"{source} retry backoff: waiting {wait:.1f}s (attempt {attempt})")
    time.sleep(wait)
    return wait


def request_data(url, retry=10, sleep_time=6.0, timeout=15):
    """请求 DBLP 数据，带限速与更严格退避重试。

    Args:
        url: DBLP 请求 URL。
        retry: 失败后的额外重试次数（总尝试次数 = retry + 1）。
        sleep_time: 每次请求前的基础等待秒数（会叠加随机抖动）。
        timeout: 单次请求超时时间（秒）。
    """
    max_attempts = retry + 1
    for attempt in range(1, max_attempts + 1):
        try:
            # DBLP 主流程查询：基础间隔 + 轻微抖动，降低突发请求概率
            time.sleep(sleep_time + random.uniform(DBLP_SEARCH_JITTER_MIN_SECONDS, DBLP_SEARCH_JITTER_MAX_SECONDS))
            response = requests.get(url, timeout=timeout)
            if response.status_code == 429:
                _sleep_for_retry(
                    "DBLP search API rate limited",
                    attempt,
                    response=response,
                    base=DBLP_SEARCH_RETRY_BASE_SECONDS,
                    cap=DBLP_SEARCH_RETRY_CAP_SECONDS,
                )
                continue
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Exception: {e}")
            if attempt < max_attempts:
                logger.info(f"retrying {url}")
                _sleep_for_retry(
                    "DBLP search API failure",
                    attempt,
                    base=DBLP_SEARCH_RETRY_BASE_SECONDS,
                    cap=DBLP_SEARCH_RETRY_CAP_SECONDS,
                )
                continue
            logger.error(f"Failed to request {url}")
            return None

def _rate_limited_request(url, last_request_time, min_interval=1.0, timeout=10, jitter=0.2, **kwargs):
    """发送限速 HTTP 请求，确保两次请求间隔至少 min_interval 秒。

    Args:
        url: 请求 URL。
        last_request_time: 上一次请求完成时间戳（秒）。
        min_interval: 最小请求间隔（秒）。
        timeout: 单次请求超时时间（秒）。
        jitter: 额外随机等待上限（秒），用于分散请求峰值。
        **kwargs: 透传给 requests.get 的参数（headers/params 等）。

    Returns:
        (response, new_last_request_time)
    """
    now = time.time()
    elapsed = now - last_request_time
    wait = max(0.0, min_interval - elapsed)
    if wait > 0:
        time.sleep(wait + random.uniform(0.0, jitter))
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
                _sleep_for_retry("Rate limited (Crossref)", attempt, response=resp)
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
                _sleep_for_retry("Crossref timeout", attempt)
        except Exception as e:
            logger.warning(f"Crossref attempt {attempt} failed for {doi}: {e}")
            if attempt < max_retries:
                _sleep_for_retry("Crossref failure", attempt)
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
                _sleep_for_retry("Rate limited (SS)", attempt, response=resp)
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
                _sleep_for_retry("SS timeout", attempt)
        except Exception as e:
            logger.warning(f"SS attempt {attempt} failed for {doi}: {e}")
            if attempt < max_retries:
                _sleep_for_retry("SS failure", attempt)
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
                _sleep_for_retry("Rate limited (arXiv)", attempt, response=resp)
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
                _sleep_for_retry("arXiv timeout", attempt)
        except Exception as e:
            logger.warning(f"arXiv attempt {attempt} failed for title '{title[:60]}...': {e}")
            if attempt < max_retries:
                _sleep_for_retry("arXiv failure", attempt)
    return None, None, last_request_time


def fetch_abstract_for_papers(papers, sleep_sec=2.0, max_retries=4, contact_email=""):
    """为论文列表批量获取 abstract。

    Args:
        papers: 论文 dict 列表，每个 dict 应包含 doi、title 等字段。
        sleep_sec: 两次请求之间的最小间隔（秒），默认 2.0（从 1.0 提升以降低限速风险）。
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


def _fetch_crossref_doi(title: str, last_request_time: float, min_interval: float = 1.0, max_retries: int = 3, contact_email: str = ""):
    """通过 Crossref 搜索 API 用标题查找 DOI，返回 (doi_or_None, api_title_or_None, last_request_time)。"""
    encoded_title = urllib.parse.quote(title)
    url = f"https://api.crossref.org/works?query.title={encoded_title}&rows=1"
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
                _sleep_for_retry("Rate limited (Crossref search)", attempt, response=resp)
                continue
            resp.raise_for_status()
            data = resp.json()
            items = data.get("message", {}).get("items", [])
            if not items:
                return None, None, last_request_time
            item = items[0]
            doi = item.get("DOI", "").strip()
            raw_title = item.get("title")
            if isinstance(raw_title, list) and raw_title:
                api_title = str(raw_title[0]).strip() or None
            elif raw_title:
                api_title = str(raw_title).strip() or None
            else:
                api_title = None
            if doi:
                return doi, api_title, last_request_time
            return None, api_title, last_request_time
        except requests.exceptions.Timeout:
            logger.warning(f"Crossref search timeout for '{title[:60]}...', attempt {attempt}")
            if attempt < max_retries:
                _sleep_for_retry("Crossref search timeout", attempt)
        except Exception as e:
            logger.warning(f"Crossref search attempt {attempt} failed for '{title[:60]}...': {e}")
            if attempt < max_retries:
                _sleep_for_retry("Crossref search failure", attempt)
    return None, None, last_request_time


def _fetch_semantic_scholar_doi(title: str, last_request_time: float, min_interval: float = 1.0, max_retries: int = 3):
    """通过 Semantic Scholar 搜索 API 用标题查找 DOI，返回 (doi_or_None, api_title_or_None, last_request_time)。"""
    encoded_title = urllib.parse.quote(title)
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={encoded_title}&fields=title,externalIds&limit=1"
    for attempt in range(1, max_retries + 1):
        try:
            resp, last_request_time = _rate_limited_request(
                url, last_request_time, min_interval=min_interval, timeout=10
            )
            if resp.status_code in (404, 403):
                return None, None, last_request_time
            if resp.status_code == 429:
                _sleep_for_retry("Rate limited (SS search)", attempt, response=resp)
                continue
            resp.raise_for_status()
            data = resp.json()
            papers = data.get("data", [])
            if not papers:
                return None, None, last_request_time
            paper = papers[0]
            api_title = paper.get("title")
            if api_title:
                api_title = str(api_title).strip() or None
            external_ids = paper.get("externalIds", {})
            doi = (external_ids.get("DOI") or "").strip()
            if doi:
                return doi, api_title, last_request_time
            return None, api_title, last_request_time
        except requests.exceptions.Timeout:
            logger.warning(f"SS search timeout for '{title[:60]}...', attempt {attempt}")
            if attempt < max_retries:
                _sleep_for_retry("SS search timeout", attempt)
        except Exception as e:
            logger.warning(f"SS search attempt {attempt} failed for '{title[:60]}...': {e}")
            if attempt < max_retries:
                _sleep_for_retry("SS search failure", attempt)
    return None, None, last_request_time


def _fetch_dblp_doi(key: str, last_request_time: float, min_interval: float = 1.0, max_retries: int = 3):
    """通过 DBLP XML API 用论文 key 重新查询 DOI，返回 (doi_or_None, api_title_or_None, last_request_time)。

    DBLP 的搜索 API 有时无法按 key 精确命中，因此直接请求单条记录的 XML 端点
    (https://dblp.org/rec/{key}.xml)。解析 <doi> 标签，若不存在则从 <ee>
    中以 https://doi.org/ 前缀提取 DOI。
    """
    if not key:
        return None, None, last_request_time
    import xml.etree.ElementTree as ET

    url = f"https://dblp.org/rec/{key}.xml"
    for attempt in range(1, max_retries + 1):
        try:
            resp, last_request_time = _rate_limited_request(
                url, last_request_time, min_interval=min_interval, timeout=10
            )
            if resp.status_code in (404, 403):
                return None, None, last_request_time
            if resp.status_code == 429:
                _sleep_for_retry("Rate limited (DBLP)", attempt, response=resp)
                continue
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
            # DBLP XML root is <dblp>, first child is the record element
            record = root.find(".")
            if record is None or len(root) == 0:
                return None, None, last_request_time
            record = root[0]

            api_title = None
            title_elem = record.find("title")
            if title_elem is not None and title_elem.text:
                api_title = title_elem.text.strip()

            # 1. 优先使用显式的 <doi> 标签
            doi = None
            doi_elem = record.find("doi")
            if doi_elem is not None and doi_elem.text:
                doi = doi_elem.text.strip()

            # 2. 若 <doi> 不存在，尝试从 <ee> 中提取 https://doi.org/... 链接
            if not doi:
                ee_elem = record.find("ee")
                if ee_elem is not None and ee_elem.text:
                    ee = ee_elem.text.strip()
                    if ee.startswith("https://doi.org/"):
                        doi = ee[len("https://doi.org/"):].strip()
                    elif ee.startswith("http://doi.org/"):
                        doi = ee[len("http://doi.org/"):].strip()

            if doi:
                return doi, api_title, last_request_time
            return None, api_title, last_request_time
        except requests.exceptions.Timeout:
            logger.warning(f"DBLP timeout for key '{key}', attempt {attempt}")
            if attempt < max_retries:
                _sleep_for_retry("DBLP timeout", attempt)
        except Exception as e:
            logger.warning(f"DBLP attempt {attempt} failed for key '{key}': {e}")
            if attempt < max_retries:
                _sleep_for_retry("DBLP failure", attempt)
    return None, None, last_request_time


def fetch_doi_for_papers(papers, sleep_sec=2.0, max_retries=4, contact_email="", overwrite=False):
    """为论文列表批量获取 DOI（默认仅补充缺失 DOI 的条目）。

    查询优先级：
      1. DBLP API（通过论文 key 重新查询，最权威）
      2. Crossref 搜索 API（通过标题搜索）
      3. Semantic Scholar 搜索 API（通过标题搜索）

    Args:
        papers: 论文 dict 列表，每个 dict 应包含 title 字段。
        sleep_sec: 两次请求之间的最小间隔（秒），默认 2.0（从 1.0 提升以降低限速风险）。
        max_retries: 每个 API 的最大重试次数。
        contact_email: 用于 Crossref User-Agent 的联系邮箱（可选）。
        overwrite: 是否对已有 DOI 的条目也重新获取。默认 False。

    Returns:
        传入的 papers 列表（原地修改，为每个 dict 添加/更新 doi 字段）。
    """
    last_request_time = {
        "dblp": 0.0,
        "crossref": 0.0,
        "semanticscholar": 0.0,
    }
    success = 0
    failed = 0
    skipped = 0

    for i, paper in enumerate(papers, 1):
        title = (paper.get("title") or "").strip()
        key = (paper.get("key") or "").strip()
        existing_doi = (paper.get("doi") or "").strip()

        if existing_doi and not overwrite:
            skipped += 1
            continue

        if not title:
            logger.info(f"[{i}/{len(papers)}] Skipping empty title")
            failed += 1
            continue

        logger.info(f"[{i}/{len(papers)}] Fetching DOI: {title[:60]}...")
        doi = None

        # 1. 优先 DBLP API（通过 key 重新查询，最权威）
        if key:
            doi, api_title, last_request_time["dblp"] = _fetch_dblp_doi(
                key, last_request_time["dblp"], min_interval=sleep_sec, max_retries=max_retries
            )
            if doi and api_title and not is_title_match(api_title, title):
                logger.warning(
                    f"  -> DBLP title mismatch for key '{key}': "
                    f"expected '{title[:80]}...', got '{api_title[:80]}...'"
                )
                doi = None

        # 2. DBLP 失败则尝试 Crossref
        if not doi:
            doi, api_title, last_request_time["crossref"] = _fetch_crossref_doi(
                title, last_request_time["crossref"], min_interval=sleep_sec, max_retries=max_retries,
                contact_email=contact_email
            )
            if doi and api_title and not is_title_match(api_title, title):
                logger.warning(
                    f"  -> Crossref title mismatch for '{title[:80]}...': "
                    f"got '{api_title[:80]}...'"
                )
                doi = None

        # 3. Crossref 失败则尝试 Semantic Scholar
        if not doi:
            doi, api_title, last_request_time["semanticscholar"] = _fetch_semantic_scholar_doi(
                title, last_request_time["semanticscholar"], min_interval=sleep_sec, max_retries=max_retries
            )
            if doi and api_title and not is_title_match(api_title, title):
                logger.warning(
                    f"  -> Semantic Scholar title mismatch for '{title[:80]}...': "
                    f"got '{api_title[:80]}...'"
                )
                doi = None

        if doi:
            paper["doi"] = doi
            success += 1
            logger.info(f"  -> OK (DOI: {doi})")
        else:
            failed += 1
            logger.info("  -> Failed")

    logger.info(f"DOI fetch done. Success: {success}, Failed: {failed}, Skipped: {skipped}")
    return papers
