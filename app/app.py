import json
from flask import Flask, request
from langchain.sql_database import SQLDatabase
import os
from core.service import run_generation
from core.llm import sqlcoder, GPT, DeepSeek
app = Flask(__name__)

print("=============Starting service==============")
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
print("lengeth of table_info: ", len(table_info))

llm = sqlcoder()


@ app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


@ app.route("/predict", methods=["POST"])
def predict():
    content_type = request.headers.get("Content-Type")
    if content_type != "application/json":
        return {
            "success": False,
            "message": "Content-Type must be application/json"
        }
    print("request:", request)
    request_json = request.json
    print("request_json:", request_json)
    question = request_json.get("natural_language_query")
    print(f"Question: {question}")

    # sql_query = "SELECT ......"
    try:
        sql_query = run_generation(
            question, db_name, db_description, tables, table_info, llm)
    except Exception as e:
        print("Error: ", e)
        return {
            "success": False,
            "message": str(e)
        }
    return {
        "success": True,
        "sql_queries": [
            sql_query
        ]
    }


if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True, port=18080)
