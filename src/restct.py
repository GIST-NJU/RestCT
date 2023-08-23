import time
import sys
from loguru import logger
from pathlib import Path
from src.parseJson import parse
from src.Dto.operation import Operation
from src.Dto.parameter import Example
from src.algorithm import RESTCT, Report
from src.ca import CA
from src.sca import SCA
from src.controller import RemoteController


class RestCT:
    outputFolder = ""
    dataPath = ""
    columnId = ""
    SStrength = 0
    EStrength = 0
    AStrength = 0
    budget = 0

    def __init__(self,
                 config,
                 controller: RemoteController,
                 specified_url: str = "http://localhost:8080/forward"
                 ):
        self._config = config
        self._sca: SCA = SCA()
        self._ca = CA(self._config)

        self._controller = controller
        self._specified_url = specified_url

    """
    on starting a test case
    """

    def _before_testcase(self):
        self._controller.register_testcase()

    """
    on completing a test 
    """

    def _after_testcase(self):
        self._controller.stop_testcase()

    def run(self):
        start_time = time.time()
        loggerPath = Path(RESTCT.dataPath) / "log/log_{time}.log"
        logger.remove(0)
        logger.add(loggerPath.as_posix(), rotation="100 MB",
                   format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | - <level>{message}</level>")
        logger.add(sys.stderr,
                   format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | - <level>{message}</level>")
        parse(self._specified_url)

        logger.info("operations: {}".format(len(Operation.members)))
        logger.info("examples found: {}".format(len(Example.members)))
        Report.Uncovered = len(self._sca.uncoveredSet)
        while len(self._sca.uncoveredSet) > 0:
            sequence = self._sca.buildSequence()
            logger.info("uncovered combinations: {}, sequence length: {}".format(len(self._sca.uncoveredSet), len(sequence)))

        for sequence in sorted(SCA.members, key=lambda item: len(item)):
            flag = self._ca.handle(sequence, RESTCT.budget - (time.time() - start_time))
            self._controller.stop_testcase()
            if not flag:
                break
        Report.Cost = time.time() - start_time
        Report.report(RESTCT.outputFolder)
