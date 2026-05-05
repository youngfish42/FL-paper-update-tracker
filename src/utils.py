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