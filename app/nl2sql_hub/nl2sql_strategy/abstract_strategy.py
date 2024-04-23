from nl2sql_hub.inference.args import InferenceArgs


class AbstractNL2SQLStrategy:
    def __init__(self, inference_args: InferenceArgs):
        pass

    def predict(self, nl_query, **kwargs):
        raise NotImplementedError()

    def make_data_for_sft(self, queries: list[dict[str, str]], **kwargs):
        raise NotImplementedError()
