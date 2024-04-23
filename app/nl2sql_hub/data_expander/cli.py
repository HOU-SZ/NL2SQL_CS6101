import click
from nl2sql_hub.data_expander.noop_expander import NoopDataExpander
from nl2sql_hub.data_expander.sagegpt_bi_template_expander import (
    SageGPTBITemplateExpander,
)
from nl2sql_hub.data_expander.openai_expander import OpenAIExpander
from nl2sql_hub.datasource import DataSource
from langchain.sql_database import SQLDatabase
from loguru import logger
import json
import random
import os

db_org_topic_mapping = {
    "gyhh": (1, 1),
    "loreal": (2, 2),
    "yzkj": (7, 8),
    "tyjs": (12, 19),
    "bjdx": (16, 27),
    "hxjj": (17, 28),
    "icbc": (13, 21)
}


@click.command()
@click.option("--expander", multiple=True, default=["noop"], help="data expander")
@click.option("--nl2sql-workdir", default="data/demo-work", help="workdir")
@click.option(
    "--examples-sub-path", default="expand-data.json", help="examples file subpath"
)
@click.option("--shuffle", default=True, help="shuffle the data, default is True")
@click.option(
    "--datasource-path", "datasource_path", default="data/demo", help="datasource path"
)
@click.option(
    "--input-dataset-name-or-path",
    "datasource_path",
    hidden=True,
    default="data/demo",
    help="input dataset name or path",
)
@click.option(
    '--expander-args',
    default='{}',
    help='expander args, use json format, e.g. {"max_per_tpl": 10}',
)
def main(
        expander: list[str],
        datasource_path,
        nl2sql_workdir,
        examples_sub_path,
        shuffle,
        expander_args,
):
    try:
        expander_args = json.loads(expander_args)
    except Exception as e:
        logger.error(f"expander args error: {e}")
        raise e
    # for sagegpt-bi template expander
    with open(os.path.join(datasource_path, "datasource.json"), "r") as f:
        ds = json.load(f)
        print(f"load datasource from {datasource_path}, content:\n{ds}\n")
        datasource = DataSource.parse_obj(ds)
        for db_prefix in db_org_topic_mapping.keys():
            if datasource.name and db_prefix in datasource.name:
                org_id, topic_id = db_org_topic_mapping[db_prefix]
                logger.info(
                    f"found datasource {datasource.name}, org_id={org_id}, topic_id={topic_id}"
                )
                break

    used_expanders = []
    for name in expander:
        if name == "noop":
            used_expanders.append(NoopDataExpander())
        elif name == "template":
            used_expanders.append(
                SageGPTBITemplateExpander(org_id=org_id, topic_id=topic_id, **expander_args)
            )
        elif name == "openai":
            used_expanders.append(OpenAIExpander(datasource=datasource))

    all_data = []
    try:
        for expander in used_expanders:
            expanded_data = expander.expand(datasource_path, nl2sql_workdir)
            logger.info(f"expanded {len(expanded_data)} examples by {expander.name()}")
            all_data.extend(expanded_data)

        # dedup by query
        logger.info(f"dedup by query, before: {len(all_data)}")
        seen = set()
        dedup_data = []
        for d in all_data:
            if d["query"] not in seen:
                seen.add(d["query"])
                dedup_data.append(d)
        all_data = dedup_data
        logger.info(f"dedup by query, after: {len(all_data)}")

        if shuffle:
            random.shuffle(all_data)
            logger.info(f"shuffle data")
        with open(os.path.join(nl2sql_workdir, examples_sub_path), "w") as target:
            logger.info(f"write to {target.name}")
            json.dump(all_data, target, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Expand error: {e}")
        raise e


if __name__ == "__main__":
    main()
