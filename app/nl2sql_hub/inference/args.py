from pydantic import BaseModel
from loguru import logger

from nl2sql_hub.datasource import DataSource


class InferenceArgs(BaseModel):
    strategy: str = "basic"
    strategy_args: dict = {}
    model_type: str | None  # tgi or openai
    openai_mode: str = "chat"  # chat or completion
    stop_words: list[str] | None = None
    model_url: str | None = None
    model_name: str | None = "gpt3.5-turbo"
    prompt_template: int = 0
    max_length: int = 4096
    n_shots: int = 3
    temperature: float = 0.0
    best_of: int = 1
    use_beam_search: bool = False
    early_stopping: bool = False
    max_new_tokens: int = 1024
    debug: bool = False

    datasource: DataSource | None = None


global_inf_args: InferenceArgs = InferenceArgs()

# int single instance of InferenceArgs
# def init_args(args: InferenceArgs) -> InferenceArgs:
#     global global_inf_args
#     if global_inf_args is not None:
#         logger.warning("InferenceArgs has been initialized, skip")
#         return global_inf_args
#     global_inf_args = args
#     logger.info(f"Init InferenceArgs: {args}")
#     return args
