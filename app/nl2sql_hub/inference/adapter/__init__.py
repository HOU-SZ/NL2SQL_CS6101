from nl2sql_hub.inference.adapter.inference_adapter import BaseInferenceAdapter
from nl2sql_hub.inference.adapter.tgi_client import TGIInferenceAdapter
from nl2sql_hub.inference.adapter.openai import OpenAIInferenceAdapter


def get_inference_adapter(adapter_name: str, **args) -> BaseInferenceAdapter:
    if adapter_name == "tgi":
        model_url = args.pop("model_url")
        return TGIInferenceAdapter(tgi_url=model_url, **args)
    elif adapter_name == "openai":
        model_name = args.pop("model_name")
        return OpenAIInferenceAdapter(model=model_name, **args)
    else:
        raise NotImplementedError()
