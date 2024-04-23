from .prompt import BasePrompt
from nl2sql_hub.datasource import DataSource, get_url
from langchain.sql_database import SQLDatabase
from loguru import logger
import re


class OpenAIPrompt(BasePrompt):
    def __init__(self, datasource: DataSource, prompt_template: int | str):
        super().__init__(datasource, prompt_template)
        self.prompt_template = prompt_template
        self.datasource = datasource

        ds_url = get_url(datasource)
        logger.info(f"datasource url: {ds_url}")

        db_tool = SQLDatabase.from_uri(database_uri=ds_url)

        # 获取数据库类型
        self.db_type = db_tool.dialect
        logger.info(f"db type is {self.db_type}")

        # 获取表名
        self.table_names = db_tool.get_table_names()
        logger.info(f"table names is {self.table_names}")

        # 获取 table info
        self.table_info = db_tool.get_table_info()
        logger.info(f"table info is {self.table_info}")

        self.default_examples = self.build_default_examples()

    def build_default_examples(self):
        return [[f'请问{t}表中一共有多少条数据', f'select count(0) from {t};'] for t in self.table_names][0:3]

    @classmethod
    def name(cls):
        return 'openai'

    def build_prompt(self, query, examples=None, max_length=4096, **kwargs):
        if not examples:
            examples = self.default_examples

#         examples_txt = "\n".join([f"""{e[0]}
# 生成的sql:{e[1]}""" for e in examples])

#         prompt = f"""你将扮演一位 {self.db_type} 专家。根据我提供给你的表格和需求，给我生成能解决这个需求的SQL代码，你只需要返回给我SQL代码。
# 您只能查询回答问题所需的列。请用反引号 (`) 包裹每个列名，以表示它们是分隔标识符。
# 请注意只使用下面表中您能看到的列名。不要查询不存在的列。同时也要注意哪个列名在哪个表中。
# 如果问题涉及“今天”，请注意使用 CURDATE() 函数来获取当前日期。
# 你可以参考的一些例子为：
# {examples_txt}
# 现在，表格信息如下：
# {self.table_info}
# 我的需求是： {query}
# 你的回答格式应为：生成的sql:<生成的sql>\n解释：<解释>\n.
# 你的回答为："""

        examples_txt = "\n".join([f"""Question: {e[0]}
SQL:
```sql
{e[1]}
```""" for e in examples])

        prompt = f"""You are a {self.db_type} expert. Given an input question, create a syntactically correct {self.db_type} query.
Never query for all columns from a table. You must query only the columns that are needed to answer the question. Wrap each column name in backticks (`) to denote them as delimited identifiers.
Pay attention to use only the column names you can see in the tables below. Be careful to not query for columns that do not exist. Also, pay attention to which column is in which table.
Pay attention to use CURDATE() function to get the current date, if the question involves "today".

Use the following format:
Question: <question text>
SQL:
```sql
<your SQL query>
```
Only use the following tables:
{self.table_info}

Some examples of SQL queries that corrsespond to questions are:
{examples_txt}

Question: {query}
SQL:
```sql
"""
        return prompt

    def post_process(self, query, generated_sql: str, examples=None):
        sql = generated_sql
        # 如果上面的提取失败，则尝试提取以 SELECT（不区分大小写）开头，以 ; 结尾的片段
        # match = re.search(r"\bselect\b.*?;", generated_sql, re.DOTALL | re.IGNORECASE)
        # if match:
        #     return match.group(0).strip(" \t\n\r")

        logger.info(f'post process sql: {sql}')
        return sql
