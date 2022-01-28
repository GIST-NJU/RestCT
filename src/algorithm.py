import time
from pathlib import Path
from loguru import logger
from src.parseJson import parse
from src.generateSCA import SCA
from src.generateCA import CA, SendRequest
from src.Dto.parameter import Example
from itertools import combinations
from src.Dto.operation import Operation
import sys


class Report:
    StillUncovered = 0
    Uncovered = 0
    Cost = 0

    @staticmethod
    def getSequenceInfo():
        """Get The Number of Operation Sequences Exercised (Seq) and Their Average Length (Len)"""
        return len(SCA.members), sum([len(m) for m in SCA.members]) / len(SCA.members)

    @staticmethod
    def getSequenceTested():
        """
        Compute the proportion of 1-way and 2-way sequences that are actually tested
        @:return: 1-way tested, 1-way all,  2-way tested, 2-way all, still uncovered SStrength-way due to timeout, all uncovered SStrength-way
        """
        return Report._computeCombinations(CA.successSet, 1), \
               Report._computeCombinations(SCA.members, 1), \
               Report._computeCombinations(CA.successSet, 2), \
               Report._computeCombinations(SCA.members, 2), \
               Report.Uncovered

    @staticmethod
    def getBugInfo():
        return len(CA.bugList)

    @staticmethod
    def getRestCallNumber():
        return SendRequest.callNumber

    @staticmethod
    def getCost():
        """
        :return: in minutes
        """
        return Report.Cost / 60

    @staticmethod
    def _computeCombinations(seqSet, strength):
        coveredSet = set()
        for seq in seqSet:
            if len(seq) < strength:
                continue
            for c in combinations(seq, strength):
                coveredSet.add(tuple(c))
        return len(coveredSet)

    @staticmethod
    def report(outputFolder):
        seq, length = Report.getSequenceInfo()
        c_1, c_1_a, c_2, c_2_a, a_c = Report.getSequenceTested()
        bug = Report.getBugInfo()
        total = Report.getRestCallNumber()
        cost = Report.getCost()

        file = Path(outputFolder) / "statistics.csv"
        columns = ["columnId", "SStrength", "EStrength", "AStrength", "Seq", "Len", "C_1_way", "C_2_way", "All C_SStrength_way", "Bug",
                   "Total", "Cost"]
        if not file.exists():
            with file.open("w") as fp:
                fp.write(",".join(columns))
                fp.write("\n")

        data = "{},{},{},{},{},{:.2f},{:.2f},{:.2f},{},{},{},{:.2f}\n".format(RESTCT.columnId, RESTCT.SStrength, RESTCT.EStrength, RESTCT.AStrength, seq, length, c_1 / c_1_a, c_2 / c_2_a, a_c, bug, total, cost)
        with file.open("a") as fp:
            fp.write(data)
            logger.info("{},{},{},{},{},{:.2f},{:.2f},{:.2f},{},{},{},{:.2f}\n".format(RESTCT.columnId, RESTCT.SStrength, RESTCT.EStrength, RESTCT.AStrength, seq, length, c_1 / c_1_a, c_2 / c_2_a, a_c, bug, total, cost))


class RESTCT:
    outputFolder = ""
    dataPath = ""
    columnId = ""
    SStrength = 0
    EStrength = 0
    AStrength = 0
    budget = 0

    @staticmethod
    def run():
        startTime = time.time()
        loggerPath = Path(RESTCT.dataPath) / "log/log_{time}.log"
        logger.remove(0)
        logger.add(loggerPath.as_posix(), rotation="100 MB",
                   format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | - <level>{message}</level>")
        logger.add(sys.stderr,
                   format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | - <level>{message}</level>")
        parse()
        logger.info("operations: {}".format(len(Operation.members)))
        logger.info("examples found: {}".format(len(Example.members)))
        sca = SCA()
        Report.Uncovered = len(sca.uncoveredSet)
        while len(sca.uncoveredSet) > 0:
            sequence = sca.buildSequence()
            logger.info("uncovered combinations: {}, sequence length: {}".format(len(sca.uncoveredSet), len(sequence)))

        for sequence in sorted(SCA.members, key=lambda item: len(item)):
            ca = CA(sequence)
            flag = ca.main(RESTCT.budget - (time.time() - startTime))
            if not flag:
                break
        Report.Cost = time.time() - startTime
        Report.report(RESTCT.outputFolder)
