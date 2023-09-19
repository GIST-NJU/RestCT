import sys
from pathlib import Path
from typing import Set

from loguru import logger

from src.Dto.parameter import Example
from src.ca import CA
from src.controller import RemoteController
from src.openapiParser import Parser
from src.sca import SCA
from src.statistics import Statistics


class RestCT:
    def __init__(self, config):
        self._config = config
        self._logger = logger
        self._statistics = Statistics(config)

        self._seq_set: Set[tuple] = set()

        self._controller = None
        if self._config.forwarding_url is not None and len(self._config.forwarding_url) > 0:
            self._controller = RemoteController(config.forwarding_url)

        self._update_log_config()

        json_parser = Parser(logger, forwarding_url=self._config.forwarding_url)
        json_parser.parse()
        self._operations = json_parser.operations
        self._statistics.op_num.update(self._operations)

        self._sca = SCA(self._config.s_strength, self._operations, self._statistics)

        self._ca = CA(self._config.dataPath,
                      self._config.jar,
                      self._config.a_strength,
                      self._config.s_strength,
                      query_auth=self._config.query,
                      header_auth=self._config.header,
                      stat=self._statistics)

    def _update_log_config(self):
        loggerPath = Path(self._config.dataPath) / "log/log_{time}.log"
        logger.remove(0)
        logger.add(loggerPath.as_posix(), rotation="100 MB",
                   format="<level>{level: <6}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
        logger.add(sys.stderr,
                   format="<level>{level: <6}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
        # logger.add(loggerPath.as_posix(), rotation="100 MB",
        #            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | - "
        #                   "<level>{message}</level>")
        # logger.add(sys.stderr,
        #            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | - "
        #                   "<level>{message}</level>")

    def _before_testcase(self):
        if self._controller is not None:
            self._controller.register_testcase(logger)

    def _after_testcase(self):
        if self._controller is not None:
            self._controller.stop_testcase(logger)

    def run(self):
        self._statistics.dump_snapshot()
        self._logger.info("operations: {}".format(len(self._operations)))
        self._logger.info("examples found: {}".format(len(Example.members)))

        sequences = []
        while not self._sca.is_all_covered():
            sequences.append(self._sca.build_one_sequence())
            self._statistics.dump_snapshot()
            # self._before_testcase()

        for sequence in sorted(sequences, key=lambda s: len(s)):
            flag = self._ca.handle(sequence, self._config.budget)
            # self._after_testcase()

            if not flag:
                break

        # self._statistics.stop_test()
        self._statistics.write_report()
