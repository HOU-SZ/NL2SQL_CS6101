from .prompt import BasePrompt
from nl2sql_hub.datasource import DataSource, get_url
from langchain.sql_database import SQLDatabase
from loguru import logger
import re

# follow https://github.com/ise-uiuc/magicoder/blob/main/src/magicoder/prompt_template.py
MAGICODER_PROMPT = """You are an exceptionally intelligent coding assistant that consistently delivers accurate and reliable responses to user instructions.

@@ Instruction
{instruction}

@@ Response
{response}"""

# Used to format the `{instruction}` part above
SRC_INSTRUCT_INSTRUCTION_PROMPT = """Write a solution to the following coding problem:
{problem}"""

# Used to format src-instruct data points
SRC_INSTRUCT_ILLUSTRATION_PROMPT = """[Problem]
{problem}

[Solution]
{solution}"""


class MagicoderPrompt(BasePrompt):
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
        return 'magicoder'

    def build_prompt(self, query, examples=None, max_length=4096, **kwargs):
        if not examples:
            examples = self.default_examples

        knowledge_txt = "\n".join(kwargs.get('knowledge_texts', []))

        examples_txt = "\n".join([f"""Question: {e[0]}
SQL:
```sql
{e[1]}
```""" for e in examples])

        prompt = f"""You are a {self.db_type} expert. Given an input question, create a syntactically correct {self.db_type} sql.
You must query only the columns that are needed to answer the question. Wrap each column name in backticks (`) to denote them as delimited identifiers.
Pay attention to use only the column names you can see in the tables below. Be careful to not query for columns that do not exist. Also, pay attention to which column is in which table.
Pay attention to use CURDATE() function to get the current date, if the question involves "today".
YOU MUST give a sql query to answer the question.

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
{"Some knowledge about the database:" if knowledge_txt else ""}
{knowledge_txt if knowledge_txt else ""}
Question: {query}
SQL:
```sql
"""

        instructed_prompt = MAGICODER_PROMPT.format(instruction=prompt, response="")

        # return instructed_prompt
        return prompt

    def post_process(self, query, generated_sql: str, examples=None):
        """
        尽量不通过 stop word [```, Question] 来控制，因为模型有时候会将问题重复一遍，导致输出是空的
        """
        generated_sql = generated_sql.strip()

        if not generated_sql:
            return ''
        # 不加 stop words 的情况下，可能出现几种情况：
        # 1. 完全 follow instruction，接着我们给的 ```sql\n 开始
        # 2. 1 基础上有后面有重复的Question
        # 3. 直接从 Question 开始，并且第一个不是我们的提问问题
        # 4. 前面有一些无关的文字，然后开始 ```sql 给出答案
        # 5. 其他

        if query in generated_sql:
            generated_sql: str = generated_sql.split(query)[1].strip()
        # 此时最开始的应该是 SQL:
        if generated_sql.startswith("SQL:"):
            generated_sql = generated_sql.split("SQL:")[1].strip()
        if generated_sql.startswith("```sql"):
            generated_sql = generated_sql.split("```sql")[1].strip()
        if generated_sql.lower().startswith("select"):
            generated_sql = generated_sql.split('```')[0].strip()
            if not generated_sql.endswith(';') and 'Question:':
                generated_sql = generated_sql.split('Question:')[0].strip()
        else:
            generated_sql = generated_sql.split('```sql')[-1].strip().split('```')[0].strip()
        sql = generated_sql
        logger.info(f'post process sql: {sql}')
        return sql
