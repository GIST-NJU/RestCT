import sys
import time
from loguru import logger
from pathlib import Path

from src.ca import CA
from src.info import RuntimeInfoManager
from src.sequence import SCA
from src.swagger import SwaggerParser


class Initialize:
    def __init__(self, config):
        self._config = config
        self._logger = logger

        self._update_log_config()

        swagger_parser = SwaggerParser(self._config)
        self._operations = swagger_parser.extract()

        self._manager = RuntimeInfoManager(config)

    def _update_log_config(self):
        loggerPath = Path(self._config.data_path) / "log/log_{time}.log"
        logger.remove(0)
        logger.add(loggerPath.as_posix(), rotation="100 MB",
                   format="<level>{level: <6}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
        logger.add(sys.stderr,
                   format="<level>{level: <6}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")


class RestCT(Initialize):
    def __init__(self, config):
        super().__init__(config)

        self._sca = SCA(self._config.s_strength, self._operations)

        self._ca = CA(self._config, manager=self._manager, operations=self._operations)

    def run(self):
        self._logger.info("operations: {}".format(len(self._operations)))
        self._ca.start_time = time.time()

        # round 1: cover all operations
        sequences = []
        while not self._sca.is_all_covered():
            sequences.append(self._sca.build_one_sequence())

        for index, sequence in enumerate(sorted(sequences, key=lambda s: len(s))):
            logger.debug(f"{index+1}-th sequence : {sequence}")
            flag = self._ca.handle(sequence)
            if not flag:
                break