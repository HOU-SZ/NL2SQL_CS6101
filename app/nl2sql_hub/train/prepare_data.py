import click
import os
import json
from nl2sql_hub.inference.args import InferenceArgs
from nl2sql_hub.inference.args import global_inf_args
from nl2sql_hub.datasource import DataSource
from nl2sql_hub.nl2sql_strategy import (
    BasicNL2SQL,
    LangchainStrategy,
    AbstractNL2SQLStrategy,
)
from loguru import logger


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
@click.option("--strategy", default="basic", help="Strategy name.")
@click.option("--strategy-args", default="{}", help="Strategy args.")
@click.option("--prompt-template", default=0, type=IntOrStr(), help="prompt template id")
@click.option("--debug", default=False, help="enable debug mode")
@click.option("--datasource-path", default="data/demo", help="datasource path")
@click.option("--nl2sql-workdir", default="data/demo-work", help="workdir")
@click.option(
    "--examples-sub-path", default="expand-data.json", help="examples file sub path"
)
@click.option(
    "--generate-few-shots", default=True, help="generate few-shots data for sft"
)
@click.option("--generate-zero-shot", default=True, help="generate fewshot data for sft")
@click.option("--output-sub-path", default="train.json", help="output file sub path")
@click.option("--sft-format", default='qwen', help="sft format")
def main(
        strategy,
        strategy_args,
        prompt_template,
        debug,
        datasource_path,
        nl2sql_workdir,
        examples_sub_path,
        generate_few_shots,
        generate_zero_shot,
        output_sub_path,
        sft_format,
):
    with open(os.path.join(datasource_path, "datasource.json"), "r") as f:
        ds = json.load(f)
        print(f"load datasource from {datasource_path}, content:\n{ds}\n")
        datasource = DataSource.parse_obj(ds)

    global_inf_args.strategy = strategy
    global_inf_args.strategy_args = json.loads(strategy_args)
    global_inf_args.prompt_template = prompt_template
    global_inf_args.debug = debug
    global_inf_args.datasource = datasource

    STRATEGY_MAP = {
        "basic": BasicNL2SQL,
        "langchain": LangchainStrategy,
    }

    if strategy not in STRATEGY_MAP:
        raise ValueError(f"Invalid strategy name: {strategy}")
    cls = STRATEGY_MAP[strategy]
    logger.info(f"Loading strategy class: {cls} for strategy: {strategy}")
    s: AbstractNL2SQLStrategy = cls(global_inf_args)
    logger.info(f"Loaded strategy: {strategy}")

    with open(os.path.join(nl2sql_workdir, examples_sub_path)) as f:
        examples = json.load(f)

    prompts = s.make_data_for_sft(examples, generate_few_shots=generate_few_shots,
                                  generate_zero_shot=generate_zero_shot, sft_format=sft_format)

    with open(os.path.join(nl2sql_workdir, output_sub_path), "w") as f:
        json.dump(prompts, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    main()
