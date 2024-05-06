import json
import sys
from flask import Flask, request
from langchain.sql_database import SQLDatabase
import argparse
import os
from core.service import run_generation_mac, run_genration_din
from core.llm import sqlcoder, GPT, DeepSeek, modelhub_deepseek_coder_33b_instruct, modelhub_qwen1_5_72b_chat
from multiprocessing import Value

counter = Value('i', -1)
app = Flask(__name__)

print("=============Starting service==============")
parser = argparse.ArgumentParser()
parser.add_argument("--model_name", type=str, choices=[
                    "gpt-3.5-turbo", "sqlcoder-7b-2", "deepseek-coder-33b-instruct", "modelhub-deepseek-coder-33b-instruct", "modelhub_qwen1_5_72b_chat"], default="sqlcoder-7b-2")
parser.add_argument("--method", type=str,
                    choices=["mac", "din"], default="mac")
args = parser.parse_args()
model_name = args.model_name
method = args.method
print(f"model_name: {model_name}")


for_submit = True
if for_submit:
    from nl2sql_hub.datasource import DataSource, get_url
    datasource_path = os.getenv("NL2SQL_DATASOURCE_PATH")
    with open(os.path.join(datasource_path, "datasource.json"), "r") as f:
        ds = json.load(f)
        print(f"load datasource from {datasource_path}, content: \n{ds}\n")
        db_name = ds.get("name")
        db_description = ds.get("description")
        db_tables = ds.get("tables")
        datasource = DataSource.parse_obj(ds)
    ds_url = get_url(datasource)
else:
    with open("datasource.json", "r", encoding='UTF-8') as f:
        ds = json.load(f)
        print(f"load datasource from datasource.json, content: \n{ds}\n")
        db_name = ds.get("name")
        db_description = ds.get("description")
        db_tables = ds.get("tables")
        datasource = ds
        ds_url = "sqlite:///./concert_singer.db"

print(f"datasource url: {ds_url}\n")
db_tool = SQLDatabase.from_uri(database_uri=ds_url)


# 获取数据库类型
db_type = db_tool.dialect
print(f"database type: {db_type}")  # 输出mysql


# 获取数据库中的所有表名
tables = db_tool.get_table_names()
# print("type of tables: ", type(tables))
# print("length of tables: ", len(tables))
print(f"tables: {tables}")  # 输出['t1', 't2', 't3']

# 获取table info
table_info = {}
for table in tables:
    cur_table_info = db_tool.get_table_info([table])
    table_info[table] = cur_table_info
    print(f"table_info: {cur_table_info}")  # 输出建表语句以及3条数据示例
print("length of table_info: ", len(table_info))


model_dict = {
    "gpt-3.5-turbo": GPT,
    "sqlcoder-7b-2": sqlcoder,
    "deepseek-coder-33b-instruct": DeepSeek,
    "modelhub-deepseek-coder-33b-instruct": modelhub_deepseek_coder_33b_instruct,
    "modelhub_qwen1_5_72b_chat": modelhub_qwen1_5_72b_chat
}

try:
    llm = model_dict[model_name]()
except Exception as e:
    print("Error in starting llm: ", e)
    sys.exit("Error in starting llm: ", e)


@ app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


@ app.route("/predict", methods=["POST"])
def predict():
    with counter.get_lock():
        counter.value += 1
        out = counter.value
    count = out
    content_type = request.headers.get("Content-Type")
    if content_type != "application/json":
        return {
            "success": False,
            "message": "Content-Type must be application/json"
        }
    print("count:", count)  # record the number of requests
    print("request:", request)
    request_json = request.json
    print("request_json:", request_json)
    question = request_json.get("natural_language_query")
    print(f"Question: {question}")

    sql_query = ""
    try:
        if method == "din":
            sql_query = run_genration_din(
                question, db_name, db_description, tables, table_info, llm, db_tool)
        else:
            sql_query = run_generation_mac(
                question, db_name, db_description, db_type, tables, table_info, llm)

    except Exception as e:
        print("Error: ", e)
        return {
            "success": False,
            "message": [str(e)]
        }
    print(f"Returned SQL query: {sql_query}")
    # save the count, db, question, and sql_query to the records json file
    with open("records.json", "a", encoding='UTF-8') as f:
        record = {
            "count": count,
            "db": db_name,
            "question": question,
            "sql_query": sql_query
        }
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    if count % 10 == 0:
        # print the records every 10 requests
        with open("records.json", "r", encoding='UTF-8') as f:
            records = f.readlines()
            print("records: ", records)
    return {
        "success": True,
        "sql_queries": [
            sql_query
        ]
    }


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=18080)
