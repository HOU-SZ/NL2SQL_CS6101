import requests
import os
from loguru import logger
import pandas as pd
from tqdm import tqdm

STAGE = os.getenv('STAGE')
JOB_ID = os.getenv('JOB_ID')
NL2SQL_DATASOURCE_PATH = os.getenv('NL2SQL_DATASOURCE_PATH', 'data/demo')
NL2SQL_WORK_DIR = os.getenv('NL2SQL_WORK_DIR', 'data/demo')
NL2SQL_TRAIN_DATA_SUB_PATH = os.getenv('NL2SQL_TRAIN_DATA_SUB_PATH', 'train/data.json')
API_KEY = os.getenv('BI_API_KEY', '74e8a8580a475932590527a07df974b5')
url = f"http://data-query-app-service-{STAGE}-{JOB_ID}:8000/api/v1"
# url = "http://127.0.0.1:29080/api/v1"


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


def create_query(q, api_key, org_id, topic_id):
    resp = requests.post(f"{url}/org/{org_id}/topic/{topic_id}/query",
                         headers={'Content-Type': 'application/json', 'X-API-KEY': api_key},
                         json={
                             'content': q
                         }, params={
            'interactive': True,
            'execute_sql': False
        })
    resp.raise_for_status()
    query = resp.json()
    return query['data']['id']


def update_query(q_id, sql, api_key, org_id, topic_id):
    resp = requests.put(f"{url}/org/{org_id}/topic/{topic_id}/queries/{q_id}",
                        headers={'Content-Type': 'application/json', 'X-API-KEY': api_key},
                        json={
                            'raw_sql': sql,
                            'sql_generator': 'TEMPLATE'
                        })
    resp.raise_for_status()
    return resp.json()


def insert(train):
    with tqdm(total=len(train)) as pbar:
        for i, row in train.iterrows():
            q = row['query']
            sql = row['sql']
            q_id = create_query(q, API_KEY, 1, 1)
            resp = update_query(q_id, sql, API_KEY, 1, 1)
            logger.info(f"update response {resp}")
            pbar.update(1)


def main():
    train = load_data(os.path.join(NL2SQL_DATASOURCE_PATH, NL2SQL_TRAIN_DATA_SUB_PATH))
    insert(train)


if __name__ == '__main__':
    main()
