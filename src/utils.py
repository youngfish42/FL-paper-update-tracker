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


def get_msg(items, topic, aggregated=False):
    # change "topic" from url to string
    string_topic = urllib.parse.unquote(topic)
    # get name of topic
    name_topic = string_topic.split(":")[-2]

    # print information of topic
    msg = f"## [{name_topic}](https://dblp.org/search?q={topic})\\n\\n"
    msg += f"""Explore {len(items)} new papers about {name_topic}.\\n\\n"""

    if aggregated == False:
        for item in items:
            msg += f"{item['title']}\\n"
            # msg += f"[{item['title']}]({item['url']})\\n"
            # msg += f"- Authors: {item['author']}\\n"
            # msg += f"- Venue: {item['venue']}\\n"
            msg += f"- Year: {item['year']}\\n\\n"

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