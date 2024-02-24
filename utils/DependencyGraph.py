import os.path
from enum import Enum
from typing import Literal, List, Dict
from graphviz import Digraph

from llm import PROJECT_DIR
import json

from utils.util import YamlReader, ContentExtractor
import re


class CodeEntityType(Enum):
    Package = 0
    Class = 1
    Function = 2


class Edge:
    def __init__(self, from_entity, to_entity, desc: str = None):
        self.from_entity = from_entity
        self.to_entity = to_entity
        self.desc = desc

    def get_desc(self):
        return self.desc

    def get_from_entity(self):
        return self.from_entity

    def get_to_entity(self):
        return self.to_entity


class CodeEntity:
    def __init__(self, entity_name:str ,entity_type: CodeEntityType = None, code_definition: str = None, code_desc: str = None,
                 code_body: str = None,
                 sub_entities: List = None,
                 in_edges: List[Edge] = None, out_edges: List[Edge] = None, parent_code_entity=None,
                 dependency_graph=None):
        self.entity_name=entity_name
        self.entity_type = entity_type
        self.code_definition = code_definition
        self.code_desc = code_desc
        self.code_body = code_body
        self.sub_entities = sub_entities
        self.in_edges = in_edges
        self.out_edges = out_edges
        self.parent_code_entity = parent_code_entity
        self.dependency_graph = dependency_graph

    def add_in_edge(self, in_edge: Edge):
        if self.in_edges:
            self.in_edges.append(in_edge)
        else:
            self.in_edges = [in_edge]

    def add_out_edge(self, out_edge: Edge):
        if self.out_edges:
            self.out_edges.append(out_edge)
        else:
            self.out_edges = [out_edge]

    def add_to_entity(self, to_entity):
        self.add_out_edge(Edge(self, to_entity))

    def add_from_entity(self, from_entity):
        self.add_in_edge(Edge(from_entity, self))

    def get_in_degree(self) -> int:
        return len(self.in_edges)

    def get_entity_name(self):
        return self.entity_name

    def get_entity_type(self):
        return self.entity_type

    def get_code_body(self):
        return self.code_body

    def get_code_definition(self):
        return self.code_definition

    def get_code_desc(self):
        return self.code_desc

    def get_parent_code_entity(self):
        return self.parent_code_entity

    def get_dependency_graph(self):
        return self.dependency_graph

    def get_to_entity_by_index(self, index: int):
        return self.out_edges[index].to_entity

    def get_from_entity_by_index(self, index: int):
        return self.in_edges[index].from_entity

    def del_to_entity_by_index(self, index: int):
        del self.out_edges[index]

    def del_from_entity_by_index(self, index: int):
        del self.in_edges[index]

    def set_

    def set_code_body(self, code_body: str):
        self.code_body = code_body

    def set_code_definition(self, code_definition: str):
        self.code_definition = code_definition

    def set_entity_type(self, entity_type: CodeEntityType):
        self.entity_type = entity_type

    def set_sub_entities(self, sub_entities: List):
        self.sub_entities = sub_entities

    def add_sub_entity(self, sub_entity):
        if self.sub_entities:
            self.sub_entities.append(sub_entity)
        else:
            self.sub_entities = [sub_entity]

    def set_in_edges(self, in_edges: List[Edge]):
        self.in_edges = in_edges

    def set_out_edges(self, out_edges: List[Edge]):
        self.out_edges = out_edges

    def set_parent_entity(self, parent_code_entity):
        self.parent_code_entity = parent_code_entity

    def set_dependency_graph(self, dependency_graph):
        self.dependency_graph = dependency_graph


class DependencyGraph:
    def __init__(self, entities: List[CodeEntity]):
        self.entities = entities

    def append_entity(self, entity: CodeEntity):
        self.entities.append(entity)

    def top_sort_entities(self) -> List[CodeEntity]:
        in_degrees: Dict[CodeEntity, int] = dict[CodeEntity, int]()
        entities_queue: List[CodeEntity] = []
        head = 0
        for entity in self.entities:
            in_degrees[entity] = entity.get_in_degree()
        for entity in self.entities:
            if in_degrees[entity] == 0:
                entities_queue.append(entity)
        while head < len(entities_queue):
            from_entity = entities_queue[head]
            head = head + 1
            for out_edge in from_entity.out_edges:
                to_entity = out_edge.to_entity
                in_degrees[to_entity] = in_degrees[to_entity] - 1
                if in_degrees[to_entity] == 0:
                    entities_queue.append(to_entity)
        return entities_queue

    def graph_visualize(self, project_name: str, format: str = 'png'):
        assert format in ['png', 'jpg', 'svg'], f'do not support graph format {format}'
        path = os.path.join(PROJECT_DIR, 'workingspace', project_name + '.' + format)
        graph = Digraph(name=project_name)
        entities_with_index: Dict[CodeEntity, int] = Dict[CodeEntity, int]()
        for i, entity in enumerate(self.entities):
            graph.node(str(i), entity.get_entity_definition())
            entities_with_index[entity] = i
        for entity, index in entities_with_index.items():
            for edge in entity.out_edges:
                to_entity = edge.to_entity
                graph.edge(str(index), str(entities_with_index[to_entity]))
        graph.render(filename=path, format=format, view=True)

    @staticmethod
    def create_graph_from_json(dependency_json_file_path: str, code_entities: List[CodeEntity]):
        assert os.path.exists(dependency_json_file_path), f'{dependency_json_file_path} does not exits'
        graph: Dict[str, List[Dict[str, str]]] = None
        with open(dependency_json_file_path, 'r') as f:
            graph = json.load(f)
        for code_entity in code_entities:



    @staticmethod
    def create_entities_from_steps(plan_steps_file: str) -> List[CodeEntity]:
        assert os.path.exists(plan_steps_file), f'{plan_steps_file} does not exits'
        assert plan_steps_file.endswith('.yaml'), f'does not support file format {plan_steps_file}'
        code_entities: List[CodeEntity] = []
        steps: List[str] = YamlReader.read(plan_steps_file)
        for step in steps:
            code_entity = ContentExtractor.extract_code_entity_from_step(step)
            code_entities.append(code_entity)
        return code_entities

    @staticmethod
    def _code_entities_to_dict(code_entities:List[CodeEntity]) -> Dict[str]:
        code_entities_dict: Dict[str, CodeEntity] = {}
        for code_entity in code_entities:
            code_entities_dict[code_entity.code_definition]=code_entity
        return code_entities_dict

