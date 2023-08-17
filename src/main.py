from loguru import logger
from fire import Fire
from utils import get_msg, init, get_dblp_items
import yaml
import requests


class Scaffold:
    def __init__(self):
        pass

    def run(self, env: str = "dev", cfg: str = "./../config.yaml"):
        cfg = init(cfg_path=cfg)

        logger.info(f"running with env: {env} and cfg: {cfg}")

        # dblp

        # load cache
        cache_path = cfg["cache_path"] / "dblp.yaml"
        dblp_cache = (
            yaml.safe_load(open(cache_path, "r")) if cache_path.exists() else {}
        )
        logger.info(f"dblp cache: {dblp_cache}")
        dblp_new_cache = {}

        dblp_url = cfg["dblp"]["url"]
        msg = ""
        flag = False

        for topic in cfg["dblp"]["topics"]:
            logger.info(f"topic: {topic}")

            # get dblp data
            dblp_data = requests.get(dblp_url.format(topic)).json()
            logger.info(f"dblp_data: {dblp_data}")

            # get items
            items = get_dblp_items(dblp_data)
            logger.info(f"items: {items}")

            # new cache
            cached_items = dblp_cache.get(topic, [])
            new_items = [item for item in items if item not in cached_items]
            dblp_new_cache[topic] = new_items

            if topic not in dblp_cache:
                dblp_cache[topic] = []
            dblp_cache[topic].extend(new_items)

            logger.info(f"new_items: {new_items}")

            if len(new_items) > 0:
                flag = True

            msg += get_msg(new_items, topic)
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
                    f.write("MSG=$'" + msg + "'")


if __name__ == "__main__":
    Fire(Scaffold)
