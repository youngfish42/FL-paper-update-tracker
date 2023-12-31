from loguru import logger
from fire import Fire
from utils import get_msg, init, get_dblp_items, request_data
import yaml



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

        logger.info(f"topics: {cfg['dblp']['topics']}")

        for topic in cfg["dblp"]["topics"]:
            # random sleep to avoid being blocked
            dblp_data = request_data(dblp_url.format(topic))

            if dblp_data is None:
                logger.error(f"dblp_data is None, topic: {topic}")
                continue
        
            # 如果没有异常，则执行这里的代码
            # logger.info(f"dblp_data: {dblp_data}")

            # get items
            items = get_dblp_items(dblp_data)
            # logger.info(f"items: {items}")

            # add new cache for this topic
            cached_items = dblp_cache.get(
                topic, []
            )  # get the value of the key "topic" in dblp_cache, if not exist, return []
            new_items = [item for item in items if item not in cached_items]  # get the new items
            dblp_new_cache[topic] = new_items

            if topic not in dblp_cache:
                dblp_cache[topic] = []
            dblp_cache[topic].extend(new_items)

            logger.info(f"new_items: {new_items}")

            # if there is any new items, we set flag to create a new issue
            if len(new_items) > 0:
                flag = True

            # only when new items >0 in this topic we creat the msg
            if len(new_items) > 0:
                aggregated_msg += get_msg(new_items, topic, aggregated=True)
                msg += get_msg(new_items, topic)
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
                with open(env_file, "a") as f:
                    f.write("MSG=$'" + aggregated_msg + msg + "'")
                    # f.write("MSG=$'" + msg + "'")


if __name__ == "__main__":
    Fire(Scaffold)
