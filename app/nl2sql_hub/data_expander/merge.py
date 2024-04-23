import click
import json
from loguru import logger
import os
import random


@click.command()
@click.option("--inputs", multiple=True, default=[], help="input json file")
@click.option("--shuffle", default=True, help="shuffle the data, default is True")
@click.option("--nl2sql-workdir", default="data/demo-work", help="workdir")
@click.option(
    "--examples-sub-path", default="expand-data.json", help="examples file subpath"
)
def main(inputs, shuffle, nl2sql_workdir, examples_sub_path):
    all_data = []
    for file_name in inputs:
        print(f"merge {file_name}")
        with open(file_name, "r") as f:
            data = json.load(f)
            print(f"load {len(data)} examples")
            all_data.extend(data)

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


if __name__ == "__main__":
    main()
