from typing import List, Set
from itertools import permutations, combinations
from random import choice
from typing import List, Set

from loguru import logger

from src.Dto.keywords import Method
from src.Dto.operation import Operation


class SemanticValidator:
    """handle CURD semantic, and other sequence dependencies in the future"""

    @staticmethod
    def _validate_post(post: Operation, seq_before: List[Operation]):
        for pre in seq_before:
            if post.path.is_ancestor_of(pre.path):
                return False

        return True

    @staticmethod
    def _validate_delete(delete: Operation, seq_after: List[Operation]):
        for aft in seq_after:
            if delete.path.is_ancestor_of(aft.path):
                return False

        return True

    @staticmethod
    def is_valid(permutation):
        for index, operation in enumerate(permutation):
            if operation.method is Method.POST and not SemanticValidator._validate_post(operation, permutation[:index]):
                return False
            elif operation is Method.DELETE and not SemanticValidator._validate_delete(operation,
                                                                                       permutation[index + 1:]):
                return False
        return True


class SCA:
    def __init__(self, strength, operations):
        self._strength = min(strength, len(operations))
        self._operations: Set[Operation] = operations

        self._uncovered = self._compute_all_combinations()

    def _compute_all_combinations(self):
        cover = set()
        for p in permutations(self._operations, self._strength):
            if SemanticValidator.is_valid(p):
                cover.add(p)
        return cover

    def build_one_sequence(self):
        seq: List[Operation] = list()

        is_loop = True
        while is_loop:
            # c_size: the size of a combination
            for c_size in range(self._strength - 1, -1, -1):
                if c_size > len(seq):
                    continue

                candidates = self._get_candidates(seq)
                if candidates == 0:
                    continue

                max_count, op_list = self._find_best(candidates, seq, c_size)
                if max_count > 0:
                    selected = choice(op_list)
                    op_list_to_add = self._retrieve_dependent_ops(selected, seq)
                    seq.extend(op_list_to_add)
                    break
                else:
                    if c_size == 0:
                        is_loop = False

        self._update_uncovered(seq)
        logger.info(
            "uncovered combinations: {}, sequence length: {}".format(len(self._uncovered), len(seq)))
        return seq

    def _update_uncovered(self, sequence: List[Operation]):
        covered = set(combinations(sequence, self._strength))
        self._uncovered -= covered

    def _retrieve_dependent_ops(self, op: Operation, seq: List[Operation]):
        result: List[Operation] = []
        for candidate in self._operations:
            if candidate in seq or candidate == op:
                continue
            if candidate.method is Method.POST and candidate.path.is_ancestor_of(op.path):
                result.append(candidate)
        result = sorted(result, key=lambda o: len(o.path.elements))
        result.append(op)
        return result

    def _get_candidates(self, seq: List[Operation]):
        candidates = set()

        for op in self._operations:
            if op in seq:
                continue
            is_destroy = False
            for member in seq:
                if member.method is Method.DELETE and member.path.is_ancestor_of(op.path):
                    is_destroy = True
                    break

            if not is_destroy:
                candidates.add(op)

        return candidates

    def _find_best(self, candidates, seq, c_size):
        if len(candidates) == 0:
            return 0, []

        results = list()
        max_count = 0
        for c in candidates:
            count = self._count_permutation_with_op(c, seq, c_size)
            if count == max_count:
                results.append(c)
            elif count > max_count:
                results.clear()
                results.append(c)
                max_count = count
            else:
                continue
        return max_count, results

    def _count_permutation_with_op(self, op, seq, c_size):
        p_list = {p + (op,) for p in combinations(seq, c_size)}
        if c_size == self._strength - 1:
            return len(self._uncovered & p_list)
        else:
            count = 0
            for uc in self._uncovered:
                if uc[:(c_size + 1)] in p_list:
                    count += 1
        return count

    def is_all_covered(self):
        return len(self._uncovered) == 0
