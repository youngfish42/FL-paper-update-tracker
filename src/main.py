from loguru import logger
from fire import Fire
from utils import (
    get_msg, init, get_dblp_items, request_data,
    deduplicate_items_by_ee, deduplicate_items_by_title,
    filter_items_by_year, get_topic_short_name,
    format_title_topics, fetch_abstract_for_papers,
    translate_abstracts_for_papers,
)
import yaml
import datetime
import urllib.parse
import os

# 本地开发时从 .env 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass



class Scaffold:
    def __init__(self):
        pass

    def run(self, env: str = "dev", cfg: str = "./../config.yaml"):
        cfg = init(cfg_path=cfg)

        logger.info(f"running with env: {env} and cfg: {cfg}")

        # dblp

        # load cache
        cache_path = cfg["cache_path"] / "dblp.yaml"
        dblp_cache = yaml.safe_load(open(cache_path, "r")) if cache_path.exists() else {}
        # logger.info(f"dblp cache: {dblp_cache}")
        dblp_new_cache = {}

        dblp_url = cfg["dblp"]["url"]
        keyword = cfg["dblp"]["keyword"]
        queries = cfg["dblp"]["queries"]
        mails = cfg["dblp"].get("mails", [])
        contact_email = mails[0] if mails else ""
        aggregated_msg = ""
        msg = ""
        flag = False
        active_topics = []  # 收集本次有新增论文的 topic 简称

        logger.info(f"keyword: {keyword}, queries: {queries}")

        # 全局去重集合：跨所有 topic 跟踪已见过的 ee 和 title，防止同一论文被缓存到多个 topic 下
        global_seen_ee = set()
        global_seen_title = set()
        for topic, items in dblp_cache.items():
            for item in items:
                ee = item.get("ee", "")
                title = item.get("title", "").strip()
                if ee:
                    global_seen_ee.add(ee)
                if title:
                    global_seen_title.add(title)

        for query in queries:
            topic = f"{keyword}%20{urllib.parse.quote(query, safe='')}"
            # random sleep to avoid being blocked
            dblp_data = request_data(dblp_url.format(topic))

            if dblp_data is None:
                logger.error(f"dblp_data is None, topic: {topic}")
                continue
        
            # 如果没有异常，则执行这里的代码
            # logger.info(f"dblp_data: {dblp_data}")

            # 解析 DBLP 返回的原始数据，提取需要的字段
            items = get_dblp_items(dblp_data)
            # logger.info(f"items: {items}")

            # 按年份过滤，仅保留近三年及未来一年的论文（如 2026 年则保留 2023-2027）
            current_year = datetime.datetime.now().year
            items = filter_items_by_year(items, current_year)

            # 对当前 topic 获取的论文列表先按 ee 去重，再按 title 去重
            items = deduplicate_items_by_ee(items)
            items = deduplicate_items_by_title(items)

            # 从缓存中读取该 topic 已保存的论文列表
            cached_items = dblp_cache.get(topic, [])
            # 构建已缓存论文的 ee 集合和 title 集合，用于判断哪些是新论文
            cached_ee_set = {item.get("ee", "") for item in cached_items if item.get("ee", "")}
            cached_title_set = {item.get("title", "").strip() for item in cached_items if item.get("title", "")}
            # 筛选出 ee 和 title 均不在该 topic 缓存集合中，且不在全局集合中的论文作为新论文
            new_items = [
                item for item in items
                if item.get("ee", "") not in cached_ee_set
                and item.get("title", "").strip() not in cached_title_set
                and item.get("ee", "") not in global_seen_ee
                and item.get("title", "").strip() not in global_seen_title
            ]
            dblp_new_cache[topic] = new_items

            # 将新论文的 ee 和 title 加入全局集合
            for item in new_items:
                ee = item.get("ee", "")
                title = item.get("title", "").strip()
                if ee:
                    global_seen_ee.add(ee)
                if title:
                    global_seen_title.add(title)

            # 若该 topic 首次查询，则初始化为空列表
            if topic not in dblp_cache:
                dblp_cache[topic] = []

            # 为新增论文自动获取 abstract
            if new_items:
                fetch_abstract_for_papers(new_items, sleep_sec=2.0, max_retries=4, contact_email=contact_email)
                api_key = os.getenv("DASHSCOPE_API_KEY", "")
                translate_abstracts_for_papers(new_items, api_key=api_key, sleep_sec=0.5, max_retries=3)

            # 将新论文追加到缓存中（已保证无 ee/title 重复）
            dblp_cache[topic].extend(new_items)

            logger.info(f"new_items: {new_items}")

            # if there is any new items, we set flag to create a new issue
            if len(new_items) > 0:
                flag = True

            # only when new items >0 in this topic we creat the msg
            if len(new_items) > 0:
                aggregated_msg += get_msg(new_items, topic, aggregated=True)
                msg += get_msg(new_items, topic)
                # 收集该 topic 的简称，用于后续 Issue 标题
                active_topics.append(get_topic_short_name(topic))
            logger.info(f"aggregated_msg: {aggregated_msg}")
            logger.info(f"msg: {msg}")

        # save cache
        yaml.safe_dump(dblp_cache, open(cache_path, "w"), sort_keys=False, indent=2)

        if env == "prod":
            import os

            env_file = os.getenv("GITHUB_ENV")

            # check if msg is too long
            if len(msg) > 4096:
                msg = msg[:4096] + "..."

            if flag:
                # 生成 Issue 标题中的 topic 片段，控制长度不超过 80 字符
                title_topics = format_title_topics(active_topics)
                with open(env_file, "a") as f:
                    f.write("MSG=$'" + aggregated_msg + msg + "'\n")
                    f.write(f"ISSUE_TITLE_TOPICS={title_topics}\n")


if __name__ == "__main__":
    Fire(Scaffold)
