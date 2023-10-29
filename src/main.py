from loguru import logger
from fire import Fire
from utils import get_msg, init, get_dblp_items
import yaml
import requests
import json


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
        aggregated_msg = ""
        msg = ""
        flag = False

        for topic in cfg["dblp"]["topics"]:
            logger.info(f"topic: {topic}")

            # get dblp data
            # dblp_data = requests.get(dblp_url.format(topic)).json()
            # deal with the error: dblp_data is not json
            response = requests.get(dblp_url.format(topic))  
            try:
                response.raise_for_status()  # 如果响应状态不是200，将引发HTTPError异常  
                dblp_data = response.json()
            except requests.HTTPError as http_err:  
                logger.error(f'HTTP error occurred: {http_err}')   
            except json.JSONDecodeError:  
                logger.error('Response is not a valid JSON. Maybe the server is down or the URL is incorrect.')  
                # if json is not valid, we set dblp_data to empty
                dblp_data = {}
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


            # if there is any new items, we set flag to create a new issue
            if len(new_items) > 0:
                flag = True
            
            # only when new items >0 in this topic we creat the msg
            if len(new_items) > 0:
                aggregated_msg+= get_msg(new_items, topic ,True)
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
