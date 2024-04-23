import click
import uvicorn
import os
import json
from nl2sql_hub.inference.args import InferenceArgs
from nl2sql_hub.inference.args import global_inf_args
from nl2sql_hub.datasource import DataSource


class IntOrStr(click.ParamType):
    name = "int_or_str"

    def convert(self, value, param, ctx):
        try:
            # 首先尝试将值转换为整数
            return int(value)
        except ValueError:
            # 如果转换失败，返回字符串
            return value


@click.command()
@click.option("--host", default="0.0.0.0", help="Host address.")
@click.option("--port", default=8000, help="Port.")
@click.option("--strategy", default="basic", help="Strategy name.")
@click.option("--strategy-args", default="{}", help="Strategy args.")
@click.option("--model-type", default="tgi", help="tgi or openai")
@click.option("--openai-mode", default="chat", help="chat or completion")
@click.option("--stop-words", multiple=True, default=[], help="stop words")
@click.option(
    "--model-url",
    default="http://model",
    help="model service url for text-generation-inference",
)
@click.option(
    "--model-name", default="qwen", help="model name for openai compatible api"
)
@click.option("--prompt-template", type=IntOrStr(), default=0, help="prompt template id")
@click.option("--temperature", default=0.0, help="temperature")
@click.option("--best-of", default=1, help="best of")
@click.option("--use-beam-search", default=False, help="use beam search")
@click.option("--early-stopping", default=False, help="early stopping")
@click.option("--max-new-tokens", default=1024, help="max new tokens")
@click.option("--debug", default=False, help="enable debug mode")
@click.option("--datasource-path", default="data/demo", help="datasource path")
def main(
        host,
        port,
        strategy,
        strategy_args,
        model_type,
        openai_mode,
        stop_words,
        model_url,
        model_name,
        prompt_template,
        temperature,
        best_of,
        use_beam_search,
        early_stopping,
        max_new_tokens,
        debug,
        datasource_path,
):
    with open(os.path.join(datasource_path, "datasource.json"), "r") as f:
        ds = json.load(f)
        print(f"load datasource from {datasource_path}, content:\n{ds}\n")
        datasource = DataSource.parse_obj(ds)

    global_inf_args.strategy = strategy
    global_inf_args.strategy_args = json.loads(strategy_args)
    global_inf_args.model_type = model_type
    global_inf_args.openai_mode = openai_mode
    global_inf_args.stop_words = stop_words
    global_inf_args.model_url = model_url
    global_inf_args.model_name = model_name
    global_inf_args.prompt_template = prompt_template
    global_inf_args.temperature = temperature
    global_inf_args.best_of = best_of
    global_inf_args.use_beam_search = use_beam_search
    global_inf_args.early_stopping = early_stopping
    global_inf_args.max_new_tokens = max_new_tokens
    global_inf_args.debug = debug
    global_inf_args.datasource = datasource

    uvicorn.run("nl2sql_hub.inference.server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
