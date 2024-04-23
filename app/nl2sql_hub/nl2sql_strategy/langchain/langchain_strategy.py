import os
from typing import List
from pydantic import BaseModel
import requests
import json
import openai
from nl2sql_hub.datasource import DataSource
from nl2sql_hub.datasource import get_url
from nl2sql_hub.inference.args import InferenceArgs
from nl2sql_hub.inference.adapter import (
    BaseInferenceAdapter,
    TGIInferenceAdapter,
    OpenAIInferenceAdapter,
    get_inference_adapter,
)
from nl2sql_hub.nl2sql_strategy.abstract_strategy import AbstractNL2SQLStrategy
from nl2sql_hub.nl2sql_strategy.langchain.tool import CustomSQLDatabaseToolkit

from loguru import logger
from langchain.agents import create_sql_agent
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.sql_database import SQLDatabase
from langchain.llms.openai import OpenAI
from langchain.agents import AgentExecutor
from langchain.agents.agent_types import AgentType
from langchain.chat_models import ChatOpenAI, AzureChatOpenAI
from langchain.agents.agent_toolkits import create_retriever_tool
from langchain.schema import BaseRetriever, Document


class ExamplesRetriever(BaseRetriever, BaseModel):
    k = 3
    scene_id: int = int(os.getenv("SCENE_ID", "0"))

    class Config:
        arbitrary_types_allowed = True

    def get_relevant_documents(self, query: str) -> List[Document]:
        task_service_url = os.getenv("TASK_SERVICE_URL")
        url = f"{task_service_url}/api/v1/findExamples"
        data = {
            "natural_language_query": query,
            "limit_num": self.k,
            "scene_id": self.scene_id,
        }
        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(url, headers=headers, data=json.dumps(data))
            examples = response.json()
            return examples[: self.k]
        except Exception as e:
            logger.error(f"retrival examples error: {e}", exc_info=True)
            return []


def process_args(args: dict):
    if args is None:
        return {}
    config = {"use_example": args.get("use_example", True)}
    return config


class LangchainStrategy(AbstractNL2SQLStrategy):
    def __init__(self, inference_args: InferenceArgs):
        self.inference_args = inference_args

        self.strategy_args = process_args(inference_args.strategy_args)

        self.datasource: DataSource = inference_args.datasource

        self.create_table_sqls = {
            t.table_name: t.create_table_sql for t in self.datasource.tables
        }
        # table names
        self.used_tables = [t.table_name for t in self.datasource.tables]
        # column names
        self.columns = {
            t.table_name: [c.name for c in t.columns] for t in self.datasource.tables
        }

        self.inference_helper: BaseInferenceAdapter = get_inference_adapter(
            inference_args.model_type,
            model_url=inference_args.model_url,
            max_new_tokens=inference_args.max_new_tokens,
            # noqa
            temperature=inference_args.temperature,
            stop_words=inference_args.stop_words,
            openai_mode=inference_args.openai_mode,
            model_name=inference_args.model_name,
        )

        # TODO: get task service url from config
        self.task_service_url = os.getenv(
            "TASK_SERVICE_URL", None
        )
        self.scene_id = int(os.getenv("SCENE_ID", "0"))

        db_url = get_url(self.datasource)
        logger.info(f"db_url: {db_url}")
        self.db = SQLDatabase.from_uri(database_uri=db_url)

        SQL_PREFIX = """You are an agent designed to create a syntactically correct {dialect} sql query for user input.
Given an input question, create a syntactically correct {dialect} sql query to run, then return the sql as answer.
Never generate sql query for all the columns from a specific table, only ask for the relevant columns given the question.
You have access to tools for interacting with the database to check if sql is correct.
Only use the below tools. Only use the information returned by the below tools to generate sql.
YOU MUST executing sql BEFORE return the sql query.
YOU MUST return sql, DON'T return the execution result.
You MUST double check your query before executing it. If you get an error while executing a query, rewrite the query and try again.

DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.

If the question does not seem related to the database, just return "I don't know" as the answer.
"""

        if openai.api_type and openai.api_type.startswith("azure"):
            llm = AzureChatOpenAI(
                temperature=0.0,
                deployment_name=os.environ.get("OPENAI_AZURE_DEPLOYMENT_ID"),
            )
        else:
            llm = ChatOpenAI(temperature=0.0)

        db_tool = CustomSQLDatabaseToolkit(db=self.db, llm=llm)
        tool_description = """
This tool will help you understand similar examples to adapt them to the user question.
Input to this tool should be the user question.
"""

        retriever_tool = create_retriever_tool(
            ExamplesRetriever(),
            name="sql_get_similar_examples",
            description=tool_description,
        )

        use_example = self.strategy_args.get("use_example")

        custom_tool_list = [retriever_tool] if use_example else []

        custom_suffix = """Begin!

Question: {input}
Thought: I should first get the similar examples I know.
If the examples are enough to construct the query, I can build it.
Otherwise, I can then look at the tables in the database to see what I can query.
Then I should query the schema of the most relevant tables.
{agent_scratchpad}"""

        default_suffix = """Begin!

Question: {input}
Thought: I should look at the tables in the database to see what I can query. Then I should query the schema of the most relevant tables.
{agent_scratchpad}"""

        self.agent = create_sql_agent(
            llm=llm,
            toolkit=db_tool,
            verbose=True,
            prefix=SQL_PREFIX,
            agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            extra_tools=custom_tool_list,
            suffix=custom_suffix if use_example else default_suffix,
            top_k=3,
            max_iterations=10,
            max_execution_time=60,
        )

    def predict(self, nl_query, **kwargs):
        result = self.agent.run(nl_query)
        # trim left and right ", ', \n, \t from result
        result = result.strip("\n\t ")
        if result and result[0] == result[-1] and result[0] in ['"', "'"]:
            result = result[1:-1]
        return result
