from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
)
import os
import openai
from loguru import logger
import traceback

from nl2sql_hub.inference.adapter.inference_adapter import BaseInferenceAdapter


class OpenAIInferenceAdapter(BaseInferenceAdapter):
    def __init__(self, model, openai_mode="chat", **args) -> None:
        self.model = model
        self.mode = openai_mode  # chat / completion

    @retry(wait=wait_random_exponential(min=60, max=120), stop=stop_after_attempt(6))
    def infer(
            self, prompt, temperature=0.0, max_new_tokens=1024, stop_words=None, **kwargs
    ):
        try:
            if self.mode == "chat":
                args = {
                    "model": self.model,
                    "messages": [{"content": prompt, "role": "user"}],
                    "temperature": temperature,
                    "max_tokens": max_new_tokens,
                    "stop": stop_words,
                    "use_beam_search": kwargs.get("use_beam_search", False),
                    "best_of": kwargs.get("best_of", 1),
                    "early_stopping": kwargs.get("early_stopping", False),
                }
                if openai.api_type and openai.api_type.startswith("azure"):
                    args["engine"] = os.environ.get("OPENAI_AZURE_DEPLOYMENT_ID")
                    args.pop("model")
                    args.pop("use_beam_search")
                    args.pop("best_of")
                    args.pop("early_stopping")

                logger.info(f"openai chat args: {args}\n")
                completion = openai.ChatCompletion.create(**args)

                generated_text = completion["choices"][0]["message"]["content"]
                logger.info(f"openai chat response: {generated_text}")
                return generated_text
            elif self.mode == "completion":
                args = {
                    "model": self.model,
                    "prompt": prompt,
                    "temperature": temperature,
                    "max_tokens": max_new_tokens,
                    "stop": stop_words,
                    "use_beam_search": kwargs.get("use_beam_search", False),
                    "best_of": kwargs.get("best_of", 1),
                    "early_stopping": kwargs.get("early_stopping", False),
                }
                if openai.api_type and openai.api_type.startswith("azure"):
                    args["engine"] = os.environ.get("OPENAI_AZURE_DEPLOYMENT_ID")
                    args.pop("model")
                    args.pop("use_beam_search")
                    args.pop("best_of")
                    args.pop("early_stopping")

                logger.info(f"openai completion args: {args}\n")
                response = openai.Completion.create(**args)
                generated_text = response["choices"][0]["text"]
                logger.info(generated_text)
                return generated_text
            else:
                raise RuntimeError("unknown mode " + self.mode)
        except Exception as e:
            logger.info(f"openai api error: {e}")
            traceback.print_exc()
            raise e
