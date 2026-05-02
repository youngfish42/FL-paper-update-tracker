from loguru import logger
from fire import Fire
from utils import get_msg, init, get_dblp_items, request_data, deduplicate_items_by_ee, filter_items_by_year, get_topic_short_name, format_title_topics
import yaml
import datetime



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
        aggregated_msg = ""
        msg = ""
        flag = False
        active_topics = []  # 收集本次有新增论文的 topic 简称

        logger.info(f"topics: {cfg['dblp']['topics']}")

        for topic in cfg["dblp"]["topics"]:
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

            # 对当前 topic 获取的论文列表按 ee 去重，消除同一次查询中返回的重复论文
            items = deduplicate_items_by_ee(items)

            # 从缓存中读取该 topic 已保存的论文列表
            cached_items = dblp_cache.get(topic, [])
            # 构建已缓存论文的 ee 集合，用于判断哪些是新论文
            cached_ee_set = {item.get("ee", "") for item in cached_items if item.get("ee", "")}
            # 筛选出 ee 不在缓存集合中的论文作为新论文（基于 ee 去重，避免作者字段微差异导致重复）
            new_items = [item for item in items if item.get("ee", "") not in cached_ee_set]
            dblp_new_cache[topic] = new_items

            # 若该 topic 首次查询，则初始化为空列表
            if topic not in dblp_cache:
                dblp_cache[topic] = []
            # 将新论文追加到缓存中（已保证无 ee 重复）
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
