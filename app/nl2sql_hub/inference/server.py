from fastapi import FastAPI, Depends
from pydantic import BaseModel
from loguru import logger
from nl2sql_hub.inference.args import InferenceArgs
from nl2sql_hub.nl2sql_strategy import BasicNL2SQL, LangchainStrategy
import sys

app = FastAPI()

nl2sql_strategy = None

STRATEGY_MAP = {
    "basic": BasicNL2SQL,
    "langchain": LangchainStrategy,
}

logger.remove()
logger.add(sys.stdout, level="ERROR")

def load_strategy(name, global_inf_args: InferenceArgs):
    if name not in STRATEGY_MAP:
        raise ValueError(f"Invalid strategy name: {name}")
    cls = STRATEGY_MAP[name]
    logger.info(f"Loading strategy class: {cls} for strategy: {name}")
    s = cls(global_inf_args)
    logger.info(f"Loaded strategy: {name}")
    return s


@app.on_event("startup")
def startup_event():
    logger.info("startup_event")
    # import after init global_inf_args
    from nl2sql_hub.inference.args import global_inf_args

    # global_inf_args = config.global_inf_args
    if global_inf_args is None or global_inf_args.datasource is None:
        raise ValueError("InferenceArgs is not initialized")
    logger.info(f"global_inf_args: {global_inf_args}")
    strategy_name = global_inf_args.strategy
    app.state.nl2sql_strategy = load_strategy(strategy_name, global_inf_args)


class PredictRequest(BaseModel):
    natural_language_query: str


class PredictResponse(BaseModel):
    success: bool
    sql_queries: list[str]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict")
def predict(req: PredictRequest):
    try:
        nl2sql = app.state.nl2sql_strategy
        nl_query = req.natural_language_query
        logger.info(f"Received query: {nl_query}")
        sql = nl2sql.predict(nl_query)
        logger.info(f"Predicted sql: {sql}")
        return PredictResponse(success=True, sql_queries=[sql])
    except Exception as e:
        logger.error(f"Predict error: {e}")
        return PredictResponse(success=False, sql_queries=[])
