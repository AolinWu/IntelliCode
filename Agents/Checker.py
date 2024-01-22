import abc
from abc import ABC
from typing import List, Any

from llm.api import LLMApi

import re


class IssueReport:
    def __init__(self):
        self.issues: List[Any] = list[Any]()
        self.iterator = None

    def clear_issue_report(self):
        self.issues.clear()

    def append_issue(self, issue: Any):
        self.issues.append(issue)

    def get_issue_by_index(self, index: int):
        return self.issues[index]

    def del_issue_by_index(self, index: int):
        del self.issues[index]

    def __len__(self):
        return len(self.issues)

    def __iter__(self):
        self.iterator = iter(self.issues)

    def __next__(self):
        return next(self.iterator)

    def __str__(self):
        return '\n'.join(map(lambda i, issue: f'issue ({i}):{str(issue)}', enumerate(self.issues)))


class Checker(metaclass=abc.ABCMeta):
    def __init__(self, api: LLMApi):
        self.api = api
        self.issue_reports: IssueReport = IssueReport()

    @abc.abstractmethod
    def check(self, response: str) -> bool:
        ...

    @abc.abstractmethod
    def revise(self, response: str, max_round: int) -> str:
        ...


class CodePlanFormatChecker(Checker, ABC):
    def __init__(self, api: LLMApi):
        super().__init__(api)

    @staticmethod
    def check_one_line(line: str) -> bool:
        if re.match(
                r'Step (\d+):Create a class called ([_a-zA-Z][0-9_a-zA-Z]*)\.This class will be responsible for ('
                r'.+)\.',
                line) is None and re.match(
            r'Step (\d+):Create a function called ([_a-zA-Z][0-9_a-zA-Z]*)\.This function will be responsible for '
            r'(.+)\.',
            line
        ) is None:
            return False
        return True

    def check(self, response: str) -> bool:
        lines = response.strip().splitlines(keepends=False)
        flag = True
        for i, line in enumerate(lines):
            if not self.check_one_line(line):
                self.issue_reports.append_issue((i, line))
                flag = False
        return flag

    def revise(self, response: str, max_round: int) -> str:
        lines = response.strip().splitlines(keepends=False)
        for _ in range(max_round):
            if self.check(response):
                break
            else:
                for issue in self.issue_reports:
                    i, line = issue
