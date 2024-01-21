from abc import abstractmethod, ABCMeta
from typing import List, Dict

from llm.api import LLMApi
from utils.util import YamlPromptReader, QAExamples, MessageQueue, Message

from collections import deque


class Agent(metaclass=ABCMeta):
    def __init__(self, prompt_file: str):
        prompts = YamlPromptReader.readPrompt(prompt_file)
        self.system_msg: str = prompts['system_msg']
        self.prompt_templates: Dict[str, str] = prompts['prompt_templates']
        self.examples: QAExamples = QAExamples.createQAExamples(prompts['examples'])
        self.msg_queue: MessageQueue = MessageQueue()

    def send_msg(self, send_to, msg: Message):
        msg.setSender(self)
        send_to.receive_msg(msg)

    def receive_msg(self, msg: Message):
        msg.setReceiver(self)
        self.msg_queue.push(msg)

    @abstractmethod
    def process_msg(self):
        ...

    @abstractmethod
    def chatLLM(self, api: LLMApi, template_key: str, **kwargs):
        ...
