import os
import openai
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import modelscope


def get_tokenizer_model(model_name):
    try:
        print("torch.cuda.device_count(): ", torch.cuda.device_count())
        print("torch.cuda.is_available(): ", torch.cuda.is_available())
        print("torch.version.cuda: ", torch.version.cuda)
    except Exception as e:
        print("Error: ", e)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        trust_remote_code=True,
        torch_dtype=torch.float16,
        device_map="auto",
        use_cache=True,
    )
    return tokenizer, model


class sqlcoder:
    def __init__(self, model_name="./model-sqlcoder-7b-2"):
        self.tokenizer, self.model = get_tokenizer_model(model_name)

    def generate(self, prompt):
        # print("Prompt: ", prompt, flush=True)
        pipe = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            max_new_tokens=600,
            do_sample=False,
            return_full_text=False,
            num_beams=1,
        )
        generated_query = (
            pipe(
                prompt,
                num_return_sequences=1,
                eos_token_id=self.tokenizer.eos_token_id,
                pad_token_id=self.tokenizer.eos_token_id,
            )[0]["generated_text"]
            .split(";")[0]
            .split("```")[0]
            .strip()
            + ";"
        )
        # print("+++++++++++++++++++++Response:\n", generated_query, flush=True)
        # print("+++++++++++++++++++++Response end\n")
        return generated_query

    def debug(self, prompt):
        # print("Prompt: ", prompt, flush=True)
        pipe = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            max_new_tokens=350,
            do_sample=False,
            return_full_text=False,
            num_beams=1,
        )
        generated_query = (
            pipe(
                prompt,
                num_return_sequences=1,
                eos_token_id=self.tokenizer.eos_token_id,
                pad_token_id=self.tokenizer.eos_token_id,
            )[0]["generated_text"]
            .split(";")[0]
            .split("```")[0]
            .strip()
            + ";"
        )
        # print("+++++++++++++++++++++Response:\n", generated_query, flush=True)
        # print("+++++++++++++++++++++Response end\n")
        return generated_query


class GPT:
    def __init__(self, model_name="gpt-3.5-turbo"):
        self.model_name = model_name
        API_KEY = ""  # shizheng key
        os.environ["OPENAI_API_KEY"] = API_KEY
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def generate(self, prompt):
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            n=1,
            stream=False,
            temperature=0.0,
            max_tokens=600,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            stop=["Q:"]
        )
        return response['choices'][0]['message']['content']

    def debug(self, prompt):
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            n=1,
            stream=False,
            temperature=0.0,
            max_tokens=350,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            stop=["#", ";", "\n\n"]
        )
        return response['choices'][0]['message']['content']


class DeepSeek:
    def __init__(self, model_name="./deepseek-coder-33b-instruct"):
        self.tokenizer = modelscope.AutoTokenizer.from_pretrained(
            model_name, trust_remote_code=True)
        self.model = modelscope.AutoModelForCausalLM.from_pretrained(
            model_name, use_cache=True, trust_remote_code=True, torch_dtype=torch.bfloat16).cuda()

    def generate(self, prompt):
        messages = [
            {'role': 'user', 'content': prompt}
        ]
        inputs = self.tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, return_tensors="pt").to(self.model.device)
        # tokenizer.eos_token_id is the id of <|EOT|> token
        outputs = self.model.generate(inputs, max_new_tokens=512, do_sample=False,
                                      top_k=5, num_return_sequences=1, eos_token_id=self.tokenizer.eos_token_id)
        print(self.tokenizer.decode(
            outputs[0][len(inputs[0]):], skip_special_tokens=True))
        return self.tokenizer.decode(outputs[0][len(inputs[0]):], skip_special_tokens=True)

    def debug(self, prompt):
        messages = [
            {'role': 'user', 'content': prompt}
        ]
        inputs = self.tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, return_tensors="pt").to(self.model.device)
        # tokenizer.eos_token_id is the id of <|EOT|> token
        outputs = self.model.generate(inputs, max_new_tokens=350, do_sample=False,
                                      top_k=5, num_return_sequences=1, eos_token_id=self.tokenizer.eos_token_id)
        print(self.tokenizer.decode(
            outputs[0][len(inputs[0]):], skip_special_tokens=True))
        return self.tokenizer.decode(outputs[0][len(inputs[0]):], skip_special_tokens=True)


class modelhub_deepseek_coder_33b_instruct:
    def __init__(self, model_name="deepseek-coder-33b-instruct"):
        self.model_name = model_name
        self.client = openai.OpenAI(api_key="9ea3d7417a2e4115a18c7048cb0c216f",
                                    base_url="http://modelhub.4pd.io/learnware/models/openai/4pd/api/v1")

    def generate(self, prompt):
        response = self.client.chat.completions.create(
            model="public/deepseek-coder-33b-instruct@main",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=600,
            top_p=1.0,
            stop=None
        )
        return response.choices[0].message.content

    def debug(self, prompt):
        response = self.client.chat.completions.create(
            model="public/deepseek-coder-33b-instruct@main",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=350,
            top_p=1.0,
            stop=None
        )
        return response.choices[0].message.content


class modelhub_qwen1_5_72b_chat:
    def __init__(self, model_name="qwen1.5-72b-chat"):
        self.model_name = model_name
        self.client = openai.OpenAI(api_key="9ea3d7417a2e4115a18c7048cb0c216f",
                                    base_url="http://modelhub.4pd.io/learnware/models/openai/4pd/api/v1")

    def generate(self, prompt):
        response = self.client.chat.completions.create(
            model="public/qwen1-5-72b-chat@main",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=600,
            top_p=1.0,
            stop=None
        )
        return response.choices[0].message.content

    def debug(self, prompt):
        response = self.client.chat.completions.create(
            model="public/qwen1-5-72b-chat@main",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=350,
            top_p=1.0,
            stop=None
        )
        return response.choices[0].message.content
