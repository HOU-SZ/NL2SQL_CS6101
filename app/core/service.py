from app.core.tools.fix_column_names import fix_sql
from core.chat_manager import ChatManager, ChatManager_DIN
from core.const import SYSTEM_NAME


def init_message(question, db_name, db_description, db_type, tables, table_info):
    user_message = {
        "send_to": SYSTEM_NAME,
        "question": question,
        "db_name": db_name,
        "db_description": db_description,
        "db_type": db_type,
        "tables": tables,
        "table_info": table_info
    }
    return user_message


def run_generation_mac(question, db_name, db_description, db_type, tables, table_info, column_values_dict, llm):
    print("Start generating SQL query...")
    print("Database name: ", db_name)
    print("Database description: ", db_description)
    print("Database type: ", db_type)
    print("Tables: ", tables)
    # print("Table info: ", table_info)

    prompt_type = "bird"
    chat_manager = ChatManager(
        db_name, db_description, db_type, tables, table_info, prompt_type, llm)

    user_message = init_message(
        question, db_name, db_description, db_type, tables, table_info)
    user_message = chat_manager.start(user_message)
    SQL = user_message['final_sql']
    SQL = SQL.replace("\n", " ")
    SQL = SQL.replace("\t", " ")
    SQL = fix_sql(SQL, column_values_dict)
    return SQL


def run_genration_din(question, db_name, db_description, tables, table_info, llm, db_tool):
    print("Start generating SQL query...")
    print("Question: ", question)
    print("Database name: ", db_name)
    print("Database description: ", db_description)
    print("Tables: ", tables)
    # print("Table info: ", table_info)

    prompt_type = "din"
    chat_manager = ChatManager_DIN(
        db_name, db_description, tables, table_info, prompt_type, llm, db_tool)

    user_message = init_message(
        question, db_name, db_description, tables, table_info)
    user_message = chat_manager.start(user_message)
    SQL = user_message['final_sql']
    SQL = SQL.replace("\n", " ")
    SQL = SQL.replace("\t", " ")
    return SQL
