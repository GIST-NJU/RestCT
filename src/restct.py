import time
import sys
from loguru import logger
from pathlib import Path
from typing import Set
from src.openapiParser import Parser
from src.Dto.operation import Operation
from src.Dto.parameter import Example
from src.ca import CA
from src.sca import SCA
from src.controller import RemoteController
# from src.statistics import Statistics
from typing import List


class RestCT:
    def __init__(self, config):
        self._config = config
        self._logger = logger
        # self._statistics = Statistics(config.dataPath)

        self._seq_set: Set[tuple] = set()

        self._controller = None
        if self._config.forwarding_url is not None and len(self._config.forwarding_url) > 0:
            self._controller = RemoteController(config.forwarding_url)

        self._update_log_config()

        json_parser = Parser(logger, forwarding_url=self._config.forwarding_url)
        json_parser.parse()
        self._operations = json_parser.operations

    def _update_log_config(self):
        loggerPath = Path(self._config.dataPath) / "log/log_{time}.log"
        self._logger.remove(0)
        self._logger.add(loggerPath.as_posix(), rotation="100 MB",
                         format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | - "
                                "<level>{message}</level>")
        self._logger.add(sys.stderr,
                         format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | - "
                                "<level>{message}</level>")

    def _before_testcase(self):
        if self._controller is not None:
            self._controller.register_testcase(logger)

    def _after_testcase(self):
        if self._controller is not None:
            self._controller.stop_testcase(logger)

    def run(self):
        self._logger.info("operations: {}".format(len(self._operations)))
        self._logger.info("examples found: {}".format(len(Example.members)))

        # self._statistics.start_test()

        sca = SCA(self._config.s_strength, self._operations)
        # self._statistics.seq_to_covered = len(sca.uncoveredSet)

        ca = CA(self._config.dataPath,
                self._config.jar,
                self._config.a_strength,
                self._config.s_strength,
                query_auth=self._config.query,
                header_auth=self._config.header)

        sequences = []
        while not sca.is_all_covered():
            sequences.append(sca.build_one_sequence())

            # self._before_testcase()

        for sequence in sorted(sequences, key=lambda s: len(s)):
            flag = ca.handle(sequence, self._config.budget)

            # self._after_testcase()

            if not flag:
                break

        # self._statistics.stop_test()
        # self._statistics.report()
