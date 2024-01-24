import os.path
from typing import Literal, List, Dict
from graphviz import Digraph

from llm import PROJECT_DIR

CodeEntityType = Literal['class', 'function']


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
    def __init__(self, entity_type: CodeEntityType = None, definition: str = None, desc: str = None,
                 code_body: str = None,
                 sub_entities: List = None,
                 in_edges: List[Edge] = None, out_edges: List[Edge] = None):
        self.entity_type = entity_type
        self.definition = definition
        self.desc = desc
        self.code_body = code_body
        self.sub_entities = sub_entities
        self.in_edges = in_edges
        self.out_edges = out_edges

    def add_in_edge(self, in_edge: Edge):
        self.in_edges.append(in_edge)

    def add_out_edge(self, out_edge: Edge):
        self.out_edges.append(out_edge)

    def add_to_entity(self, to_entity):
        self.add_out_edge(Edge(self, to_entity))

    def add_from_entity(self, from_entity):
        self.add_in_edge(Edge(from_entity, self))

    def get_in_degree(self) -> int:
        return len(self.in_edges)

    def get_entity_type(self):
        return self.entity_type

    def get_code_body(self):
        return self.code_body

    def get_to_entity_by_index(self, index: int):
        return self.out_edges[index].to_entity

    def get_from_entity_by_index(self, index: int):
        return self.in_edges[index].from_entity

    def del_to_entity_by_index(self, index: int):
        del self.out_edges[index]

    def del_from_entity_by_index(self, index: int):
        del self.in_edges[index]

    def get_entity_definition(self):
        return self.definition

    def set_code_body(self,code_body:str):
        self.code_body=code_body


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
    def create_graph_from_json():
