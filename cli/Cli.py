import abc
from typing import Type, Literal, List

RoleType = Literal[
    'code_executor', 'code_generator', 'code_integrator', 'code_planner', 'code_reviewer', 'test_case_generator', 'format_checker', 'human']


class ChatItem:
    def __init__(self, role: RoleType, content: str):
        self.role = role
        self.content = content

    def get_role(self):
        return self.role

    def get_content(self):
        return self.content

    def set_role(self, new_role: RoleType):
        self.role = new_role

    def set_content(self, new_content: str):
        self.content = new_content

    def __str__(self):
        return f'{self.role} >>> {self.content}'


class ChatHistory:
    def __init__(self):
        self.chat_history: List[ChatItem] = list[ChatItem]()
        self.iterator = None

    def append_item(self, chat_item: ChatItem):
        self.chat_history.append(chat_item)

    def del_item_by_index(self, index: int):
        del self.chat_history[index]

    def get_item_by_index(self, index: int) -> ChatItem:
        return self.chat_history[index]

    def __len__(self):
        return len(self.chat_history)

    def __str__(self):
        return "=" * 20 + '\n' + '\n'.join(map(lambda x: str(x), self.chat_history)) + '\n' + "=" * 20

    def __iter__(self):
        self.iterator = iter(self.chat_history)

    def __next__(self):
        return next(self.iterator)


class Cli(metaclass=abc.ABCMeta):
    def __init__(self, role: RoleType, chat_history: ChatHistory):
        self.role = role
        self.chat_history = chat_history

    def prompt(self, prompt_msg: str):
        print(self.role + ' > ' + prompt_msg)
        self.chat_history.append_item(ChatItem(self.role, prompt_msg))

    def input(self):
        msg = input('human > ')
        self.chat_history.append_item(ChatItem('human', msg))

