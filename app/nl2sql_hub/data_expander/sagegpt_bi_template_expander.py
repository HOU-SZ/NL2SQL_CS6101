import json
import os
from loguru import logger

import requests
from nl2sql_hub.data_expander.base_expander import BaseExpander


class SageGPTBITemplateExpander(BaseExpander):
    def __init__(self, **kwargs):
        self.org_id = int(kwargs.get("org_id"))
        self.topic_id = int(kwargs.get("topic_id"))
        self.max_per_tpl = int(kwargs.get("max_per_tpl", "10"))
        self.bi_api_url = kwargs.get("bi_api_url") or os.getenv(
            "BI_API_URL", "http://172.21.64.33:8000/api/v1"
        )
        self.bi_app_auth = kwargs.get("bi_app_auth") or os.getenv("BI_APP_AUTH")
        logger.info(
            f"org_id: {self.org_id}, topic_id: {self.topic_id},  max_per_tpl: {self.max_per_tpl}",
            f"bi_api_url: {self.bi_api_url}, bi_app_auth: {self.bi_app_auth}",
        )

        self.max_templates = 500

        if self.bi_api_url == "http://172.21.64.33:8000/api/v1":
            logger.warning("using default bi_api_url, this may not work in future")
        if not self.bi_app_auth:
            raise Exception("BI_APP_AUTH is required, please set it in .env file")
        self.cli = requests.Session()
        self.cli.headers.update({"X-API-KEY": self.bi_app_auth})

    def list_all_templates(self):
        r = self.cli.get(
            f"{self.bi_api_url}/org/{self.org_id}/topic/{self.topic_id}/templates?active=True&page=1&size={self.max_templates}"
        )
        r.raise_for_status()
        try:
            templates = r.json()["data"]
        except Exception as e:
            logger.info(r.raw)
            raise e

        q_tpls = {t["origin_query"].strip(): t for t in templates}
        logger.info(f"load {len(q_tpls)} templates")
        return q_tpls

    def expand(self, input_dataset_name_or_path, nl2sql_workdir):
        q_tpls = self.list_all_templates()
        find = 0
        not_found = 0
        total = 0
        templates = {}

        not_found_queries = {}

        all_data = {}

        with open(
            os.path.join(input_dataset_name_or_path, "train/data.json"), "r"
        ) as f:
            train_data_list = json.load(f)
            for train_data in train_data_list:
                query = train_data["query"]
                query = query.strip(" \t\n\r")
                if not query:
                    logger.warning(f"empty query: {train_data}")
                    continue
                # insert origin query by default
                all_data[query] = train_data["sql"]
                for origin in q_tpls.keys():
                    origin = origin.strip(" \t\n\r")
                    if query in origin or origin in query:
                        find += 1
                        templates[query] = q_tpls[origin]["id"]
                        break
                else:
                    not_found_queries[query] = train_data["sql"]
                    not_found += 1
                total += 1
            logger.info(f"total queries {total}")
            logger.info(f"find {find} in templates")
            logger.info(f"left {not_found} queries not in templates")

        for tpl_id in set(templates.values()):
            r = self.cli.get(
                f"{self.bi_api_url}/org/{self.org_id}/topic/{self.topic_id}/template/{tpl_id}/examples?limit={self.max_per_tpl}"
            )
            r.raise_for_status()
            try:
                result = r.json()["data"]
                examples = result["examples"]
                for example in examples:
                    all_data[example["content"]] = example["raw_sql"]
            except Exception as e:
                logger.error(f"get examples error: {e}", exc_info=True)
                raise e

        return [{"query": k, "sql": v} for k, v in all_data.items() if k.strip() != ""]

    def name(self):
        return "template"
