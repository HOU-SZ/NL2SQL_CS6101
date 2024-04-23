import random

from nl2sql_hub.datasource import DataSource
from nl2sql_hub.inference.args import InferenceArgs
from nl2sql_hub.inference.adapter import (
    BaseInferenceAdapter,
    TGIInferenceAdapter,
    OpenAIInferenceAdapter,
    get_inference_adapter,
)
import requests
import json
import os
from loguru import logger
from nl2sql_hub.nl2sql_strategy.abstract_strategy import AbstractNL2SQLStrategy

internal_knowledge = {
    'gyhh': [
        "和城市相关请使用 new_energy_vehicle_city_sales，和品牌相关请使用 new_energy_vehicle_model_sales，和批发量有个使用 new_energy_vehicle_model_sales, 其他情况使用 new_energy_vehicle_sales",
        "除非用户强调累积，否则使用按年、按季度、按月统计"
        "new_energy_vehicle_model_sales 中的销量应该带上 sale_type='零售量' 条件",
        "计算占比的时候，仔细考虑分母。如A群体中的B占比，应该先过滤A群体，再算B的占比",
        "A条件下的B占比 = count(B) / count(0) where A",
        "整体乘用车=新能源+燃油车",
        "phev+bev=nev=新能源",
        "passenger_car_sales - nev = 燃油车",
        "passenger_car_sales-(phev+bev)=燃油车",
        "2022年销量同比 =(2022-2021)/2021",
        "新能源suv渗透率 = suv新能源销量/(suv新能源销量+suv燃油车销量)",
        "A00级新能源渗透率 = A00级新能源销量/(A00整体销量)，整体=新能源+燃油",
        "自主品牌渗透率 = 自主品牌新能源销量/(自主品牌整体销量)，整体=新能源+燃油",
        "新能源乘用车渗透率 = 新能源乘用车销量/(新能源销量+燃油车销量)",
        "25-40万价格段新能源乘用车占比 = max_price >= 20 AND max_price <= 40 的所有（新能源+燃油车）销量，再计算这部分中 新能源类型销量的占比",
        "询问趋势时，给出销量即可",
        "new_energy_vehicle_model_sales中包含不同能源类型",
        "涉及价格条件时，最小、最大价格均需满足"
    ],
    'loreal': [
        "查询各个品牌的销量、消费者人数、消费者人数增长百分比、各渠道的绑定率、各客户类型（新客户、老客户、流失客户、唤醒客、沉睡客等）的增长百分比",
        "绑定率是mock的数据，计算绑定率用MAX函数取最大值即可",
        "YSL 2022年的客户保留率 = (YSL 2022年的老客客人数总和 / YSL 2022年的购买客人数总和) * 100",
        "新客同比增长率 = (当前年度新客人数 - 前一年度新客人数) / 前一年度新客人数 * 100 %",
        "老客留存率 =（老客人数 / 总购买客户数）*100 %",
        "YSL品牌在天猫2022年的人均消费金额 = YSL品牌在天猫2022年的总销售额 / YSL品牌在天猫2022年的购买客人数",
        "平均花费 = 销售额总和 / 购买客人数总和",
        "YSL 2021年的人均购买金额 = YSL 2021年的总销售额 / YSL 2021年的购买客人数。",
        "YSL品牌某渠道本年度的人均消费 = YSL品牌某渠道本年度销售总额 / YSL品牌某渠道本年度购买客人数",
    ],
    "yzkj": [
        "近5年环比是比较最近五年的数据和前五年的数据",
        "请区分同比和环比",
        "企业同比增长率 = ((当前年份符合条件的企业数量 - 前一年度符合条件的企业数量) / 前一年度符合条件的企业数量) * 100 %",
        "注意排序的时候使用 `` 包含列名，不要使用单引号",
        "registered_capital 的单位是万"
    ],
    "tyjs": ["注意排序的时候使用 `` 包含列名"],
    "bjdx": [
        "主要是查询工单问题，工单标签分为三级，类似省市县的关系"
        "根据某个级别标签或者两个、三个标签组合的工单问题查询",
        "问题包括全月工单量、每周工单量、占比、日环比、日同比等",
        "工单日环比增长率 = ((某日工单个数 - 前一日工单个数) / 前一日工单个数) * 100 %",
    ],
    "hxjj": [
        "Y 份额产品指的是基金名以 Y 结尾, fund_name like '%Y",
        # "问题涉及到分布的时候，应该同时计算数量和相对整体百分比",
        "优先使用问题中的基金名称，并使用 fund_name like '%{fund_name}%' 的方式",
        "带实效性的数据查询，都要用 confirm_date = date '2023-08-01'",
        "计算占比的时候，仔细考虑分母。如A群体中的B占比，应该先过滤A群体，再算B的占比",
        "A条件下的B占比 = count(B) / count(0) where A",
        # "年龄分布为 18-25, 25-35, 35-45, 45-55, 55-65, 65+",
        "正收益率指的是 all_profit_untl_now_cny / all_cost_untl_now_cny > 0",
        "性别包括男、女、未知",
        "持仓用户指的是 hold_shr > 0",
        "销售情况指的是销量、客户数量、持有金额",
        "涉及到持仓时考虑hold_shr > 0",
        # "地域分布请返回省份、数量、占比",
        # "持仓金额分布为 0-5万, 5-10万, 10-20万, 20-50万, 50-100万, 100万+",
        # "收益率分布为 -50%以下, -50%~-30%, -30%~-20%, -20%~-10%, -10%~-5%, -5%~0%, 0%~5%, 5%~10%, 10%~20%, 20%~30%, 30%~50%, >(50%)",
        "客户数量可能重复，记得加 distinct",
        "尽量使用 ads_dtas_cust_cnt",
        "累计收益情况需要求和"
    ],
    "icbc": [
        "pname 是一级行, zname 是二级行",
        "客户数量可能重复，记得加 distinct"
    ]
}


class BasicNL2SQL(AbstractNL2SQLStrategy):
    def __init__(self, inference_args: InferenceArgs):
        self.inference_args = inference_args
        self.datasource: DataSource = inference_args.datasource

        if inference_args.model_type:
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

        self.config = {"use_cn": False, "db_type": self.datasource.driver}

        # TODO: get task service url from config
        self.task_service_url = os.getenv(
            "TASK_SERVICE_URL", None
        )
        self.scene_id = int(os.getenv("SCENE_ID", "0"))

        import nl2sql_hub.nl2sql_strategy.basic.prompt

        prompt_builders = nl2sql_hub.nl2sql_strategy.basic.prompt.load_prompts(nl2sql_hub.nl2sql_strategy.basic.prompt)

        clz = prompt_builders[inference_args.prompt_template]
        logger.info(f"load prompt builder: {clz}, type is {type(clz)}")
        self.prompt_builder = clz(prompt_template=self.inference_args.prompt_template, datasource=self.datasource)
        logger.info(f"prompt builder: {self.prompt_builder}")

        if inference_args.strategy_args.get("rag", False):
            self.knowledge_texts = internal_knowledge.get(self.datasource.name, [])
        else:
            self.knowledge_texts = []

    def predict(self, query, **kwargs):
        prompt_template = self.inference_args.prompt_template
        max_length = self.inference_args.max_length
        stop_words = self.inference_args.stop_words
        examples = self.retrival_examples(query)

        temperature = self.inference_args.temperature
        best_of = self.inference_args.best_of
        use_beam_search = self.inference_args.use_beam_search
        early_stopping = self.inference_args.early_stopping

        prompt = self.prompt_builder.build_prompt(
            query,
            examples=examples,
            max_length=max_length,
            knowledge_texts=self.knowledge_texts,
        )
        sql = self.infer(prompt, stop_words=stop_words, temperature=temperature, best_of=best_of,
                         use_beam_search=use_beam_search, early_stopping=early_stopping, **kwargs)
        sql = self.prompt_builder.post_process(query, sql, )
        return sql

    def infer(self, prompt, **kwargs):
        response = self.inference_helper.infer(prompt, **kwargs)
        return response

    def retrival_examples(self, query, top_k=3):
        if self.task_service_url is None:
            logger.warning("try to retrival examples, but task service url is None")
            return []
        url = f"{self.task_service_url}/api/v1/findExamples"
        data = {
            "natural_language_query": query,
            "limit_num": top_k,
            "scene_id": self.scene_id,
        }
        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(url, headers=headers, data=json.dumps(data))
            examples = response.json()
            return examples[:top_k]
        except Exception as e:
            logger.error(f"retrival examples error: {e}", exc_info=True)
            return None

    def make_data_for_sft(
            self, queries: list[dict[str, str]], sft_format="qwen", generate_few_shots=True,
            generate_zero_shot=True, **kwargs
    ):
        """
        :param queries: [{"query": "xxx", "sql": "xxx"}, ...]
        :param sft_format: qwen or vicuna
        :param generate_few_shots: if true, generate few shots, else generate only zero shots
        :param generate_zero_shot: if true, generate zero shots when few shots are generated, else not
        """
        logger.info(f"make data for sft, sft_format: {sft_format}")
        prompts = []
        sqls = []
        logger.info(f"generate_few_shots: {generate_few_shots}")
        logger.info(f"generate_zero_shot: {generate_zero_shot}")
        logger.info(f"total queries: {len(queries)}")
        for q in queries:
            prompt_template = self.inference_args.prompt_template
            max_length = self.inference_args.max_length
            question = q["query"]
            sql = q["sql"]
            if generate_few_shots:
                examples = self.retrival_examples(question, top_k=10)
            else:
                examples = []
            if examples is not None:
                p = random.random()
                if p < 0.3:
                    examples = examples[-3:]
                elif p < 0.4:
                    examples = random.sample(
                        examples, min(random.randint(0, 4), len(examples))
                    )
                else:
                    examples = examples[:3]

            prompt_few_shots = self.prompt_builder.build_prompt(
                question,
                examples=examples,
                max_length=max_length,
                knowledge_texts=self.knowledge_texts,
            )
            prompts.append(prompt_few_shots)
            sqls.append(sql)
            if generate_zero_shot and examples:
                prompt_0_shots = self.prompt_builder.build_prompt(
                    question,
                    examples=None,
                    max_length=max_length,
                    knowledge_texts=self.knowledge_texts,
                )
                prompts.append(prompt_0_shots)
                sqls.append(sql)

        return self.sft_format_adapter(prompts, sqls, sft_format=sft_format)

    def sft_format_adapter(self, prompts, sqls, shuffle=True, sft_format="qwen"):
        if sft_format == "qwen":
            data_list = []
            idx = 0
            for pair in zip(prompts, sqls):
                data = {
                    "id": f"identity_{idx}",
                    "conversations": [
                        {"from": "user", "value": pair[0]},
                        {"from": "assistant", "value": pair[1]},
                    ],
                }
                data_list.append(data)
                idx += 1
            if shuffle:
                random.shuffle(data_list)
            return data_list
        elif sft_format == "vicuna":
            data_list = []
            idx = 0
            for pair in zip(prompts, sqls):
                data = {
                    "id": f"identity_{idx}",
                    "conversations": [
                        {"from": "human", "value": pair[0]},
                        {"from": "gpt", "value": pair[1]},
                    ],
                }
                data_list.append(data)
                idx += 1
            if shuffle:
                random.shuffle(data_list)
            return data_list
        elif sft_format == 'deepseek':
            data_list = []
            idx = 0
            for pair in zip(prompts, sqls):
                data = {
                    "instruction": pair[0],
                    "output": pair[1]
                }
                data_list.append(data)
                idx += 1
            if shuffle:
                random.shuffle(data_list)
            return data_list
        elif sft_format == 'magicoder':
            data_list = []
            idx = 0
            for pair in zip(prompts, sqls):
                data = {
                    "instruction": pair[0],
                    "response": pair[1]
                }
                data_list.append(data)
                idx += 1
            if shuffle:
                random.shuffle(data_list)
            return data_list
        else:
            raise NotImplementedError
