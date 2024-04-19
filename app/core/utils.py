import json
import re
from typing import Dict, List

# 获取建表语句
def get_create_table_sqls(tables, table_info):
    create_table_sqls = []
    for table in tables:
        cur_table_info = table_info[table]
        cur_create_table_sql = cur_table_info.split("/*")[0]
        create_table_sqls.append(cur_create_table_sql)
    return create_table_sqls

# 获取3条数据示例
def get_table_data(tables, table_info):
    table_data = {}
    for table in tables:
        cur_table_info = table_info[table]
        cur_data = cur_table_info.split("/*")[1].split("*/")[0].split("\n")[-3]
        table_data[table] = "\n".join(cur_data)
    return table_data

# check if valid format
def check_selector_response(json_data: Dict) -> bool:
    FLAGS = ['keep_all', 'drop_all']
    for k, v in json_data.items():
        if isinstance(v, str):
            if v not in FLAGS:
                print(f"error: invalid table flag: {v}\n")
                print(f"json_data: {json_data}\n\n")
                return False
        elif isinstance(v, list):
            pass
        else:
            print(f"error: invalid flag type: {v}\n")
            print(f"json_data: {json_data}\n\n")
            return False
    return True

def parse_json(text: str) -> dict:
    # 查找字符串中的 JSON 块
    start = text.find("```json")
    end = text.find("```", start + 7)
    
    # 如果找到了 JSON 块
    if start != -1 and end != -1:
        json_string = text[start + 7: end]
        
        try:
            # 解析 JSON 字符串
            json_data = json.loads(json_string)
            valid = check_selector_response(json_data)
            if valid:
                return json_data
            else:
                return {}
        except:
            print(f"error: parse json error!\n")
            print(f"json_string: {json_string}\n\n")
            pass
    
    return {}

def parse_sql_from_string(input_string):
    sql_pattern = r'```sql(.*?)```'
    all_sqls = []
    # 将所有匹配到的都打印出来
    for match in re.finditer(sql_pattern, input_string, re.DOTALL):
        all_sqls.append(match.group(1).strip())
    
    if all_sqls:
        return all_sqls[-1]
    else:
        return "error: No SQL found in the input string"