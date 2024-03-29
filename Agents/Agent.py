from abc import abstractmethod, ABCMeta
from typing import List, Dict, overload, Literal

from injector import singleton

from llm.api import LLMApi, Api
from utils.util import YamlReader, QAExamples, MessageQueue, Message

from collections import deque


class Agent(metaclass=ABCMeta):
    def __init__(self, prompt_file: str = None, role_name: str = None):
        if prompt_file:
            prompts = YamlReader.read(prompt_file)
            self.system_msg: str = prompts['system_msg']
            self.prompt_templates: Dict[str, str] = prompts['prompt_templates']
            read_examples: Dict[str, List[Dict[str, str]]] = prompts['examples']
            self.examples: Dict[str, QAExamples] = {}
            for k, v in read_examples:
                self.examples[k] = QAExamples.createQAExamples(v)
        self.msg_queue: MessageQueue = MessageQueue()
        self.role_name = role_name

    def __str__(self):
        return self.role_name

    def send_msg(self, send_to, msg: Message):
        msg.setSender(self)
        send_to.receive_msg(msg)

    def receive_msg(self, msg: Message):
        msg.setReceiver(self)
        self.msg_queue.push(msg)

    @overload
    def process_msg(self):
        ...

    @overload
    def process_msg(self, msg: Message):
        ...

    @abstractmethod
    def process_msg(self, arg=None):
        ...

    @abstractmethod
    def chatLLM(self, api: Api, template_key: str, **kwargs):
        ...
