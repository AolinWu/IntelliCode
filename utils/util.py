import abc
import os.path
from abc import abstractmethod
from typing import Dict, List, Any, Optional

import yaml

from Agents.Agent import Agent
from collections import deque

from llm.api import LLMApi


class QAExample:
    @staticmethod
    def createQAExample(qa: Dict[str, str]):
        return QAExample(qa.get('Q'), qa.get('A'))

    def __init__(self, q: str = None, a: str = None):
        self.q = q
        self.a = a

    def __str__(self):
        return f"Q:{self.q}\nA:{self.a}"

    def getQ(self):
        return self.q

    def getA(self):
        return self.a

    def setQ(self, q: str):
        self.q = q

    def setA(self, a: str):
        self.a = a


class QAExamples:
    @staticmethod
    def createQAExamples(qas: List[Dict[str, str]]):
        examples = list[QAExample]()
        for qa in qas:
            examples.append(QAExample.createQAExample(qa))
        return QAExamples(examples)

    def __init__(self, examples: List[QAExample] = None):
        if examples:
            self.examples = examples
        else:
            self.examples = list[QAExample]()
        self.iterator = None

    def __len__(self):
        return len(self.examples)

    def __str__(self):
        return '\n\n'.join(map(lambda qa: str(qa), self.examples))

    def getExampleByIndex(self, index: int) -> QAExample:
        return self.examples[index]

    def setExampleByIndex(self, index: int, new_example: QAExample):
        self.examples[index] = new_example

    def delExampleByIndex(self, index: int):
        del self.examples[index]

    def addExample(self, example: QAExample):
        self.examples.append(example)

    def __iter__(self):
        self.iterator = iter(self.examples)

    def __next__(self):
        return next(self.iterator)


class Message:
    def __init__(self, sender: Agent = None, receiver: Agent = None, content: Any = None):
        self.sender = sender
        self.receiver = receiver
        self.content = content

    def getContent(self):
        return self.content

    def setContent(self, new_content):
        self.content = new_content

    def setSender(self, send_from: Agent):
        self.sender = send_from

    def setReceiver(self, send_to: Agent):
        self.receiver = send_to

    def getSender(self):
        return self.sender

    def getReceiver(self):
        return self.receiver


class MessageQueue:
    def __init__(self):
        self.msg_queue = deque(list[Message]())

    def push(self, msg: Message):
        self.msg_queue.append(msg)

    def pop(self) -> Optional[Message]:
        if len(self.msg_queue) == 0:
            return None
        return self.msg_queue.popleft()

class FormatChecker(metaclass=abc.ABCMeta):
    """
    check the LLM's response format and collect related format issues and feedback to LLM,then let LLM correct the format issue progressively
    """
    def __init__(self,api:LLMApi):
        self.issues:List[str]=list[str]()
    @abstractmethod
    def format_check(self,response:str)->bool:
        """
        :param response: need to be checked response
        :return: true if format is right,false if format is wrong
        """
        ...
    def format_revise(self):



class YamlPromptReader:
    @staticmethod
    def readPrompt(path: str, encoding: str = 'utf-8'):
        assert os.path.exists(path), f'{path} does not exits'
        result = None
        with open(path, 'r', encoding=encoding) as f:
            result = yaml.load(f.read(), Loader=yaml.FullLoader)
        return result
