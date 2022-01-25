import time
from typing import List, Set, Tuple
from src.Dto.operation import Operation
from enum import Enum
from src.Dto.keywords import Method
from itertools import groupby, permutations, combinations
from random import choice


class Node:
    def __init__(self, operations: List[Operation]):
        self.operations: List[Operation] = operations

        # resource states
        self.state = Resource.NoExist if Method.POST in self.methodSet else Resource.Exist

        self.successors: List[Node] = list()
        self.predecessor: Node = None

    @property
    def methodSet(self) -> Set[Method]:
        return {op.method for op in self.operations}

    def haveMethod(self, method: Method):
        return method in self.methodSet

    def findOperation(self, method: Method):
        for operation in self.operations:
            if operation.method is method:
                return operation

    def isRoot(self):
        """is it root node ?"""
        return len(self.methodSet) == 0

    def havePredecessor(self):
        return self.predecessor is not None

    def haveSuccessor(self):
        return not len(self.successors)

    @property
    def url(self):
        return self.operations[0].url

    @property
    def splittedUrl(self) -> Set[Tuple[str, int]]:
        return self.operations[0].splittedUrl


class Resource(Enum):
    NoExist = 0
    Exist = 1
    Destroy = -1


class Graph:
    """graph structure"""

    def __init__(self):
        self.root = Node(list())
        self.nodes = dict()

    def insert(self, newNode: Node, predecessor: Node = None):
        """
        :param newNode: node to be inserted
        :param predecessor: parent node
        :return:
        """
        if predecessor is None:
            predecessor = self.root

        insertFlag = True
        if predecessor.isRoot() or newNode.splittedUrl > predecessor.splittedUrl:
            for successor in predecessor.successors:
                if newNode.splittedUrl > successor.splittedUrl:
                    self.insert(newNode, successor)
                    insertFlag = False
        if insertFlag:
            if len(predecessor.successors) > 0:
                nodesModified = list()
                for successor in predecessor.successors:
                    if newNode.splittedUrl < successor.splittedUrl:
                        nodesModified.append(successor)
                for curNode in nodesModified:
                    curNode.predecessor = newNode
                    newNode.successors.append(curNode)
                    predecessor.successors.remove(curNode)
            predecessor.successors.append(newNode)
            newNode.predecessor = predecessor

    def change(self, opsToAdd: List[Operation]):
        for operation in opsToAdd:
            node = self.findNode(operation.url)
            if operation.method is Method.POST:
                assert node.state is Resource.NoExist
                node.state = Resource.Exist
            elif operation.method is Method.DELETE:
                assert node.state is Resource.Exist
                node.state = Resource.Destroy
            else:
                continue

    def findNode(self, url: str):
        assert url in self.nodes.keys()
        return self.nodes.get(url)

    @staticmethod
    def findPredecessors(node):
        predecessors = list()
        curNode = node
        while True:
            preNode = curNode.predecessor
            if preNode.isRoot():
                return predecessors
            else:
                predecessors.insert(0, preNode)
                curNode = preNode

    @classmethod
    def buildGraph(cls, operations: List[Operation]):
        graph = cls()

        operationSorted = sorted(operations, key=lambda op: op.url)
        for url, group in groupby(operationSorted, key=lambda op: op.url):
            node = Node(list(group))
            graph.nodes[url] = node
            graph.insert(node, None)
        return graph


class SCA:
    members: List[Tuple[Operation]] = list()

    def __init__(self):
        from src.restct import Config
        self._strength = min(Config.s_strength, len(Operation.members))
        self.uncoveredSet = self._collectUncoveredSet()

        # start time
        self.time = time.time()

    def _collectUncoveredSet(self):
        """get all combinations to be covered"""
        uncoveredSet = set()
        for p in permutations(Operation.members, self._strength):
            if self._isValidP(p):
                uncoveredSet.add(p)
        return uncoveredSet

    @staticmethod
    def _isValidP(permutation):
        """check the permutation"""
        for index, operation in enumerate(permutation):
            # POST Constraint
            if operation.method is Method.POST:
                for loc in range(index):
                    if operation.splittedUrl <= permutation[loc].splittedUrl:
                        return False
            # DELETE Constraint
            if operation.method is Method.DELETE:
                for loc in range(index + 1, len(permutation)):
                    if operation.splittedUrl <= permutation[loc].splittedUrl:
                        return False
        return True

    @staticmethod
    def _getCandidates(graph: Graph):
        candidates = set()
        stack = [graph.root]
        while len(stack):
            curNode = stack.pop()
            for successor in curNode.successors:
                if successor.state is not Resource.Destroy:
                    candidates.update(successor.operations)
                    stack.insert(0, successor)
        return candidates

    def _setPriorities(self, candidates, sequence, length):
        if len(candidates) == 0:
            return 0, list()
        candidatesWithCount: List[Tuple[Operation, int]] = [(op, self._countPWithOp(op, sequence, length)) for op in
                                                            candidates]
        maxCount = 0
        targetOpList = list()
        for op, count in candidatesWithCount:
            if count == maxCount:
                targetOpList.append(op)
            elif count > maxCount:
                targetOpList.clear()
                targetOpList.append(op)
                maxCount = count
            else:
                continue
        return maxCount, targetOpList

    def _countPWithOp(self, op, seq, length):
        """compute how many tuples will be covered by append op to seq"""
        assert length <= len(seq)
        combinationsWithOp = {p + (op,) for p in combinations(seq, r=length)}
        assert 0 <= length <= self._strength
        if length == self._strength - 1:
            return len(self.uncoveredSet & combinationsWithOp)
        else:
            count = 0
            for uncovered in self.uncoveredSet:
                if uncovered[:(length + 1)] in combinationsWithOp:
                    count += 1
            return count

    @staticmethod
    def _genDependOps(operation: Operation, graph: Graph):
        """generate extra operation sequence before appending selected op to satisfied the constraints"""
        opsToAdd = list()
        node: Node = graph.findNode(operation.url)
        while True:
            if node.isRoot():
                break
            if node.state is Resource.NoExist:
                assert Method.POST in node.methodSet
                opsToAdd.insert(0, node.findOperation(Method.POST))
            assert node.state is not Resource.Destroy
            node = node.predecessor
        if operation not in opsToAdd:
            opsToAdd.append(operation)
        return opsToAdd

    def buildSequence(self) -> Tuple[Operation]:
        sequence: List[Operation] = list()
        graph = Graph.buildGraph(Operation.members)
        loopFlag = True

        while loopFlag:
            for childLength in range(self._strength - 1, -1, -1):
                if childLength > len(sequence):
                    continue
                candidates = SCA._getCandidates(graph) - set(sequence)
                maxCount, operationList = self._setPriorities(candidates, sequence, childLength)
                if maxCount > 0:
                    selectedOp = choice(operationList)
                    opsToAdd = SCA._genDependOps(selectedOp, graph)
                    graph.change(opsToAdd)
                    sequence.extend(opsToAdd)
                    break
                else:
                    if childLength == 0:
                        loopFlag = False

        # update uncovered set
        newCovered = set(combinations(sequence, self._strength))
        self.uncoveredSet -= newCovered
        SCA.members.append(tuple(sequence))
        return tuple(sequence)
