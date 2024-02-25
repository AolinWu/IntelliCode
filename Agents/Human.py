from abc import ABC
from typing import overload

from injector import singleton

from Agents.Agent import Agent


@singleton
class Human(Agent, ABC):
    def __init__(self, role_name: str):
        super().__init__(role_name=role_name)

    def
