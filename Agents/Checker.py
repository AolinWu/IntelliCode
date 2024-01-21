import abc
from typing import List

from llm.api import LLMApi

class IssueReports:
    def __init__(self):
        self.issues:List[str]
class Checker(metaclass=abc.ABCMeta):
    def __init__(self, api: LLMApi):
        self.api = api
        self.issue_reports: List[str] = list[str]()

    @abc.abstractmethod
    def check(self, response: str) -> bool:
        ...

    @abc.abstractmethod
    def revise(self, response: str, max_round: int) -> str:
        ...

    def clear_issue_reports(self):
        self.issue_reports.clear()

    def append_issue_report(self, issue: str):
        self.issue_reports.append(issue)

    def get_issue_report_by_index(self, index:int):
