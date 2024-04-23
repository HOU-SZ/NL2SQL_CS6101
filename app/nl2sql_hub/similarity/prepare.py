import click
import numpy as np
import os
from loguru import logger

import pandas as pd
import requests
import json
import asyncio
import aiohttp
import json
from tqdm import tqdm
import argparse
import nest_asyncio
import sys

nest_asyncio.apply()

import os
from dotenv import load_dotenv

load_dotenv()
task_service_url = os.getenv("TASK_SERVICE_URL", None)


def load_data(filepath):
    # 读取数据
    logger.info(f"Loading data from {filepath}")
    train = pd.read_json(filepath)

    # 去重
    train = train.drop_duplicates("query", keep="last")
    train.index = range(len(train))

    logger.info(f"train data shape {train.shape}")
    logger.info(f"train data examples {train.head(3)}")

    return train


def delete_existing_data(scene_id):
    url = f"{task_service_url}/api/v1/examplesByInfo"
    headers = {"Content-Type": "application/json"}

    data = {"scene_id": scene_id}

    response = requests.post(url, headers=headers, data=json.dumps(data))
    scene_id_examples = [x["id"] for x in response.json()]
    logger.info(f"Deleting {len(scene_id_examples)} records")

    for id_ in tqdm(scene_id_examples):
        url = f"{task_service_url}/api/v1/examples/{id_}"
        response = requests.delete(url)


async def post_data(semaphore, queue, session, url, headers, data, max_retries=3):
    async with semaphore:
        for _ in range(max_retries):
            try:
                timeout = aiohttp.ClientTimeout(total=5 * 60)
                async with session.post(
                        url, headers=headers, data=json.dumps(data), timeout=timeout
                ) as response:
                    await queue.put(1)  # 任务完成，队列中加入一个元素
                    if response.status != 201:
                        logger.info(
                            f"Failed to post data: {data}, response: {response}"
                        )
                        raise Exception(
                            f"Failed to post data: {data}, response: {response}"
                        )
                    return await response.json()
            except (asyncio.exceptions.TimeoutError, aiohttp.ClientError) as e:
                if _ == max_retries - 1:
                    await queue.put(1)
                    logger.info(f"Failed to post data: {data}", e)
                    sys.exit(1)
                continue


async def update_progress_bar(queue, pbar, total):
    """专门的协程来更新进度条"""
    for _ in range(total):
        await queue.get()  # 等待一个任务完成
        pbar.update(1)  # 更新进度条


async def insert(train, scene_id):
    url = f"{task_service_url}/api/v1/examples"
    headers = {"Content-Type": "application/json"}

    logger.info(f"Inserting {len(train)} records to scene {scene_id}, url {url}")

    # 删除现有的数据
    delete_existing_data(scene_id)

    concurrent_limit = 3

    conn = aiohttp.TCPConnector(limit=concurrent_limit)
    queue = asyncio.Queue()
    semaphore = asyncio.Semaphore(concurrent_limit)

    with tqdm(total=len(train)) as pbar:
        # 启动专门的进度条更新协程
        progress_task = asyncio.create_task(
            update_progress_bar(queue, pbar, len(train))
        )

        async with aiohttp.ClientSession(connector=conn) as session:
            tasks = []
            for idx in range(len(train)):
                query = train.loc[idx, "query"]
                sql = train.loc[idx, "sql"]
                data = {"scene_id": scene_id, "user_query": query, "sql_query": sql}
                tasks.append(post_data(semaphore, queue, session, url, headers, data))

            await asyncio.gather(*tasks, progress_task)


@click.command()
@click.option("--nl2sql-workdir", default="data/demo-work", help="workdir")
@click.option(
    "--examples-sub-path", default="expand-data.json", help="examples file subpath"
)
@click.option("--scene-id", default=0, help="Scene ID for the data")
def main(nl2sql_workdir, examples_sub_path, scene_id):
    train = load_data(os.path.join(nl2sql_workdir, examples_sub_path))
    asyncio.run(insert(train, scene_id))


if __name__ == "__main__":
    main()
