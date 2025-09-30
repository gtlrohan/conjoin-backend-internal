import logging
from typing import List

import openai
import tiktoken
from openai import OpenAI

from app.constants import OPENAI_API_KEY
from app.postgres.models.gpt import Message

log = logging.getLogger(__name__)

client = OpenAI(api_key=OPENAI_API_KEY)

# USD pricing per 1000 tokens
gpt_4_turbo = {"input": 0.01, "output": 0.03}

gpt_4 = {"gpt-4": {"input": 0.03, "output": 0.06}, "gpt-4-32k": {"input": 0.06, "output": 0.12}}

gpt_35_turbo = {"gpt-3.5-turbo-1106": {"input": 0.0010, "output": 0.0020}, "gpt-3.5-turbo-instruct": {"input": 0.0015, "output": 0.0020}}

pricing = {
    "gpt-4-0125-preview": gpt_4_turbo,
    "gpt-4-turbo-preview": gpt_4_turbo,
    "gpt-4-1106-preview": gpt_4_turbo,
    "gpt-4-vision-preview": gpt_4_turbo,
    "gpt-4": gpt_4["gpt-4"],
    "gpt-4-0613": gpt_4["gpt-4"],
    "gpt-4-32k": gpt_4["gpt-4-32k"],
    "gpt-4-32k-0613": gpt_4["gpt-4-32k"],
    "gpt-3.5-turbo": gpt_35_turbo["gpt-3.5-turbo-1106"],
    "gpt-3.5-turbo-1106": gpt_35_turbo["gpt-3.5-turbo-1106"],
    "gpt-3.5-turbo-instruct": gpt_35_turbo["gpt-3.5-turbo-instruct"],
}


async def ask_gpt(messages: List[Message], system_prompt: str, model_name: str):
    # Log the input to the API
    log.info(f"Sending prompt to GPT:\nSystem Prompt: {system_prompt}\nUser Prompt: {messages}")

    openai.api_key = OPENAI_API_KEY
    try:
        # Create messages list with system prompt included
        api_messages = [{"role": "developer", "content": system_prompt}] + [{"role": msg.role, "content": msg.content} for msg in messages]

        response = client.chat.completions.create(
            model=model_name,
            messages=api_messages,
            temperature=0.0,
        )
        content = response.choices[0].message.content
        total_tokens = response.usage.total_tokens

        # Log the response from the API
        log.info(f"GPT response:\n{content}\nTokens consumed: {total_tokens}")

        return content, total_tokens
    except Exception as e:
        # Log the error if the API call fails
        log.error(f"An error occurred: {str(e)}")
        raise


async def generate_embedding(embedding_text: str):
    response = client.embeddings.create(input=embedding_text, model="text-embedding-ada-002")
    embedding = response.data[0].embedding
    return embedding


def count_input_tokens(input_str: str, model: str):
    encoding = tiktoken.encoding_for_model(model)
    token_count = len(encoding.encode(input_str))
    return token_count


def calculate_openAI_gpt_cost(input_tokens: int, output_tokens: int, model: str):
    input_cost = (input_tokens / 1000) * pricing[model]["input"]
    output_cost = (output_tokens / 1000) * pricing[model]["output"]
    return input_cost + output_cost
