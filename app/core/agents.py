import abc
import re
import sqlite3
import time

import openai
from core.const import SELECTOR_NAME, DECOMPOSER_NAME, REFINER_NAME, SYSTEM_NAME, selector_template, decompose_template_spider, decompose_template_bird, refiner_template, refiner_template_din
from core.llm import sqlcoder
from core.utils import parse_json, parse_sql_from_string, get_create_table_sqls, get_table_data, extract_foreign_keys
from core.tools.filter_schema_and_fk import apply_dictionary


class BaseAgent(metaclass=abc.ABCMeta):
    def __init__(self):
        pass

    @abc.abstractmethod
    def talk(self, message: dict):
        pass


class Selector(BaseAgent):
    """
    Get database description and if need, extract relative tables & columns
    """
    name = SELECTOR_NAME
    description = "Get database description and if need, extract relative tables & columns"

    def __init__(self, db_name, db_description, tables, table_info, llm):
        super().__init__()
        self.db_name = db_name
        self.db_description = db_description
        self.tables = tables
        self.table_info = table_info
        self.llm = llm
        self._message = {}

    def talk(self, message: dict):
        if message['send_to'] != self.name:
            return
        self._message = message
        create_table_sqls = get_create_table_sqls(self.tables, self.table_info)
        foreign_keys = extract_foreign_keys(create_table_sqls)
        foreign_keys_str = str()
        for table, fks in foreign_keys.items():
            foreign_keys_str += f"{table}: {fks}\n"
        if foreign_keys_str == "":
            foreign_keys_str = None
        prompt = selector_template.format(db_id=self.db_name, desc_str="".join(
            create_table_sqls), fk_str=foreign_keys_str, query=self._message['question'], evidence=None)
        print("prompt: \n", prompt)
        reply = self.llm.generate(prompt)
        print("reply: \n", reply)
        extracted_schema_dict = parse_json(reply)
        print("extracted_schema_dict: \n", extracted_schema_dict)
        modified_sql_commands, modified_foreign_keys = apply_dictionary(
            create_table_sqls, foreign_keys, extracted_schema_dict)

        print("modified_sql_commands: \n")
        for sql_command in modified_sql_commands:
            print(sql_command)
        print("modified_foreign_keys: \n", modified_foreign_keys)
        message['create_table_sqls'] = "".join(
            create_table_sqls)  # for refiner use
        message['foreign_keys_str'] = foreign_keys_str  # for refiner use
        message["modified_sql_commands"] = modified_sql_commands
        message["modified_foreign_keys"] = modified_foreign_keys
        message["send_to"] = DECOMPOSER_NAME


class Decomposer(BaseAgent):
    """
    Decompose the question and solve them using CoT
    """
    name = DECOMPOSER_NAME
    description = "Decompose the question and solve them using CoT"

    def __init__(self, db_name, db_description, tables, table_info, llm, prompt_type):
        super().__init__()
        self.db_name = db_name
        self.db_description = db_description
        self.tables = tables
        self.table_info = table_info
        self.llm = llm
        self.prompt_type = prompt_type
        self._message = {}

    def talk(self, message: dict):
        if message['send_to'] != self.name:
            return
        self._message = message
        foreign_keys_str = str()
        for table, fks in message["modified_foreign_keys"].items():
            foreign_keys_str += f"{table}: {fks}\n"
        if foreign_keys_str == "":
            foreign_keys_str = None
        prompt = ""
        if self.prompt_type == "spider":
            prompt = decompose_template_spider.format(desc_str="".join(
                message["modified_sql_commands"]), fk_str=foreign_keys_str, query=self._message['question'])
        else:
            prompt = decompose_template_bird.format(desc_str="".join(
                message["modified_sql_commands"]), fk_str=foreign_keys_str, query=self._message['question'], evidence=None)
        print("prompt: \n", prompt)
        reply = self.llm.generate(prompt)
        print("reply: \n", reply)

        res = ''
        qa_pairs = reply

        try:
            res = parse_sql_from_string(reply)
        except Exception as e:
            res = f'error: {str(e)}'
            print(res)
            time.sleep(1)

        message['final_sql'] = res
        message['qa_pairs'] = qa_pairs
        message['fixed'] = False
        message['send_to'] = REFINER_NAME


class Refiner(BaseAgent):
    name = REFINER_NAME
    description = "Execute SQL and preform validation"

    def __init__(self, db_name, db_description, tables, table_info, llm):
        super().__init__()
        self.db_name = db_name
        self.db_description = db_description
        self.tables = tables
        self.table_info = table_info
        self.llm = llm
        self.use_din_refiner = True
        self._message = {}

    def _create_mock_database(self):
        create_table_sqls = get_create_table_sqls(self.tables, self.table_info)
        table_data = get_table_data(self.tables, self.table_info)
        conn = sqlite3.connect(self.db_name)
        c = conn.cursor()

    def talk(self, message: dict):
        if message['send_to'] != self.name:
            return
        self._message = message
        prompt = ""
        if self.use_din_refiner:
            prompt = refiner_template_din.format(
                desc_str=self._message['create_table_sqls'], fk_str=self._message['foreign_keys_str'], query=self._message['question'], sql=message['final_sql'])
        else:
            print("Not implemented yet")
            return None
        print("prompt: \n", prompt)
        debugged_SQL = None
        while debugged_SQL is None:
            try:
                debugged_SQL = self.llm.debug(prompt)
            except openai.error.RateLimitError as error:
                print(
                    "===============Rate limit error for the classification module:", error)
                time.sleep(15)
            except Exception as error:
                print("===============Error in the refiner module:", error)
                pass
        print("Generated response:", debugged_SQL)
        SQL = None
        if debugged_SQL[:6] == "SELECT" or debugged_SQL[:7] == " SELECT":
            SQL = debugged_SQL
        elif debugged_SQL[:6] == "```sql" and debugged_SQL[-3:] == "```":
            SQL = debugged_SQL[7:-3]
        elif debugged_SQL[:6] == "```SQL" and debugged_SQL[-3:] == "```":
            SQL = debugged_SQL[7:-3]
        elif debugged_SQL[:3] == "```" and debugged_SQL[-3:] == "```":
            SQL = debugged_SQL[4:-3]
        else:
            print("Unrecognized format for the debugged SQL")
            SQL = parse_sql_from_string(debugged_SQL)
            if SQL[:5] == "error":
                SQL = message['generated_SQL']  # fallback to the generated SQL
        SQL = SQL.replace("\n", " ")
        SQL = SQL.replace("\t", " ")
        while "  " in SQL:
            SQL = SQL.replace("  ", " ")
        print("SQL after self-correction:", SQL)
        message['final_sql'] = SQL
        message['send_to'] = SYSTEM_NAME
