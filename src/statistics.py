import csv
import time
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path


@dataclass
class Snapshot:
    pos: int = 0
    name: str = ""
    s_strength: int = 2
    e_strength: int = 3
    a_strength: int = 2
    seq_all_num: int = 0
    seq_executed_num: int = 0
    avg_len_of_all_seq: float = 0.0
    avg_len_of_executed_seq: float = 0.0
    C_1_way_all: int = 0
    C_1_way_executed: int = 0
    C_1_way_success: int = 0
    C_2_way_all: int = 0
    C_2_way_executed: int = 0
    C_2_way_success: int = 0
    t_way_to_covered: int = 0
    t_way_covered: int = 0
    req_num: int = 0
    req_num_all: int = 0
    req_20x_num: int = 0
    req_30x_num: int = 0
    req_40x_num: int = 0
    req_50x_num: int = 0
    req_60x_num: int = 0
    op_num: int = 0
    op_executed_num: int = 0
    op_success_num: int = 0
    llm_call: int = 0
    call_time: int = 0
    token_nums: int = 0
    money_cost: int = 0
    bug: int = 0


class Statistics:
    def __init__(self, config):
        self.start = time.time()
        self.name = config.exp_name
        self.s_s = config.s_strength
        self.e_s = config.e_strength
        self.a_s = config.a_strength
        self.budget = config.budget
        self.interval = config.interval
        self.next_pos = 0
        self.snapshot_file = Path(config.output_folder) / "snapshot.csv"
        self.report_file = Path(config.output_folder) / "report.csv"
        self._snapshot_list = []

        self.seq_all_num = 0  #
        self.seq_executed_num = 0  #
        self.sum_len_of_all_seq: int = 0  #
        self.sum_len_of_executed_seq: int = 0  #
        self.C_1_way_all: set = set()  #
        self.C_1_way_executed: set = set()
        self.C_1_way_success: set = set()
        self.C_2_way_all: set = set()  #
        self.C_2_way_executed: set = set()
        self.C_2_way_success: set = set()
        self.t_way_to_covered: int = 0  #
        self.t_way_covered: set = set()  #
        self.req_num: int = 0  #
        self.req_num_all: int = 0  #
        self.req_20x_num: int = 0  #
        self.req_30x_num: int = 0  #
        self.req_40x_num: int = 0  #
        self.req_50x_num: int = 0  #
        self.req_60x_num: int = 0  #
        self.op_num: set = set()  #
        self.op_executed_num: set = set()  #
        self.op_success_num: set = set()  #
        self.llm_call: int = 0  #
        self.call_time: int = 0  #
        self.token_nums: int = 0  #
        self.money_cost: int = 0  #
        self.bug: set = set()  #

    def update_llm_data(self, llm_call, call_time, token_nums, cost):
        self.llm_call += llm_call
        self.call_time += call_time
        self.token_nums += token_nums
        self.money_cost += cost

    def update_all_c_way(self, seq):
        self.C_1_way_all.update(self._compute_combinations(seq, 1))
        self.C_2_way_all.update(self._compute_combinations(seq, 2))

    def update_executed_c_way(self, seq):
        self.C_1_way_executed.update(self._compute_combinations(seq, 1))
        self.C_2_way_executed.update(self._compute_combinations(seq, 2))

    def update_success_c_way(self, seq):
        self.C_1_way_success.update(self._compute_combinations(seq, 1))
        self.C_2_way_success.update(self._compute_combinations(seq, 2))

    @staticmethod
    def _compute_combinations(seq, strength):
        covered = set()
        if len(seq) < strength:
            return covered
        for c in combinations(seq, strength):
            covered.add(tuple(c))
        return covered

    def dump_snapshot(self, force=False):
        pos = (time.time() - self.start) * 1.0 / self.budget
        if not force:
            if pos < self.next_pos:
                return
            while (time.time() - self.start) * 1.0 / self.budget > self.next_pos:
                self.next_pos += self.interval

        snapshot = Snapshot(pos,
                            self.name,
                            self.s_s,
                            self.e_s,
                            self.a_s,
                            self.seq_all_num,
                            self.seq_executed_num,
                            self.sum_len_of_all_seq * 1.0 / self.seq_all_num if self.sum_len_of_executed_seq > 0 else 0,
                            self.sum_len_of_executed_seq * 1.0 / self.seq_executed_num if self.sum_len_of_executed_seq > 0 else 0,
                            len(self.C_1_way_all),
                            len(self.C_1_way_executed),
                            len(self.C_2_way_success),
                            len(self.C_2_way_all),
                            len(self.C_2_way_executed),
                            len(self.C_2_way_success),
                            self.t_way_to_covered,
                            len(self.t_way_covered),
                            self.req_num,
                            self.req_num_all,
                            self.req_20x_num,
                            self.req_30x_num,
                            self.req_40x_num,
                            self.req_50x_num,
                            self.req_60x_num,
                            len(self.op_num),
                            len(self.op_executed_num),
                            len(self.op_success_num),
                            self.llm_call,
                            self.call_time,
                            self.token_nums,
                            self.money_cost,
                            len(self.bug))
        self._snapshot_list.append(snapshot)

    def write_report(self):
        self.dump_snapshot(True)

        if not self.snapshot_file.exists():
            with self.snapshot_file.open("a+") as fp:
                writer = csv.writer(fp, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

                # Write the header row
                header = Snapshot.__annotations__.keys()
                writer.writerow(header)

        if not self.report_file.exists():
            with self.report_file.open("a+") as fp:
                writer = csv.writer(fp, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

                # Write the header row
                header = Snapshot.__annotations__.keys()
                writer.writerow(header)

        with self.snapshot_file.open("a+") as fp:
            writer = csv.writer(fp, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

            # Write data rows
            for snapshot in self._snapshot_list:
                header = Snapshot.__annotations__.keys()
                row_data = [getattr(snapshot, field) for field in header]
                writer.writerow(row_data)

        with self.report_file.open("a+") as fp:
            writer = csv.writer(fp, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

            # Write data rows
            header = Snapshot.__annotations__.keys()
            snapshot = self._snapshot_list[-1]
            row_data = [getattr(snapshot, field) for field in header]
            writer.writerow(row_data)
