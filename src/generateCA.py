import json
import random
import time
import re
import requests
import subprocess
import shlex
import chardet
from src.Dto.keywords import Loc, DataType, Method
from pathlib import Path
from typing import List, Tuple, Dict, Union, Set
from src.Dto.operation import Operation, Response
from src.Dto.constraint import Constraint, Processor
from src.Dto.parameter import AbstractParam, ValueType
from collections import defaultdict
from loguru import logger


class CA:
    # value used in success http calls. key: operation._repr_+paramName
    okValueDict: Dict[str, List[Tuple[ValueType, object]]] = defaultdict(list)
    # success http call sequence. key: url, value: last operation's parameters and values
    reuseEssentialSeqDict: Dict[Tuple[str], List[Dict[str, Tuple[ValueType, Union[str, int, float, list, dict]]]]] = defaultdict(list)
    reuseAllSeqDict: Dict[Tuple[str], List[Dict[str, Tuple[ValueType, object]]]] = defaultdict(list)
    # bug: {url: , method: , parameters: , statusCode: , response: , sequence}
    bugList: List[Dict[str, Union[str, dict, int, list]]] = list()
    # seq actually tested, return 20X or 500
    successSet: Set = set()

    def __init__(self, sequence: Tuple[Operation]):
        # start time
        self.time = time.time()

        self._sequence = sequence

        # response chain
        self._maxChainItems = 3
        self._responseChains: List[Dict[str, object]] = [dict()]
        # idCount: delete created resource
        self._idCounter: List[(int, str)] = list()

        from src.restct import Config
        self._aStrength = Config.a_strength  # cover strength for all parameters
        self._eStrength = Config.e_strength  # cover strength for essential parameters

        filePath = Path(Config.dataPath) / "unresolvedParams.json"
        if not filePath.exists():
            self._unresolvedParam = set()
        else:
            with filePath.open("r") as fp:
                self._unresolvedParam = set(json.load(fp).get("unresolvedParams", []))

    def main(self, budget) -> bool:
        for i, operation in enumerate(self._sequence):
            logger.debug("{}-th operation: {}*{}", i + 1, operation.method.value, operation.url)
            chainList = self.getChains()
            urlTuple = tuple([op.__repr__() for op in self._sequence[:i + 1]])
            while len(chainList):
                if time.time() - self.time > budget:
                    return False
                chain = chainList.pop(0)
                successUrlTuple = tuple([op.__repr__() for op in self._sequence[:i] if op.__repr__() in chain.keys()] + [operation.__repr__()])

                # solve constraints
                processor = Processor(operation.parameterList)
                constraints = processor.parse()
                operation.constraints.clear()
                operation.addConstraints(constraints)

                coverArray: List[Dict[str, Tuple[ValueType, object]]] = self.genEssentialParamsCase(operation, urlTuple, chain)
                logger.info("        {}-th operation essential parameters covering array size: {}, parameters: {}, constraints: {}".format(i + 1, len(coverArray), len(coverArray[0]), len(operation.constraints)))
                essentialSender = SendRequest(operation, coverArray, chain)
                statusCodes, responses = essentialSender.main()
                self._handleFeedback(chain, operation, statusCodes, responses, coverArray, successUrlTuple, False)
                eSuccessCodes = set(filter(lambda c: c in range(200, 300), statusCodes))
                bugCodes = set(filter(lambda c: c in range(500, 600), statusCodes))
                if len(eSuccessCodes) > 0:
                    self._saveSuccessSeq(successUrlTuple)
                elif len(bugCodes) > 0:
                    self._saveSuccessSeq(successUrlTuple)
                else:
                    pass

                coverArray: List[Dict[str, Tuple[ValueType, object]]] = self.genAllParamsCase(operation, urlTuple, chain)
                logger.info("        {}-th operation all parameters covering array size: {}, parameters: {}".format(i + 1, len(coverArray), len(coverArray[0])))
                logger.info("*" * 100)
                allSender = SendRequest(operation, coverArray, chain)
                statusCodes, responses = allSender.main()
                self._handleFeedback(chain, operation, statusCodes, responses, coverArray, successUrlTuple, True)

                successCodes = set(filter(lambda c: c in range(200, 300), statusCodes))
                bugCodes = set(filter(lambda c: c in range(500, 600), statusCodes))
                if len(successCodes) > 0:
                    self._saveSuccessSeq(successUrlTuple)
                    break
                elif len(bugCodes) > 0:
                    self._saveSuccessSeq(successUrlTuple)
                    break
                else:
                    if len(eSuccessCodes) == 0:
                        errorResponses = [responses[j] for j, sc in enumerate(statusCodes) if sc in range(400, 500)]
                        unresolvedParamList = processor.analyseError(errorResponses)
                        for up in unresolvedParamList:
                            if operation.__repr__() + up not in self._unresolvedParam:
                                self._unresolvedParam.add(operation.__repr__() + up)
                                removedCons = list()
                                for c in operation.constraints:
                                    if up in c.paramNames:
                                        removedCons.append(c)
                                for rc in removedCons:
                                    operation.constraints.remove(rc)
                                break
        logger.info("   unresolved parameters: {}".format(self._unresolvedParam))
        self.clearUp()
        return True

    @staticmethod
    def _saveSuccessSeq(successUrlTuple):
        CA.successSet.add(successUrlTuple)

    def clearUp(self):
        # clean resource created
        for iid, url in self._idCounter:
            resourceId = url.rstrip("/") + "/" + str(iid)
            try:
                requests.delete(url=resourceId, auth=Auth())
            except Exception:
                continue

        # save unresolved parameters
        from src.restct import Config
        filePath = Path(Config.dataPath) / "unresolvedParams.json"
        with filePath.open("w") as fp:
            data = {"unresolvedParams": list(self._unresolvedParam)}
            json.dump(data, fp)

    def _handleFeedback(self, chain, operation, statusCodes, responses, coverArray, urlTuple, isAll):
        for index, sc in enumerate(statusCodes):
            if sc < 300:
                CA._saveReuse(coverArray[index], urlTuple, isAll)
                CA._saveOkValue(operation.__repr__(), coverArray[index])
                self._saveChain(chain, operation.__repr__(), responses[index])
            if operation.method is Method.POST and sc < 300:
                self._saveIdCount(operation, responses[index])
            if sc in range(500, 600):
                CA._saveBug(operation.url, operation.method.value, coverArray[index], sc, responses[index], chain)

    def _saveIdCount(self, operation, response):
        if isinstance(response, dict):
            iid = response.get("id")
            try:
                self._idCounter.append((iid, operation.url))
            except TypeError:
                pass
        elif isinstance(response, list):
            for r in response:
                iid = r.get("id")
                try:
                    self._idCounter.append((int(iid), operation.url))
                except TypeError:
                    pass
        else:
            pass

    @staticmethod
    def _saveBug(url: str, method: str, parameters: dict, statusCode: int, response: Union[list, dict, str], chain: dict):
        opStrSet = {d.get("method") + d.get("url") + str(d.get("statusCode")) for d in CA.bugList}
        if method + url + str(statusCode) in opStrSet:
            return
        bugInfo = {
            "url": url,
            "method": method,
            "parameters": {paramName: (vt.value, v) for paramName, (vt, v) in parameters.items()},
            "statusCode": statusCode,
            "response": response,
            "responseChain": chain
        }
        CA.bugList.append(bugInfo)

        # save to json
        from src.restct import Config
        folder = Path(Config.dataPath) / "bug/"
        if not folder.exists():
            folder.mkdir(parents=True)
        bugFile = folder / "bug_{}.json".format(str(len(opStrSet)))
        with bugFile.open("w") as fp:
            json.dump(bugInfo, fp)

    @staticmethod
    def _saveReuse(case, urlTuple, isAll):
        if isAll:
            toDict = CA.reuseAllSeqDict
        else:
            toDict = CA.reuseEssentialSeqDict
        if len(toDict[urlTuple]) < 10:
            toDict[urlTuple].append(case)

    @staticmethod
    def _saveOkValue(opStr, case):
        for paramStr, value in case.items():
            paramId = opStr + paramStr
            if paramId not in CA.okValueDict.keys():
                CA.okValueDict[paramId].append(value)
            else:
                lst = CA.okValueDict.get(paramId)
                valueList = [v for _, v in lst]
                if len(lst) < 10 and value[1] not in valueList:
                    lst.append(value)
                else:
                    typeSet = {t for t, _ in lst}
                    if value[0] not in typeSet:
                        lst.append(value)

    def genEssentialParamsCase(self, operation, urlTuple, chain) -> List[Dict[str, Tuple[ValueType, Union[str, int, float, list, dict]]]]:
        essentialParamList: List[AbstractParam] = list(filter(lambda p: p.isEssential, operation.parameterList))
        if len(essentialParamList) == 0:
            return [{}]

        reuseSeq = CA.reuseEssentialSeqDict.get(urlTuple, list())

        if len(reuseSeq):
            # 执行过
            logger.debug("        use reuseSeq info: {}, parameters: {}", len(reuseSeq), len(reuseSeq[0].keys()))
            return reuseSeq
        else:
            paramList: List[AbstractParam] = list()
            for p in essentialParamList:
                paramList.extend(p.genDomain(operation.__repr__(), chain, CA.okValueDict))
            paramNames = [p.name for p in paramList if operation.__repr__() + p.name not in self._unresolvedParam]
            domains = [p.domain for p in paramList if operation.__repr__() + p.name not in self._unresolvedParam]

            logger.debug("        generate new domains...")
            for i, p in enumerate(paramNames):
                logger.debug("            {}: {} - {}", p, len(domains[i]), set([item[0].value for item in domains[i]]))
            try:
                acts = ACTS(paramNames, domains, operation.constraints, self._eStrength)
            except Exception:
                return [{}]
            else:
                return acts.main()

    def genAllParamsCase(self, operation, urlTuple, chain) -> List[Dict[str, Tuple[ValueType, Union[str, int, float, list, dict]]]]:
        allParamList = operation.parameterList
        if len(allParamList) == 0:
            return [{}]

        reuseSeq = CA.reuseAllSeqDict.get(urlTuple, list())
        if len(reuseSeq):
            # 执行过
            logger.debug("        use reuseSeq info: {}, parameters: {}", len(reuseSeq), len(reuseSeq[0].keys()))
            return reuseSeq
        else:
            paramList: List[AbstractParam] = operation.genDomain(chain, CA.okValueDict)
            paramNames = [p.name for p in paramList if operation.__repr__() + p.name not in self._unresolvedParam]
            domains = [p.domain for p in paramList if operation.__repr__() + p.name not in self._unresolvedParam]

            successEssentialCases = CA.reuseEssentialSeqDict.get(urlTuple, list())
            if len(successEssentialCases) > 0:
                newParamNames = list()
                newDomains = list()
                newParamNames.append("successEssentialCases")
                newDomains.append([(ValueType.NULL, i) for i in range(len(successEssentialCases))])
                for i, p in enumerate(paramNames):
                    if p not in successEssentialCases[0].keys():
                        newParamNames.append(p)
                        newDomains.append(domains[i])
                paramNames = newParamNames
                domains = newDomains

                for c in operation.constraints:
                    for p in c.paramNames:
                        if p in self._unresolvedParam:
                            return [{}]

            logger.debug("        generate new domains...")
            for i, p in enumerate(paramNames):
                logger.debug("            {}: {} - {}", p, len(domains[i]), set([item[0].value for item in domains[i]]))

            try:
                acts = ACTS(paramNames, domains, operation.constraints, self._aStrength)
            except Exception:
                return [{}]
            else:
                actsOutput = acts.main()
                for case in actsOutput:
                    if "successEssentialCases" in case.keys():
                        successIndex = case.pop("successEssentialCases")[1]
                        case.update(successEssentialCases[successIndex])
                return actsOutput

    def _saveChain(self, chain: dict, opStr: str, response):
        newChain = chain.copy()
        newChain[opStr] = response
        self._responseChains.append(newChain)
        if len(self._responseChains) > 10:
            self._responseChains.pop(0)

    def getChains(self):
        """get _maxChainItems longest chains"""
        sortedList = sorted(self._responseChains, key=lambda c: len(c.keys()), reverse=True)
        return sortedList[:self._maxChainItems] if self._maxChainItems < len(sortedList) else sortedList


class ACTS:
    def __init__(self, paramNames: list, domains: list, constraints: List[Constraint], strength: int):
        from src.restct import Config
        self._workplace = Path(Config.dataPath) / "acts"
        if not self._workplace.exists():
            self._workplace.mkdir()

        self._paramNames = paramNames
        self._domains = domains
        self._constraints = constraints
        assert len(set(self._paramNames)) == len(self._paramNames)
        assert len(self._paramNames) == len(self._domains)
        self._valueDict = dict(zip(self._paramNames, self._domains))
        self._strength = min(strength, len(self._paramNames))
        assert self._strength <= len(self._paramNames)

    def getId(self, paramName):
        index = self._paramNames.index(paramName)
        return "P" + str(index)

    def getName(self, paramId: str):
        index = int(paramId.lstrip("P"))
        return self._paramNames[index]

    def transformConstraint(self, constraint: Constraint):
        cStr = constraint.toActs(self._valueDict)
        if cStr is None:
            return ""
        for paramName in constraint.paramNames:
            pattern = r"\b" + paramName + r"\b"
            paramId = self.getId(paramName)
            cStr = re.sub(re.compile(pattern), paramId, cStr)
        return eval(cStr)

    def writeInput(self) -> Path:
        inputFile = self._workplace / "input.txt"
        with inputFile.open("w") as fp:
            fp.write(
                "\n".join(
                    ['[System]', '-- specify system name', 'Name: {}'.format("acts" + str(self._strength)), '',
                     '[Parameter]', '-- general syntax is parameter_name(type): value1, value2...\n'])
            )
            # write parameter ids
            for paramName in self._paramNames:
                domain = self._valueDict.get(paramName)
                fp.write("{}(int):{}\n".format(self.getId(paramName), ",".join([str(i) for i in range(len(domain))])))

            fp.write("\n")
            # write constraints
            if len(self._constraints) > 0:
                fp.write("[Constraint]\n")
                for c in self._constraints:
                    [fp.write(ts + "\n") for ts in self.transformConstraint(c)]

        return inputFile

    def callActs(self, inputFile) -> Path:
        outputFile = self._workplace / "output.txt"
        from src.restct import Config
        jarPath = Path(Config.jar)
        algorithm = "ipog"

        # acts 的文件路径不可以以"\"作为分割符，会被直接忽略，"\\"需要加上repr，使得"\\"仍然是"\\".
        command = r'java -Dalgo={0} -Ddoi={1} -Doutput=csv -jar {2} {3} {4}'.format(algorithm, str(self._strength),
                                                                                    str(jarPath),
                                                                                    str(inputFile),
                                                                                    str(outputFile))
        stdout, stderr = subprocess.Popen(shlex.split(command, posix=False), stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE).communicate()
        encoding = chardet.detect(stdout)["encoding"]
        stdout.decode(encoding)
        return outputFile

    def parseOutput(self, outputFile: Path):
        with outputFile.open("r") as fp:
            lines = [line.strip("\n") for line in fp.readlines() if "#" not in line and len(line.strip("\n")) > 0]
        paramNames = [self.getName(paramId) for paramId in lines[0].strip("\n").split(",")]
        coverArray: List[Dict[str, Tuple[ValueType, Union[str, int, float, list, dict]]]] = list()
        for line in lines[1:]:
            valueDict = dict()
            valueIndexList = line.strip("\n").split(",")
            for i, valueIndex in enumerate(valueIndexList):
                valueDict[paramNames[i]] = self._valueDict[paramNames[i]][int(valueIndex)]
            coverArray.append(valueDict)

        return coverArray

    def main(self):
        inputFile = self.writeInput()
        outputFile = self.callActs(inputFile)
        return self.parseOutput(outputFile)


class SendRequest:
    callNumber = 0

    def __init__(self, operation: Operation, coverArray: List[Dict[str, Tuple[ValueType, object]]], responses):
        self._operation: Operation = operation
        self._coverArray = coverArray
        self._responses = responses

    def main(self) -> Tuple[list, list]:
        statusCodes = list()
        responses = list()
        for case in self._coverArray:
            self.setParamValue(case)
            kwargs = self.assemble()
            statusCode, response = self.send(**kwargs)
            statusCodes.append(statusCode)
            responses.append(response)
        return statusCodes, responses

    def assemble(self) -> dict:
        url = self._operation.url
        headers = {
            'Content-Type': 'application/json',
            'user-agent': 'my-app/0.0.1'
        }
        params = dict()
        files = dict()
        formData = dict()
        body = dict()

        for p in self._operation.parameterList:
            value = p.printableValue(self._responses)
            if value is None:
                if p.loc is Loc.Path:
                    url = url.replace("{" + p.name + "}", str("abc"))
                # assert p.loc is not Loc.Path, "{}:{}".format(p.name, p.loc.value)
            else:
                if p.type is DataType.File:
                    files = value
                elif p.loc is Loc.Path:
                    assert p.name != "" and p.name is not None
                    url = url.replace("{" + p.name + "}", str(value))
                elif p.loc is Loc.Query:
                    params[p.name] = value
                elif p.loc is Loc.Header:
                    headers[p.name] = value
                elif p.loc is Loc.FormData:
                    if isinstance(value, dict):
                        formData.update(value)
                    else:
                        formData[p.name] = value
                elif p.loc is Loc.Body:
                    if isinstance(value, dict):
                        body.update(value)
                    else:
                        body[p.name] = value
                else:
                    raise Exception("unexpected Param Loc Type: {}".format(p.name))

        from src.restct import Config
        if Config.query is not None and len(Config.query) > 0:
            params.update(Config.query)

        kwargs = dict()
        kwargs["url"] = url
        kwargs["headers"] = headers
        if len(params) > 0:
            kwargs["params"] = params
        if len(files) > 0:
            kwargs["files"] = files
        if len(formData) > 0:
            kwargs["data"] = formData
        if len(body) > 0:
            kwargs["json"] = body
        return kwargs

    def setParamValue(self, case: Dict[str, Tuple[ValueType, object]]):
        parameters: List[AbstractParam] = self._operation.genDomain(dict(), dict())
        for p in parameters:
            p.value = case.get(p.name, [])

    def send(self, **kwargs) -> Tuple[int, Union[str, dict, None]]:
        SendRequest.callNumber += 1

        # for k, v in kwargs.items():
        #     logger.debug("{}: {}", k, v)

        try:
            feedback = getattr(requests, self._operation.method.value.lower())(**kwargs, timeout=10, auth=Auth())
        except TypeError:
            raise Exception("request type error: {}".format(self._operation.method.value.lower()))
        except requests.exceptions.Timeout:
            feedback = None
        except requests.exceptions.TooManyRedirects:
            raise Exception("bad url, try a different one\n url: {}".format(kwargs.get("url")))
        except requests.exceptions.RequestException:
            feedback = None

        if feedback is None:
            # logger.debug("status code: {}", 600)
            return 600, None
        try:
            # logger.debug("status code: {}", feedback.status_code)
            # logger.debug(feedback.json())
            return feedback.status_code, feedback.json()
        except json.JSONDecodeError:
            return feedback.status_code, feedback.text


class Auth:
    def __init__(self):
        from src.restct import Config
        self.headerAuth = Config.header

    def __call__(self, r):
        for key, token in self.headerAuth.items():
            r.headers[key] = token
        return r
