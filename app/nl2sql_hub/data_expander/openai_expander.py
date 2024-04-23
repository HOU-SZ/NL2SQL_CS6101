import json
import os
from loguru import logger
import tqdm
import random
import openai
from langchain.pydantic_v1 import BaseModel, Field, validator
import traceback
from langchain.globals import set_verbose

set_verbose(True)

from langchain.output_parsers import (
    StructuredOutputParser,
    ResponseSchema,
    PydanticOutputParser,
)
from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.chat_models import ChatOpenAI, AzureChatOpenAI
from nl2sql_hub.data_expander.base_expander import BaseExpander
from nl2sql_hub.datasource import DataSource, get_url
from langchain.sql_database import SQLDatabase


class QA(BaseModel):
    question: str = Field(description="问题")
    sql: str = Field(description="SQL查询")


class ListQA(BaseModel):
    data: list[QA] = Field(description="问题和SQL查询列表")


class OpenAIExpander(BaseExpander):
    def __init__(self, datasource: DataSource, **kwargs):
        self.iteration = int(kwargs.get("iteration", "200"))
        self.batch_size = int(kwargs.get("batch_size", "5"))

        temperature = (0.0,)
        model_name = kwargs.get("model_name", "gpt-3.5-turbo")

        if openai.api_type and openai.api_type.startswith("azure"):
            llm = AzureChatOpenAI(
                temperature=0.0,
                deployment_name=os.environ.get("OPENAI_AZURE_DEPLOYMENT_ID"),
            )
        else:
            llm = ChatOpenAI(temperature=0.0, model_name=model_name)

        self.llm = llm

        self.datasource = datasource
        self.db = SQLDatabase.from_uri(database_uri=get_url(self.datasource))
        self.table_info = self.db.get_table_info()

        self.prompt = """请根据以下'{db_name}'数据库的表结构和示例数据生成问题和SQL查询.
数据库类型: {dialect}
表结构和示例数据:
{table_info}
这里有一些示例问题和SQL：
{examples}
根据提供的表结构和示例问题，请生成{batch_size}条问题和 SQL，尽量包含不同难度的问题.
"""

    def expand(self, input_dataset_name_or_path, nl2sql_workdir):
        # parser = PydanticOutputParser(pydantic_object=list[QA])
        generated_data = []

        with open(
            os.path.join(input_dataset_name_or_path, "train/data.json"), "r"
        ) as f:
            all_data = json.load(f)
        source_all_data = all_data.copy()
        steps = max(self.iteration, len(all_data) // 3)
        for i in tqdm.tqdm(range(steps)):
            if len(all_data) == 0:
                all_data = source_all_data.copy()
            try:
                # sample 3 from all_data, and remove them from all_data
                examples = random.sample(all_data, min(3, len(all_data)))
                for e in examples:
                    all_data.remove(e)
                examples = [
                    {"question": e["query"], "sql": e["sql"].strip(" \n\r\t;")}
                    for e in examples
                    if e["query"] != ""
                ]

                prompt = ChatPromptTemplate(
                    messages=[HumanMessagePromptTemplate.from_template(self.prompt)],
                    input_variables=[
                        "db_name",
                        "dialect",
                        "table_info",
                        "examples",
                        "batch_size",
                    ],
                    # partial_variables={
                    #     "format_instructions": parser.get_format_instructions()
                    # },
                )
                _input = prompt.format_prompt(
                    db_name=self.datasource.name,
                    dialect=self.db.dialect,
                    table_info=self.table_info,
                    examples=json.dumps(examples, indent=2, ensure_ascii=False),
                    batch_size=self.batch_size,
                )

                output = self.llm(_input.to_messages())
                # output_obj = parser.parse(output)
                logger.info(f"generated_data: {output.content}")
                result = json.loads(output.content)
                generated_data.extend(
                    [{"query": qa["question"], "sql": qa["sql"]} for qa in result]
                )
            except Exception as e:
                logger.error(f"expand error: {e}", exc_info=True)
                traceback.print_exc()
                continue

        return generated_data

    def name(self):
        return "openai"
