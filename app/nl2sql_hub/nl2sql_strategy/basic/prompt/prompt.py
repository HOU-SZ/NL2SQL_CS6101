from nl2sql_hub.datasource import DataSource, get_url, get_db_engine, DBEngine
from loguru import logger
from langchain.sql_database import SQLDatabase

prompt_templates = [
    # prompt 0
    f"请帮我将查询请求转换为对应的SQL执行语句。"
    f"SQL语句必须根据以下数据库中的信息:\n$DB_TXT$\n"
    f"你的SQL语句必须遵循$DB_TYPE$的语法规则。\n"
    f"$EXAMPLES$\n"
    f"查询：$QUERY$\n"
    f"SQL：",
    # prompt 1
    f"请帮我将查询请求转换为对应的SQL执行语句。"
    f"数据库信息如下:\n$DB_TXT$\n"
    f"该数据库为$DB_TYPE$数据库。\n"
    f"$EXAMPLES$\n"
    f"查询：$QUERY$\n"
    f"SQL：",
    # prompt 2
    f"我有一个$DB_TYPE$数据库，数据库的schema信息如下\n$DB_TXT$"
    f"帮我将查询请求转换为对应的SQL执行语句。"
    f"$EXAMPLES$\n"
    f"查询：$QUERY$\n"
    f"SQL：",
    # prompt 3
    f"请根据以下$DB_TYPE$数据库信息和需求帮我生成一个SQL查询语句：\n$DB_TXT$"
    f"$EXAMPLES$\n"
    f"查询：$QUERY$\n"
    f"SQL：",
    # 4 - sqlcoder prompt
    """### Task
Generate a SQL query to answer the following question:
`$QUERY$`

### Database Schema
This query will run on a $DB_TYPE$ database whose schema is represented in this string:
$DB_TXT_CODE$

### SQL

Follow these steps to create the SQL Query:
1. Only use the columns and tables present in the database schema
2. Use table aliases to prevent ambiguity when doing joins. For example, `SELECT table1.col1, table2.col1 FROM table1 JOIN table2 ON table1.id = table2.id`.

$EXAMPLES_CODE$

Given the database schema, here is the SQL query that answers `$QUERY$`:
```sql
""",
    # 5 - common code style prompt
    """/* Given the following $DB_TYPE$ database schema : */
$DB_TXT_CODE$

Complete $DB_TYPE$ SQL query only and with no explanation

$EXAMPLES_CODE$

/*  Answer the following: $QUERY$ */
SELECT""",
    # 6 - code style for nsql
    """$DB_TXT_CODE$
-- Using valid $DB_TYPE$, answer the following questions for the tables provided above.

$EXAMPLES_CODE$

-- $QUERY$

SELECT""",
    # 7 - chat2db https://github.com/chat2db/Chat2DB/blob/main/chat2db-server/chat2db-server-web/chat2db-server-web-api/src/main/java/ai/chat2db/server/web/api/controller/ai/TextGenerationController.java
    """### Instructions:
Your task is generate a SQL query according to the prompt, given a $DB_TYPE$ database schema.
Adhere to these rules:
- **Deliberately go through the prompt and database schema word by word** to appropriately answer the question
- **Use Table Aliases** to prevent ambiguity. For example, `SELECT table1.col1, table2.col1 FROM table1 JOIN table2 ON table1.id = table2.id`.

### Input:
Generate a SQL query according to the prompt `$QUERY$`.
This query will run on a database whose schema is represented in this string:
$DB_TXT_CODE$
$EXAMPLES_CODE$

### Response:
Based on your instructions, here is the SQL query I have generated to complete the prompt `$QUERY$`:
```sql
""",
    # 8 - langchain
    """You are a $DB_TYPE$ expert. Given an input question, first create a syntactically correct MySQL query to run, then look at the results of the query and return the answer to the input question.
You can order the results to return the most informative data in the database.
Never query for all columns from a table. You must query only the columns that are needed to answer the question. Wrap each column name in backticks (`) to denote them as delimited identifiers.
Pay attention to use only the column names you can see in the tables below. Be careful to not query for columns that do not exist. Also, pay attention to which column is in which table.
Pay attention to use CURDATE() function to get the current date, if the question involves "today".

Use the following format:

Question: Question here
SQLQuery: SQL Query to run
SQLResult: Result of the SQLQuery
Answer: Final answer here

Only use the following tables:
$DB_TXT_CODE$
$EXAMPLES_CODE$
Question: $QUERY$
""",
]


class BasePrompt:
    def __init__(self, datasource: DataSource, prompt_template: int | str):
        logger.info(f"init base prompt, prompt template is {prompt_template}")
        pass

    def build_prompt(self, query, examples=None, max_length=4096, **kwargs):
        raise NotImplementedError

    def post_process(self, query, generated_sql: str, examples=None):
        raise NotImplementedError

    @classmethod
    def name(cls):
        return NotImplementedError


class LegacyPrompt(BasePrompt):
    def __init__(self, datasource: DataSource, prompt_template: int | str):
        logger.info(f'init legacy prompt, prompt template is {prompt_template}')
        super().__init__(datasource, prompt_template)
        self.prompt_template = prompt_template
        self.datasource = datasource

        ds_url = get_url(datasource)
        logger.info(f"datasource url: {ds_url}")

        db_engine = get_db_engine(datasource)

        ds_tables = db_engine.fetch_tables_info(datasource.tables)
        logger.info(f"datasource tables: {ds_tables}")

        self.create_table_sqls = {t.table_name: t.create_table_sql for t in ds_tables}

        self.columns = {
            t.table_name: [c.name for c in t.columns] for t in ds_tables
        }
        self.config = {"use_cn": False, "db_type": self.datasource.driver}

    @classmethod
    def name(cls):
        return 'legacy'

    def build_prompt(self, query, examples=None, max_length=4096, **kwargs):
        used_tables = self.datasource.tables

        db_txt = self._get_db_txt(used_tables)

        # generate table DML for code-like prompts @chenqing
        db_txt_code = (
            "\n\n".join(
                self.create_table_sqls[table_name] for table_name in used_tables
            )
            if self.create_table_sqls
            else ""
        )
        if isinstance(self.prompt_template, int):
            prompt_template = self.prompt_template
            prompt = prompt_templates[prompt_template]
            examples_text = ""
            examples_text_code = ""
            if examples is not None and len(examples) > 0:
                while (
                        len(prompt)
                        + sum([len(example[0]) + len(example[1]) for example in examples])
                        > max_length
                ):
                    examples.pop()

                if prompt_template == 4:
                    examples_text_code = "Here are some examples:\n"
                elif prompt_template == 5:
                    examples_text_code = "/* Some example questions and corresponding SQL queries are provided based on similar problems : */\n"  # noqa
                elif prompt_template == 6:
                    examples_text_code = "-- Here are some examples:\n"
                elif prompt_template == 7:
                    examples_text_code = "\n### Examples:\n"
                elif prompt_template == 8:
                    examples_text_code = "\nSome examples of SQL queries that corrsespond to questions are:\n"
                for example in examples:
                    examples_text += "查询：" + example[0] + "\n"
                    examples_text += "SQL：" + example[1] + "\n"

                    if prompt_template == 4:
                        examples_text_code += f"Question: {example[0]}\n"
                        examples_text_code += f"```sql\n{example[1]}\n```\n"
                    elif prompt_template == 5:
                        examples_text_code += f"""/* Answer the following : {example[0]} */
            {example[1]}
            """
                    elif prompt_template == 6:
                        examples_text_code += f"""-- {example[0]}
            {example[1]} 
            """
                    elif prompt_template == 7:
                        examples_text_code += f"""prompt: `{example[0]}`
            ```sql
            {example[1]}
            ```
            """
                    elif prompt_template == 8:
                        examples_text_code += f"""Question: {example[0]}
SQLQuery: {' '.join(example[1].splitlines()).strip()}"""

            prompt = prompt.replace("$EXAMPLES$", examples_text)
            prompt = prompt.replace("$EXAMPLES_CODE$", examples_text_code)
            prompt = prompt.replace("$DB_TXT$", db_txt)
            prompt = prompt.replace("$DB_TXT_CODE$", db_txt_code)
            prompt = prompt.replace("$QUERY$", query)
            prompt = prompt.replace("$DB_TYPE$", self.config["db_type"])
            return prompt

    def post_process(self, query, generated_sql: str, examples=None):
        sql = generated_sql
        prompt_template = self.prompt_template
        if prompt_template == 0:
            sql = sql.split("SQL：")[-1]
        elif prompt_template == 4:
            sql = sql.split("```sql")[-1]
        elif prompt_template == 5 or prompt_template == 6:
            sql = "SELECT " + sql.split("SELECT")[-1]
        elif prompt_template == 8:
            sql = sql.split("SQLQuery:")[-1]
        sql = sql.strip(" \t\n\r")
        return sql

    def _get_db_txt(self, used_tables):
        db_txt = ""
        seen = set()
        new_used_tables = []
        for t in used_tables:
            if t not in seen:
                seen.add(t)
                new_used_tables.append(t)
        used_tables = new_used_tables

        for i, table in enumerate(used_tables):
            db_txt += f"表{i}:\n{table}\n"
            db_txt += f"列名:\n"
            for col in self.columns[table]:
                db_txt += f"{col},"
            db_txt += "\n"
        return db_txt
