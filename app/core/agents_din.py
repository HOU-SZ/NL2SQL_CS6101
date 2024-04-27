import re
import time
from core.agents import BaseAgent
from core.tools.filter_schema_and_fk import apply_dictionary
from core.utils import get_create_table_sqls, extract_foreign_keys
from core.const_din import SCHEMA_LINKER, CLASSIFIER, GENERATOR, REFINER, SYSTEM_NAME, schema_linking_prompt, classification_prompt, easy_prompt, medium_prompt, hard_prompt, refiner_prompt
import openai


class Schema_Linker(BaseAgent):
    name = SCHEMA_LINKER

    def __init__(self, db_name, db_description, tables, table_info, llm, db_tool):
        super().__init__()
        self.db_name = db_name
        self.db_description = db_description
        self.tables = tables
        self.table_info = table_info
        self.llm = llm
        self._message = {}
        self.db_tool = db_tool

    def get_table_columns(self, db_tool, tables, table_info):
        db_columns_context = ""
        for table in db_tool._metadata.sorted_tables:
            print(table)
            single_table_context = f"Table {table}, columns = [*, "
            columns = []
            for k, v in table._columns.items():
                columns.append(k)
            single_table_context += ", ".join(columns) + "]"
            db_columns_context += single_table_context + "\n"
        return db_columns_context

    def get_foreign_keys(self, foreign_keys):
        foreign_keys_context = "Foreign_keys = ["
        for k, v in foreign_keys.items():
            foreign_keys_context += ", ".join(v) + ", "
        foreign_keys_context += "]"
        return foreign_keys_context

    def generate_filter_dictorionary(self, db_tool, schema_links):
        schema_links = schema_links[1:-1]
        schema_links = schema_links.split(",")
        schema_links_dict = {}
        for link in schema_links:
            link = link.strip()
            if "." in link and "=" not in link:
                table, column = link.split(".")
                if column == "*":
                    continue
                if table in schema_links_dict:
                    schema_links_dict[table].append(column)
                else:
                    schema_links_dict[table] = [column]
            elif "=" in link:
                link_1, link_2 = link.split("=")
                link_1.replace(" ", "")
                link_2.replace(" ", "")
                table_1, column_1 = link_1.split(".")
                table_2, column_2 = link_2.split(".")
                if table_1 in schema_links_dict:
                    schema_links_dict[table_1].append(column_1)
                else:
                    schema_links_dict[table_1] = [column_1]
                if table_2 in schema_links_dict:
                    schema_links_dict[table_2].append(column_2)
                else:
                    schema_links_dict[table_2] = [column_2]
        print("schema_links_dict: ", schema_links_dict)
        for table in db_tool._metadata.sorted_tables:
            if table.name not in schema_links_dict:
                schema_links_dict[table.name] = "drop_all"
            elif len(schema_links_dict[table.name]) == len(table._columns.items()):
                schema_links_dict[table.name] = "keep_all"
        print("schema_links_dict: ", schema_links_dict)
        return schema_links_dict

    def talk(self, message):
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

        instruction = "### Task: Find the schema_links for generating SQL queries for each question based on the database schema and Foreign keys.\n"
        instruction += "/* Some example questions and corresponding schema_links are provided: */\n"
        instruction += schema_linking_prompt
        question_instruction = "/* Given the following database schema and Foreign keys: */\n"
        question_instruction += self.get_table_columns(
            self.db_tool, self.tables, self.table_info)
        question_instruction += self.get_foreign_keys(foreign_keys)
        question_instruction += "\n/* Please provide the correct schema_link for generating SQL query for the following question. Please DO NOT include any SQL keyword in the generated schema_link! */\n"
        question_instruction += f"Q: {message['question']}" + \
            """"\nA: Let\'s think step by step."""
        prompt = instruction + question_instruction
        print("prompt: \n", prompt)
        reply = self.llm.generate(prompt)
        print("reply: \n", reply)
        try:
            schema_links = reply.split("Schema_links: ")[1]
        except Exception as e:
            print("=============Slicing error in schema linker: ", e)
            schema_links = "[]"
        if schema_links == "[]":
            try:
                schema_links = reply.split("schema_links: ")[1]
            except Exception as e:
                print("=============Slicing error in schema linker: ", e)
                schema_links = "[]"
        print("schema_links: ", schema_links)
        extracted_schema_dict = self.generate_filter_dictorionary(
            self.db_tool, schema_links)
        modified_sql_commands, modified_foreign_keys = apply_dictionary(
            create_table_sqls, foreign_keys, extracted_schema_dict)
        print("modified_sql_commands: \n")
        for sql_command in modified_sql_commands:
            print(sql_command)
        print("modified_foreign_keys: \n", modified_foreign_keys)
        message['create_table_sqls'] = "".join(
            create_table_sqls)  # for refiner use
        message['foreign_keys_str'] = foreign_keys_str  # for refiner use
        message["modified_sql_commands"] = "".join(modified_sql_commands)
        message["modified_foreign_keys"] = modified_foreign_keys
        message['schema_link'] = schema_links
        message['send_to'] = CLASSIFIER


class Classifier(BaseAgent):
    name = CLASSIFIER

    def __init__(self, db_name, db_description, tables, table_info, llm):
        super().__init__()
        self.db_name = db_name
        self.db_description = db_description
        self.tables = tables
        self.table_info = table_info
        self.llm = llm
        self._message = {}

    def talk(self, message):
        if message['send_to'] != self.name:
            return
        self._message = message
        instruction = "### Task: For the given question, classify it as EASY, NON-NESTED, or NESTED based on nested queries and JOIN.\n"
        instruction += "\nif need nested queries: predict NESTED\n"
        instruction += "elif need JOIN and don't need nested queries: predict NON-NESTED\n"
        instruction += "elif don't need JOIN and don't need nested queries: predict EASY\n\n"
        instruction += "/* Some example questions and corresponding Label are provided: */\n"
        instruction += classification_prompt
        question_instruction = "/* Please provide the correct classification label for the following question: */\n"
        question_instruction += f"Q: {message['question']}\n"
        question_instruction += f"Schema_links: {message['schema_link']}\n"
        question_instruction += "A: Let\'s think step by step."
        prompt = instruction + question_instruction
        # TODO: add database schema and foreign keys in the prompt
        print("prompt: \n", prompt)
        reply = self.llm.generate(prompt)
        print("reply: \n", reply)
        try:
            classification = reply.split("Label: ")[1]
        except Exception as e:
            print("=============Slicing error in classifier: ", e)
            classification = '"NESTED"'
        print("classification: ", classification)
        sub_questions = None
        if classification == '"NESTED"':
            try:
                sub_questions = reply.split('questions = ["')[1].split('"]')[0]
                print("Sub-questions:", sub_questions)
            except Exception as error:
                print("Slicing error for the sub_questions:", error)

        message['classification'] = classification
        message['sub_questions'] = sub_questions
        message['send_to'] = GENERATOR


class Generator:
    name = GENERATOR

    def __init__(self, db_name, db_description, tables, table_info, llm):
        super().__init__()
        self.db_name = db_name
        self.db_description = db_description
        self.tables = tables
        self.table_info = table_info
        self.llm = llm
        self._message = {}

    def easy_prompt(self, message):
        instruction = "### Task: Use the schema links to generate the SQL queries for the question.\n\n"
        instruction += "/* Some example questions and corresponding SQL queries are provided: */\n"
        instruction += easy_prompt
        question_instruction = "/* Given the following database schema: */\n"
        question_instruction += message['modified_sql_commands']
        question_instruction += "\n/* Please provide the correct SQL query for the following question: */\n"
        question_instruction += f"Q: {message['question']}\n"
        question_instruction += f"Schema_links: {message['schema_link']}\n"
        question_instruction += "SQL:"
        return instruction + question_instruction

    def medium_prompt(self, message):
        instruction = "### Task: Use the schema links to generate the SQL queries for the question.\n\n"
        instruction += "/* Some example questions and corresponding SQL queries are provided: */\n"
        instruction += medium_prompt
        question_instruction = "/* Given the following database schema: */\n"
        question_instruction += message['modified_sql_commands']
        question_instruction += "\n/* Please provide the correct SQL query for the following question: */\n"
        question_instruction += f"Q: {message['question']}\n"
        question_instruction += f"Schema_links: {message['schema_link']}\n"
        question_instruction += "A: Let\'s think step by step."
        return instruction + question_instruction

    def hard_prompt(self, message):
        instruction = "### Task: Use the intermediate representation and the schema links to generate the SQL queries for the question. The answer may involves nested or set operations such as EXCEPT, UNION, IN, and INTERSECT, or JOIN multiple tables. So to solve the question, you need to decompose the question into sub-questions first, and generate sub-queries for the sub-questions one by one. Then you need to generate a pseudo-SQL as an intermediate representation for the question. Finally, based on the sub-queries and the intermediate representation, generate the final SQL.\n\n"
        instruction += "/* Some example questions and corresponding SQL queries are provided: */\n"
        instruction += hard_prompt
        stepping = f'''\nA: Let's think step by step. "{message['question']}" can be solved by knowing the answer to the following sub-question "{message['sub_questions']}".'''
        question_instruction = "/* Given the following database schema: */\n"
        question_instruction += message['modified_sql_commands']
        question_instruction += "\n/* Please provide the correct SQL query for the following question: */\n"
        question_instruction += f"Q: {message['question']}\n"
        question_instruction += f"Schema_links: {message['schema_link']}\n"
        question_instruction += stepping
        question_instruction += '\nThe SQL query for the sub-question"'
        return instruction + question_instruction

    def talk(self, message):
        if message['send_to'] != self.name:
            return
        self._message = message
        if message['classification'] == '"EASY"':
            prompt = self.easy_prompt(message)
            print("prompt: \n", prompt)
            generated_SQL = None
            while generated_SQL is None:
                try:
                    generated_SQL = self.llm.generate(prompt)
                except openai.error.RateLimitError as error:
                    print(
                        "===============Rate limit error for the classification module:", error)
                    time.sleep(15)
                except Exception as error:
                    print("===============Error in the easy module:", error)
                    pass
        elif message['classification'] == '"NON-NESTED"':
            prompt = self.medium_prompt(message)
            print("prompt: \n", prompt)
            generated_SQL = None
            SQL = "SELECT"
            while generated_SQL is None:
                try:
                    generated_SQL = self.llm.generate(prompt)
                except openai.error.RateLimitError as error:
                    print(
                        "===============Rate limit error for the classification module:", error)
                    time.sleep(15)
                except Exception as error:
                    print("===============Error in the medium module:",
                          error)
                    pass
            print("Generated response:", generated_SQL)
            try:
                SQL = generated_SQL.split("SQL:")[1]
            except Exception as error:
                print(
                    "===============SQL slicing error for the medium module")
                SQL = "SELECT"
            if SQL == "SELECT":
                try:
                    SQL = re.split("SQL Query:", generated_SQL,
                                   flags=re.IGNORECASE)[1]
                except Exception as error:
                    print(
                        "===============SQL slicing error for the medium module")
                    SQL = "SELECT"
            if SQL == "SELECT":
                try:
                    # SQL = generated_SQL.split(
                    #     "Intermediate_representation:")[1]
                    SQL = re.split("Intermediate_representation:",
                                   generated_SQL, flags=re.IGNORECASE)[1]
                except Exception as error:
                    print(
                        "===============SQL slicing error for the medium module")
                    SQL = "SELECT"
            if SQL == "SELECT":
                try:
                    SQL = re.split(":", generated_SQL, flags=re.IGNORECASE)[-1]
                except Exception as error:
                    print(
                        "===============SQL slicing error for the medium module")
                    SQL = "SELECT"
            if SQL == "SELECT":
                SQL = generated_SQL
            generated_SQL = SQL
        elif message['classification'] == "NESTED":
            prompt = self.hard_prompt(message)
            print("prompt: \n", prompt)
            generated_SQL = None
            while generated_SQL is None:
                try:
                    generated_SQL = self.llm.generate(prompt)
                except openai.error.RateLimitError as error:
                    print(
                        "===============Rate limit error for the classification module:", error)
                    time.sleep(15)
                except Exception as error:
                    print("===============Error in the hard module:",
                          error)
                    pass
            print("Generated response:", generated_SQL)
            try:
                SQL = generated_SQL.split("SQL: ")[1]
            except Exception as error:
                print("===============SQL slicing error for the hard module")
                SQL = "SELECT"
            if SQL == "SELECT":
                try:
                    SQL = re.split("SQL Query:", generated_SQL,
                                   flags=re.IGNORECASE)[1]
                except Exception as error:
                    print(
                        "===============SQL slicing error for the hard module")
                    SQL = "SELECT"
            if SQL == "SELECT":
                try:
                    SQL = re.split("Intermediate_representation:",
                                   generated_SQL, flags=re.IGNORECASE)[1]
                except Exception as error:
                    print(
                        "===============SQL slicing error for the hard module")
                    SQL = "SELECT"
            if SQL == "SELECT":
                try:
                    SQL = re.split(":", generated_SQL, flags=re.IGNORECASE)[-1]
                except Exception as error:
                    print(
                        "===============SQL slicing error for the hard module")
                    SQL = "SELECT"
            if SQL == "SELECT":
                SQL = generated_SQL
            generated_SQL = SQL
        print("Generated SQL:", generated_SQL)
        self._message['generated_SQL'] = generated_SQL
        self._message['send_to'] = REFINER


class Refiner(BaseAgent):
    name = REFINER

    def __init__(self, db_name, db_description, tables, table_info, llm):
        super().__init__()
        self.db_name = db_name
        self.db_description = db_description
        self.tables = tables
        self.table_info = table_info
        self.llm = llm
        self.use_din_refiner = True
        self._message = {}

    def talk(self, message: dict):
        if message['send_to'] != self.name:
            return
        self._message = message
        prompt = ""
        if self.use_din_refiner:
            prompt = refiner_prompt.format(
                desc_str=self._message['create_table_sqls'], fk_str=self._message['foreign_keys_str'], query=self._message['question'], sql=message['generated_SQL'])
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
        if debugged_SQL[:6] == "SELECT":
            SQL = debugged_SQL
        elif debugged_SQL[:6] == "```sql" and debugged_SQL[-3:] == "```":
            SQL = debugged_SQL[7:-3]
        elif debugged_SQL[:6] == "```SQL" and debugged_SQL[-3:] == "```":
            SQL = debugged_SQL[7:-3]
        elif debugged_SQL[:3] == "```" and debugged_SQL[-3:] == "```":
            SQL = debugged_SQL[4:-3]
        else:
            print("Unrecognized format for the debugged SQL")
        SQL = SQL.replace("\n", " ")
        SQL = SQL.replace("\t", " ")
        while "  " in SQL:
            SQL = SQL.replace("  ", " ")
        print("SQL after self-correction:", SQL)
        message['final_sql'] = SQL
        message['send_to'] = SYSTEM_NAME
