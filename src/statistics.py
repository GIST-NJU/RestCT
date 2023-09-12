import csv
import time
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path


@dataclass
class Snapshot:
    pos: int = 0
    name: str = ""
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
    req_20x_num: int = 0
    req_30x_num: int = 0
    req_40x_num: int = 0
    req_50x_num: int = 0
    req_60x_num: int = 0
    op_num: int = 0
    op_executed_num: int = 0
    op_success_num: int = 0
    bug: int = 0


class Statistics:
    def __init__(self, name, budget, interval, output_folder):
        self.start = time.time()
        self.name = name
        self.budget = budget
        self.interval = interval
        self.next_pos = 0
        self.snapshot_file = Path(output_folder) / "snapshot.csv"
        self.report_file = Path(output_folder) / "report.csv"
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
        self.t_way_covered: int = 0  #
        self.req_num: int = 0  #
        self.req_20x_num: int = 0  #
        self.req_30x_num: int = 0  #
        self.req_40x_num: int = 0  #
        self.req_50x_num: int = 0  #
        self.req_60x_num: int = 0  #
        self.op_num: set = set()  #
        self.op_executed_num: set = set()  #
        self.op_success_num: set = set()  #
        self.bug: set = set()  #

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

    def dump_snapshot(self):
        pos = (time.time() - self.start) * 1.0 / self.budget
        if pos < self.next_pos:
            return
        while (time.time() - self.start) * 1.0 / self.budget > self.next_pos:
            self.next_pos += self.interval

        snapshot = Snapshot(pos,
                            self.name,
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
                            self.t_way_covered,
                            self.req_num,
                            self.req_20x_num,
                            self.req_30x_num,
                            self.req_40x_num,
                            self.req_50x_num,
                            self.req_60x_num,
                            len(self.op_num),
                            len(self.op_executed_num),
                            len(self.op_success_num),
                            len(self.bug))
        self._snapshot_list.append(snapshot)

    def write_report(self):
        self.dump_snapshot()

        with self.snapshot_file.open("w") as fp:
            writer = csv.writer(fp, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

            # Write the header row
            header = Snapshot.__annotations__.keys()
            writer.writerow(header)

            # Write data rows
            for snapshot in self._snapshot_list:
                row_data = [getattr(snapshot, field) for field in header]
                writer.writerow(row_data)

        with self.report_file.open("w") as fp:
            writer = csv.writer(fp, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

            # Write the header row
            header = Snapshot.__annotations__.keys()
            writer.writerow(header)

            # Write data rows
            snapshot = self._snapshot_list[-1]
            row_data = [getattr(snapshot, field) for field in header]
            writer.writerow(row_data)
