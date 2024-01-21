from typing import List

from Agents.Agent import Agent
from llm.api import LLMApi, ChatMessageType
from utils.util import YamlPromptReader


class CodePlanner(Agent):
    def __init__(self, prompt_file: str):
        super().__init__(prompt_file)

    def chatLLM(self, api: LLMApi, template_key: str, **kwargs):
        assert self.prompt_templates.get(template_key) is not None, f'{template_key} does not exists'
        messages: List[ChatMessageType] = list[ChatMessageType]()
        messages.append({"role": "system", "content": self.system_msg})
        messages.append({'role': 'user', 'content': self.prompt_templates.get(template_key).format(kwargs)})
        api.chat_completion(messages)
