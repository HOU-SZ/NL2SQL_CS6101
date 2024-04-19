from core.chat_manager import ChatManager
from core.const import SYSTEM_NAME


def init_message(question, db_name, db_description, tables, table_info):
    user_message = {
        "send_to": SYSTEM_NAME,
        "question": question,
        "db_name": db_name,
        "db_description": db_description,
        "tables": tables,
        "table_info": table_info
    }
    return user_message


def run_generation(question, db_name, db_description, tables, table_info):
    print("Start generating SQL query...")
    print("Question: ", question)
    print("Database name: ", db_name)
    print("Database description: ", db_description)
    print("Tables: ", tables)
    # print("Table info: ", table_info)

    prompt_type = "bird"
    chat_manager = ChatManager(db_name, db_description, tables, table_info, prompt_type)

    user_message = init_message(
        question, db_name, db_description, tables, table_info)
    user_message = chat_manager.start(user_message)
    SQL = user_message['final_sql']
    SQL = SQL.replace("\n", " ")
    SQL = SQL.replace("\t", " ")
    return SQL
