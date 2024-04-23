from text_generation import Client
from nl2sql_hub.inference.adapter.inference_adapter import BaseInferenceAdapter


class TGIInferenceAdapter(BaseInferenceAdapter):
    def __init__(self, tgi_url, **args):
        self.client = Client(tgi_url, timeout=60)

    def infer(self, prompt, max_new_tokens=1024, temperature=0.0, **args):
        if temperature == 0.0:
            temperature = None
        # temperature == 1.0 or temperature is None means greedy decoding for tgi.
        outputs = self.client.generate(
            prompt, temperature=temperature, max_new_tokens=max_new_tokens
        ).generated_text

        return outputs
