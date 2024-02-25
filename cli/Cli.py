import abc
import os.path
import time
from enum import Enum
from typing import Type, Literal, List

from injector import singleton

from Agents.Agent import Agent
from Agents.Human import Human
from utils.util import Message


class ChatItem:
    def __init__(self, chat_time: str, role: Agent, content: str):
        self.chat_time = chat_time
        self.role = role
        self.content = content

    def get_role(self):
        return self.role

    def get_content(self):
        return self.content

    def set_role(self, new_role: Agent):
        self.role = new_role

    def set_content(self, new_content: str):
        self.content = new_content

    def __str__(self):
        return f'{self.chat_time} : {self.role} >>> {self.content}'


@singleton
class ChatHistory:
    def __init__(self, mount_file: str):
        assert mount_file.endswith('.txt'),f'{mount_file} is not a .txt file'
        assert os.path.exists(mount_file), f'{mount_file} does not exist'
        self.chat_history: List[ChatItem] = list[ChatItem]()
        self.iterator = None

    def append_item(self, chat_item: ChatItem):
        self.chat_history.append(chat_item)

    def del_item_by_index(self, index: int):
        del self.chat_history[index]

    def get_item_by_index(self, index: int) -> ChatItem:
        return self.chat_history[index]

    def store_to_file(self):

    def __len__(self):
        return len(self.chat_history)

    def __str__(self):
        return '\n'.join(map(lambda x: str(x), self.chat_history))

    def __iter__(self):
        self.iterator = iter(self.chat_history)

    def __next__(self):
        return next(self.iterator)


class Cli(metaclass=abc.ABCMeta):
    def __init__(self, chat_history: ChatHistory):
        self.role: Agent = Human('human')
        self.chat_history = chat_history

    @staticmethod
    def _prompt(role: Agent, prompt_msg: Message):
        print(str(role) + ' > ' + prompt_msg.getContent())

    @staticmethod
    def _input(role: Agent):
        msg = input(f'{role} > ')
        return Message(sender=role, content=msg)

    def chat_round(self, ask_role: Agent, prompt_msg: Message, answer_role: Agent):
        prompt_msg.setReceiver(answer_role)
        Cli._prompt(ask_role, prompt_msg)
        self.chat_history.append_item(ChatItem(time.asctime(), ask_role, prompt_msg.getContent()))
        answer = Cli._input(answer_role)
        answer.setReceiver(ask_role)
        self.chat_history.append_item(ChatItem(time.asctime(), answer_role, answer.getContent()))
