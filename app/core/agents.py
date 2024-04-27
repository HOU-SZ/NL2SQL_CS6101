import abc
import re
import sqlite3
import time
from core.const import SELECTOR_NAME, DECOMPOSER_NAME, REFINER_NAME, SYSTEM_NAME, selector_template, decompose_template_spider, decompose_template_bird, refiner_template, refiner_template_din
from core.llm import sqlcoder
from core.utils import parse_json, parse_sql_from_string, get_create_table_sqls, get_table_data, extract_foreign_keys
# from core.tools.filter_schema_and_fk import apply_dictionary


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

    def apply_dictionary(self, sql_commands, foreign_keys, dictionary):
        modified_sql_commands = {}
        droped_tables = []
        droped_table_columns = {}

        for sql_command in sql_commands:
            table_name_match = ""
            if 'CREATE TABLE "' in sql_command:
                table_name_match = re.search(
                    r'CREATE TABLE "(.*?)"', sql_command)
            else:
                table_name_match = re.search(
                    r'CREATE TABLE (.*?)\s*\(', sql_command)
            if table_name_match:
                table_name = table_name_match.group(1)
                if table_name in dictionary:
                    if dictionary[table_name] == "keep_all":
                        modified_sql_commands[table_name] = sql_command
                    elif dictionary[table_name] == "drop_all":
                        # Drop the table and its foreign keys
                        if table_name in foreign_keys:
                            del foreign_keys[table_name]
                        droped_tables.append(table_name)
                    elif isinstance(dictionary[table_name], list):
                        # Keep only specified columns
                        columns_to_keep = set(dictionary[table_name])
                        lines = sql_command.split("\n")
                        new_lines = [lines[0]]  # Keep the CREATE TABLE line
                        for line in lines[1:]:
                            column_name_match = re.search(r'"(\w+)"', line)
                            if column_name_match and column_name_match.group(1) in columns_to_keep:
                                new_lines.append(line)
                            elif column_name_match and column_name_match.group(1) not in columns_to_keep:
                                if table_name not in droped_table_columns:
                                    droped_table_columns[table_name] = []
                                droped_table_columns[table_name].append(
                                    column_name_match.group(1))
                        new_lines.append(");")
                        modified_sql_commands[table_name] = "\n".join(
                            new_lines)
                else:
                    modified_sql_commands[table_name] = sql_command

        # Remove foreign keys constraints referencing dropped tables (right of the "=" sign)
        for table in droped_tables:
            for table_name, fks in foreign_keys.items():
                for fk in fks:
                    right_table = fk.split("=")[1].split(".")[0]
                    if right_table == table:
                        fks.remove(fk)
                # remove the command line form the corresponding create table command
                for table_name, sql_command in modified_sql_commands.items():
                    if table_name == table:
                        del modified_sql_commands[table_name]
                    elif "REFERENCES " + table in sql_command:
                        modified_sql_commands[table_name] = re.sub(
                            r'FOREIGN KEY\("(.*?)"\) REFERENCES ' + table + ' \("(.*?)"\)', '', sql_command)
                        modified_sql_commands[table_name] = re.sub(
                            r'\n\s*\n', '\n', modified_sql_commands[table_name])
                        modified_sql_commands[table_name] = re.sub(
                            r',\s*,', ',', modified_sql_commands[table_name])

        # Remove foreign keys constraints referencing columns that are not kept (left of the "=" sign)
        for table_name, fks in foreign_keys.items():
            for fk in fks:
                left_table = fk.split("=")[0].split(".")[0]
                left_column = fk.split("=")[0].split(".")[1]
                if left_table in dictionary and type(dictionary[left_table]) == list and left_column not in dictionary[left_table]:
                    fks.remove(fk)

        # Remove foreign keys constraints referencing columns that are not kept (right of the "=" sign)
        for table_name, fks in foreign_keys.items():
            for fk in fks:
                right_table = fk.split("=")[1].split(".")[0]
                right_column = fk.split("=")[1].split(".")[1]
                if right_table in dictionary and type(dictionary[right_table]) == list and right_column not in dictionary[right_table]:
                    fks.remove(fk)

        # Remove all unnecessary REFERENCES in the modified_sql_commands
        for table_name, droped_columns in droped_table_columns.items():
            for column in droped_columns:
                for table_name, sql_command in modified_sql_commands.items():
                    match_str_1 = "REFERENCES " + \
                        table_name + '("' + column + '")'
                    match_str_2 = "REFERENCES " + \
                        table_name + ' ("' + column + '")'
                    if match_str_1 in sql_command:
                        sql_command = sql_command.replace(match_str_1, '')
                    elif match_str_2 in sql_command:
                        sql_command = sql_command.replace(match_str_2, '')
                    modified_sql_commands[table_name] = sql_command
                    modified_sql_commands[table_name] = re.sub(
                        r'\n\s*\n', '\n', modified_sql_commands[table_name])
                    modified_sql_commands[table_name] = re.sub(
                        r',\s*,', ',', modified_sql_commands[table_name])
        return modified_sql_commands.values(), foreign_keys

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
        modified_sql_commands, modified_foreign_keys = self.apply_dictionary(
            create_table_sqls, foreign_keys, extracted_schema_dict)
        # modified_sql_commands, modified_foreign_keys = apply_dictionary(create_table_sqls, foreign_keys, extracted_schema_dict)
        # print("create_table_sqls: \n", create_table_sqls)
        # print("foreign_keys: \n", foreign_keys)
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
        reply = self.llm.debug(prompt)
        print("reply: \n", reply)
        message['final_sql'] = reply
        message['send_to'] = SYSTEM_NAME
