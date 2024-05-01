from core.agents import Selector, Decomposer, Refiner
from core.agents_din import Schema_Linker, Classifier, Generator, Self_Corrector
from core.const import SELECTOR_NAME, DECOMPOSER_NAME, REFINER_NAME, SYSTEM_NAME, MAX_ROUND
from core.const_din import SCHEMA_LINKER, CLASSIFIER, GENERATOR, SELF_CORRECTOR, SYSTEM_NAME
from core.llm import sqlcoder, GPT, DeepSeek
import time


class ChatManager(object):
    def __init__(self, db_name, db_description, db_type, tables, table_info, prompt_type, llm):
        self.db_name = db_name
        self.db_description = db_description
        self.db_type = db_type
        self.tables = tables
        self.table_info = table_info
        # self.llm = sqlcoder()
        # self.llm = GPT()
        # self.llm = DeepSeek()
        self.llm = llm
        self.chat_group = [
            Selector(db_name, db_description, tables, table_info, self.llm),
            Decomposer(db_name, db_description, tables,
                       table_info, self.llm, prompt_type),
            Refiner(db_name, db_description, tables, table_info, self.llm)
        ]

    def _chat_single_round(self, message: dict):
        # we use `dict` type so value can be changed in the function
        for agent in self.chat_group:  # check each agent in the group
            if message['send_to'] == agent.name:
                agent.talk(message)

    def start(self, user_message):
        # we use `dict` type so value can be changed in the function
        start_time = time.time()
        # in the first round, pass message to prune
        if user_message['send_to'] == SYSTEM_NAME:
            user_message['send_to'] = SELECTOR_NAME
        for _ in range(MAX_ROUND):  # start chat in group
            self._chat_single_round(user_message)
            if user_message['send_to'] == SYSTEM_NAME:  # should terminate chat
                break
        end_time = time.time()
        exec_time = end_time - start_time
        print(f"\033[0;34mExecute {exec_time} seconds\033[0m", flush=True)
        return user_message


class ChatManager_DIN(object):
    def __init__(self, db_name, db_description, tables, table_info, prompt_type, llm, db_tool):
        self.db_name = db_name
        self.db_description = db_description
        self.tables = tables
        self.table_info = table_info
        # self.llm = sqlcoder()
        # self.llm = GPT()
        # self.llm = DeepSeek()
        self.llm = llm
        self.chat_group = [
            Schema_Linker(db_name, db_description, tables,
                          table_info, self.llm, db_tool),
            Classifier(db_name, db_description, tables,
                       table_info, self.llm),
            Generator(db_name, db_description, tables, table_info, self.llm),
            Self_Corrector(db_name, db_description,
                           tables, table_info, self.llm)
        ]

    def _chat_single_round(self, message: dict):
        # we use `dict` type so value can be changed in the function
        for agent in self.chat_group:  # check each agent in the group
            if message['send_to'] == agent.name:
                agent.talk(message)

    def start(self, user_message):
        # we use `dict` type so value can be changed in the function
        start_time = time.time()
        # in the first round, pass message to prune
        if user_message['send_to'] == SYSTEM_NAME:
            user_message['send_to'] = SCHEMA_LINKER
        for _ in range(MAX_ROUND):  # start chat in group
            self._chat_single_round(user_message)
            if user_message['send_to'] == SYSTEM_NAME:  # should terminate chat
                break
        end_time = time.time()
        exec_time = end_time - start_time
        print(f"\033[0;34mExecute {exec_time} seconds\033[0m", flush=True)
        return user_message
