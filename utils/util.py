import abc
import logging
import os.path
from abc import abstractmethod
from typing import Dict, List, Any, Optional

import yaml

from Agents.Agent import Agent
from collections import deque

from llm import PROJECT_DIR
from llm.api import LLMApi

import re

from utils.DependencyGraph import CodeEntity, CodeEntityType


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


class Logger:
    def __init__(self, log_file: str = None, record_level: int = logging.DEBUG, format: str = None):
        self.format = format
        if format is None:
            self.format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s-%(funcName)s'
        self.log_dir = os.path.join(PROJECT_DIR, 'workingspace', 'log')
        if log_file is None:
            self.log_file = 'log.txt'
            if not os.path.exists(self.log_dir):
                os.makedirs(self.log_dir, mode=0o777)
            self.log_file = os.path.join(self.log_dir, self.log_file)
        self.record_level = record_level
        logging.basicConfig(filename=self.log_file, format=self.format, level=self.record_level)

    def info(self, msg):
        logging.info(msg)

    def debug(self, msg):
        logging.debug(msg)

    def warning(self, msg):
        logging.warning(msg)

    def error(self, msg):
        logging.error(msg)

    def fatal(self, msg):
        logging.critical(msg)


class YamlReader:
    @staticmethod
    def read(path: str, encoding: str = 'utf-8'):
        assert os.path.exists(path), f'{path} does not exits'
        with open(path, 'r', encoding=encoding) as f:
            result = yaml.load(f.read(), Loader=yaml.FullLoader)
        return result


class ContentExtractor:
    STEP_PATTERN = re.compile(r'Step\s+\d\s*:\s*Create a (\w+) called (\w+).This class will be responsible for (\w+)',
                              re.I)

    @staticmethod
    def _get_code_entity_type(entity_type: str) -> Optional[CodeEntityType]:
        lower_entity_type = entity_type.lower()
        if lower_entity_type == 'package':
            return CodeEntityType.Package
        elif lower_entity_type == 'class':
            return CodeEntityType.Class
        elif lower_entity_type == 'function':
            return CodeEntityType.Function
        raise Exception(f'unsupported code entity type:{entity_type}')

    @staticmethod
    def extract_code_entity_from_step(step: str, parent_code_entity: CodeEntity = None):
        step = step.strip()
        obj = re.match(ContentExtractor.STEP_PATTERN, step)
        assert (obj is not None
                and obj.group(1) is not None
                and obj.group(2) is not None
                and obj.group(3) is not None), f'{step} has format error'
        entity_type = ContentExtractor._get_code_entity_type(obj.group(1))
        return CodeEntity(entity_type=entity_type, entity_name=obj.group(2), code_desc=obj.group(3),
                          parent_code_entity=parent_code_entity)
