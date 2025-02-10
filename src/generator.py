import os
import random
import re
import shlex
import subprocess
from pathlib import Path
from typing import Dict, List

import chardet

from src.factor import Value
from src.nlp import Constraint


class ACTS:
    def __init__(self, data_path, jar):
        self._workplace = Path(data_path) / "acts"
        self.jar = jar
        if not self._workplace.exists():
            self._workplace.mkdir()

    @staticmethod
    def get_id(operation, param_name, domain_map):
        global_name = param_name
        for f in operation.get_leaf_factors():
            if f.name == param_name:
                global_name = f.get_global_name
                break
        index = domain_map.index(global_name)
        return "P" + str(index)

    @staticmethod
    def get_name(param_id: str, domain_map):
        index = int(param_id.lstrip("P"))
        return domain_map[index]

    def transformConstraint(self, operation, domain_map, paramNames, constraint: Constraint):
        cStr = constraint.toActs(operation, domain_map)
        if cStr is None:
            return ""
        for paramName in constraint.paramNames:
            pattern = r"\b" + paramName + r"\b"
            paramId = self.get_id(operation, paramName, paramNames)
            cStr = re.sub(re.compile(pattern), paramId, cStr)
        return eval(cStr)

    def writeInput(self, operation, domain_map, param_names, constraints, strength) -> Path:
        inputFile = self._workplace / "input.txt"
        with inputFile.open("w") as fp:
            fp.write(
                "\n".join(
                    ['[System]', '-- specify system name', 'Name: {}'.format("acts" + str(strength)), '',
                     '[Parameter]', '-- general syntax is parameter_name(type): value1, value2...\n'])
            )
            # write parameter ids
            for paramName, domain in domain_map.items():
                fp.write("{}(int):{}\n".format(self.get_id(operation, paramName, param_names),
                                               ",".join([str(i) for i in range(len(domain))])))

            fp.write("\n")
            # write constraints
            if len(constraints) > 0:
                fp.write("[Constraint]\n")
                for c in constraints:
                    [fp.write(ts + "\n") for ts in self.transformConstraint(operation, domain_map, param_names, c)]

        return inputFile

    def callActs(self, strength: int, inputFile) -> Path:
        outputFile = self._workplace / "output.txt"
        jarPath = Path(self.jar)
        algorithm = "ipog"

        # acts 的文件路径不可以以"\"作为分割符，会被直接忽略，"\\"需要加上repr，使得"\\"仍然是"\\".
        command = r'java -Dalgo={0} -Ddoi={1} -Doutput=csv -jar {2} {3} {4}'.format(algorithm, str(strength),
                                                                                    str(jarPath),
                                                                                    str(inputFile),
                                                                                    str(outputFile))
        stdout, stderr = subprocess.Popen(shlex.split(command, posix=False), stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE).communicate()
        encoding = chardet.detect(stdout)["encoding"]
        stdout.decode(encoding)
        return outputFile

    def parseOutput(self, outputFile: Path, domain_map, param_names, history_ca_of_current_op: List[dict]):
        with outputFile.open("r") as fp:
            lines = [line.strip("\n") for line in fp.readlines() if "#" not in line and len(line.strip("\n")) > 0]
        param_names = [self.get_name(paramId, param_names) for paramId in lines[0].strip("\n").split(",")]
        coverArray: List[Dict[str, Value]] = list()
        for line in lines[1:]:
            valueDict = dict()
            valueIndexList = line.strip("\n").split(",")
            for i, valueIndex in enumerate(valueIndexList):
                valueDict[param_names[i]] = domain_map[param_names[i]][int(valueIndex)]
            if "history_ca_of_current_op" in valueDict.keys():
                history_index = valueDict.pop("history_ca_of_current_op")
                valueDict.update(history_ca_of_current_op[history_index.val])
            coverArray.append(valueDict)

        return coverArray

    def process(self, operation, domain_map, constraints: List[Constraint], strength: int,
                history_ca_of_current_op: List[dict]):
        strength = min(strength, len(domain_map.keys()))
        param_names = list(domain_map.keys())
        inputFile = self.writeInput(operation, domain_map, param_names, constraints, strength)
        outputFile = self.callActs(strength, inputFile)
        return self.parseOutput(outputFile, domain_map, param_names, history_ca_of_current_op)
