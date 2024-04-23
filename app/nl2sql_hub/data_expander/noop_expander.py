import json
import os
from loguru import logger

from nl2sql_hub.data_expander.base_expander import BaseExpander


class NoopDataExpander(BaseExpander):
    def __init__(self):
        pass

    def expand(self, input_dataset_name_or_path, nl2sql_workdir):
        with open(
            os.path.join(input_dataset_name_or_path, "train/data.json"), "r"
        ) as f:
            all_data = json.load(f)
            logger.info(
                f"direct copy data from {input_dataset_name_or_path} to {nl2sql_workdir}"
            )
            return all_data

    def name(self):
        return "noop"
