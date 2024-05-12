import abc
import re
import sqlite3
import time
import random

import openai
from core.const import SELECTOR_NAME, DECOMPOSER_NAME, REFINER_NAME, FIELD_EXTRACTOR_NAME, SYSTEM_NAME, selector_template, decompose_template_spider, decompose_template_bird, refiner_template, refiner_template_din, field_extractor_template, new_field_extractor_template, new_decompose_template
from core.llm import modelhub_qwen1_5_72b_chat, GPT
from core.utils import parse_json, parse_sql_from_string, get_create_table_sqls, get_table_data, extract_foreign_keys
from core.tools.filter_schema_and_fk import apply_dictionary
from core.tools.extract_comments import extract_comments
from core.tools.get_table_and_columns import get_table_and_columns_by_fuzzy_similarity, get_table_and_columns_by_similarity
from sentence_transformers import SentenceTransformer


class BaseAgent(metaclass=abc.ABCMeta):
    def __init__(self):
        pass

    @abc.abstractmethod
    def talk(self, message: dict):
        pass


class FieldExtractor(BaseAgent):
    """
    Extract fields from the question
    """
    name = FIELD_EXTRACTOR_NAME
    description = "Extract fields from the question"

    def __init__(self, db_name, db_description, tables, table_info, llm):
        super().__init__()
        self.db_name = db_name
        self.db_description = db_description
        self.tables = tables
        self.table_info = table_info
        self.llm = modelhub_qwen1_5_72b_chat()
        self._message = {}

    def talk(self, message: dict):
        if message['send_to'] != self.name:
            return
        self._message = message
        prompt = new_field_extractor_template.format(
            question=self._message['question'])
        # print("prompt: \n", prompt)
        reply = self.llm.generate(prompt)
        print("FieldExtractor reply: \n", reply)
        start = reply.find("[")
        end = reply.find("]")
        reply = reply[start+1:end]
        fields = re.findall(r"[\w]+", reply)
        # 如果能够从database schema中获取到foreign key信息，那么不需要下面的处理。下面的处理只是为了在没有foreign key信息的情况下，尽量提高JOIN的准确性。
        # 优化完apply_dictionary之后，不再需要下面的处理
        # If the target fields includes 公司名称, please also add 股票代码 and 证券代码 to the target fields.
        # if '公司名称' in fields:
        #     if '股票代码' not in fields:
        #         fields.append('股票代码')
        #     if '证券代码' not in fields:
        #         fields.append('证券代码')
        # # If the target fields includes 股票代码, please also add 证券代码 to the target fields.
        # if '股票代码' in fields:
        #     if '证券代码' not in fields:
        #         fields.append('证券代码')
        # # If the target fields includes 证券代码, please also add 股票代码 to the target fields.
        # if '证券代码' in fields:
        #     if '股票代码' not in fields:
        #         fields.append('股票代码')
        print("fields: \n", fields)
        message['fields'] = fields
        message['send_to'] = SELECTOR_NAME


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
        # print("prompt: \n", prompt)
        reply = self.llm.generate(prompt)
        print("Selector reply: \n", reply)
        extracted_schema_dict = parse_json(reply)
        print("extracted_schema_dict: \n", extracted_schema_dict)
        # supplement the schema with the extracted fileds from the question
        comments, comments_list = extract_comments(create_table_sqls)
        # get the table and columns by similarity (SentenceTransformer)
        # embedder = SentenceTransformer('./sbert-base-chinese-nli')
        # results, selected_tables_and_columns = get_table_and_columns_by_similarity(
        #     embedder, message['fields'], comments_list)

        # get the table and columns by fuzzy similarity
        results, selected_tables_and_columns = get_table_and_columns_by_fuzzy_similarity(
            message['fields'], comments_list)
        print("table_and_columns: \n", selected_tables_and_columns)
        if selected_tables_and_columns is None or len(selected_tables_and_columns) == 0:
            print(
                "selected_tables_and_columns is None or empty, fallback to the original schema")
            selected_tables_and_columns = []
        for item in selected_tables_and_columns:
            lst = item.split(".")
            table_name = lst[0]
            column_name = lst[1]
            if table_name in extracted_schema_dict:
                if extracted_schema_dict[table_name] == "drop_all":
                    extracted_schema_dict[table_name] = [column_name]
                elif extracted_schema_dict[table_name] == "keep_all":
                    continue
                elif type(extracted_schema_dict[table_name]) == list:
                    extracted_schema_dict[table_name].append(column_name)
            else:
                extracted_schema_dict[table_name] = [column_name]
        print("\nextracted_schema_dict after supplement: \n", extracted_schema_dict)

        modified_sql_commands, modified_foreign_keys = apply_dictionary(
            create_table_sqls, foreign_keys, extracted_schema_dict)
        if modified_sql_commands is None or len(modified_sql_commands) == 0:
            print(
                "modidied_sql_commands is None or empty, fallback to the original schema")
            modified_sql_commands = create_table_sqls
            modified_foreign_keys = foreign_keys
        print("modified_sql_commands: \n")
        for sql_command in modified_sql_commands:
            print(sql_command)
        print("modified_foreign_keys: \n", modified_foreign_keys)
        message['extracted_schema_dict'] = extracted_schema_dict
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

    def __init__(self, db_name, db_description, tables, table_info, table_column_values_dict, llm, prompt_type):
        super().__init__()
        self.db_name = db_name
        self.db_description = db_description
        self.tables = tables
        self.table_info = table_info
        self.llm = llm
        self.table_column_values_dict = table_column_values_dict
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
        # original din prompt
        # if self.prompt_type == "spider":
        #     prompt = decompose_template_spider.format(db_type=self._message['db_type'], desc_str="".join(
        #         message["modified_sql_commands"]), fk_str=foreign_keys_str, query=self._message['question'])
        # else:
        #     prompt = decompose_template_bird.format(db_type=self._message['db_type'], desc_str="".join(
        #         message["modified_sql_commands"]), fk_str=foreign_keys_str, query=self._message['question'], evidence=None)

        # new din prompt
        # build example values
        example_values = {}
        extracted_schema_dict = message['extracted_schema_dict']
        for table, columns in extracted_schema_dict.items():
            if type(columns) == str and columns == "drop_all":
                continue
            if type(columns) == str and columns == "keep_all":
                for key in self.table_column_values_dict.keys():
                    if key.startswith(table):
                        len_values = len(self.table_column_values_dict[key])
                        if len_values < 10:
                            example_values[key] = self.table_column_values_dict[key]
                        else:
                            example_values[key] = random.sample(
                                self.table_column_values_dict[key], 10)
            else:
                for column in columns:
                    table_column = f"{table}.{column}"
                    if table_column in self.table_column_values_dict:
                        len_values = len(self.table_column_values_dict[key])
                        if len_values < 10:
                            example_values[key] = self.table_column_values_dict[key]
                        else:
                            example_values[key] = random.sample(
                                self.table_column_values_dict[key], 10)
        prompt = new_decompose_template.format(
            db_type=self._message['db_type'], desc_str="".join(message["modified_sql_commands"]), fk_str=foreign_keys_str, query=self._message['question'], example_values=example_values)

        print("prompt: \n", prompt)
        reply = self.llm.generate(prompt)
        print("Decomposer reply: \n", reply)

        res = ''
        qa_pairs = reply

        try:
            res = parse_sql_from_string(reply)
        except Exception as e:
            res = f'error: {str(e)}'
            print(res)
            time.sleep(1)
        if res[:5] == "error":
            res = None

        message['generated_SQL'] = res
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
        foreign_keys_str = str()
        for table, fks in message["modified_foreign_keys"].items():
            foreign_keys_str += f"{table}: {fks}\n"
        if foreign_keys_str == "":
            foreign_keys_str = None
        prompt = ""
        if self.use_din_refiner:
            prompt = refiner_template_din.format(
                db_type=self._message['db_type'], desc_str="".join(
                    message["modified_sql_commands"]), fk_str=foreign_keys_str, query=self._message['question'], sql=message['generated_SQL'])
        else:
            print("Not implemented yet")
            return None
        # print("prompt: \n", prompt)
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
        print("Refiner reply:", debugged_SQL)
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
            SQL = parse_sql_from_string(debugged_SQL)
            if SQL[:5] == "error":
                print(
                    "Unrecognized format for the debugged SQL, fallback to the generated SQL")
                SQL = message['generated_SQL']  # fallback to the generated SQL
        SQL = SQL.replace("\n", " ")
        SQL = SQL.replace("\t", " ")
        SQL = SQL.replace("`", "")
        while "  " in SQL:
            SQL = SQL.replace("  ", " ")
        SQL = SQL.strip()
        if SQL[-1] != ";":
            SQL += ";"  # add a semicolon at the end
        print("SQL after self-correction:", SQL)
        message['final_sql'] = SQL
        message['send_to'] = SYSTEM_NAME
