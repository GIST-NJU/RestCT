import json
import os
import re
from collections import defaultdict, Counter
from enum import Enum
from pathlib import Path
from typing import List, Set

import spacy
from spacy.matcher import Matcher
from spacy.tokens import Doc

from src.factor import EnumFactor, AbstractFactor

Doc.set_extension("constraints", default=None, force=True)


@spacy.Language.factory("constraintMatcher")
def createConstraintMatcher(nlp, name):
    return ConstraintMatcher(nlp)


class ConstraintMatcher:
    def __init__(self, nlp):
        self.nlp = nlp
        self.matcher = Matcher(nlp.vocab)
        self._loadPatterns()

        self.spanWithConstraints = set()

    def _loadPatterns(self):
        patternFile = Path(os.getenv("patternFile"))
        with patternFile.open("r") as fp:
            patterns = json.load(fp)
        rules = defaultdict(list)
        for ruleList in patterns.values():
            for ruleInfo in ruleList:
                constraint = tuple(ruleInfo.get("constraint"))
                rules[constraint].append(ruleInfo.get("pattern"))
        for constraint, patterns in rules.items():
            self.matcher.add(repr(constraint), patterns)

    def __call__(self, doc):
        matches = self.matcher(doc)
        for matchId, start, end in matches:
            span = doc[start: end]
            entries = list()
            for ent in span.ents:
                entries.append(ent.ent_id_)
            if tuple(entries) not in self.spanWithConstraints:
                doc._.constraints = self.nlp.vocab.strings[matchId]
                doc.ents = span.ents
                self.spanWithConstraints.add(tuple(entries))

        return doc


class EntityLabel(Enum):
    Param = "PARAM"
    Value = "VALUE"


class Processor:
    def __init__(self, paramEntities: List[AbstractFactor]):
        self.nlp = spacy.load("en_core_web_sm")
        self._paramEntities: List = paramEntities
        self._descriptions = [factor.description for factor in paramEntities]
        assert len({factor.get_global_name for factor in paramEntities}) == len(paramEntities)
        self._paramNames = {factor.get_global_name: factor for factor in paramEntities}
        self._paramValues = {factor.get_global_name: factor.enum_value for factor in paramEntities if
                             isinstance(factor, EnumFactor)}

        self.setNLP()

    def setNLP(self):
        patterns = [{"label": EntityLabel.Param.value, "pattern": name, "id": name} for name in
                    self._paramNames.keys()]
        for valueSet in self._paramValues.values():
            for value in valueSet:
                patterns.append({"label": EntityLabel.Value.value, "pattern": str(value), "id": str(value)})

        rulerPipe = self.nlp.add_pipe("entity_ruler", config={"overwrite_ents": True})
        with self.nlp.select_pipes(disable=self.nlp.pipe_names, ):
            rulerPipe.add_patterns(patterns)
        self.nlp.add_pipe("constraintMatcher", last=True)

    def _cleanText(self, text):
        if text is None:
            return ""
        return " ".join([token.text for token in self.nlp.make_doc(text) if
                         token.text not in {"'", '"', "[", "]", "(", ")"} and not token.is_space])

    def parse(self):
        constraints: List[Constraint] = list()

        for text in self._descriptions:
            text = self._cleanText(text)
            doc = self.nlp(text)
            involvedParamNames: Set[str] = set()
            involvedValues: Set[str] = set()
            involvedParamNames.update([ent.ent_id_ for ent in doc.ents if ent.label_ == EntityLabel.Param.value])
            involvedValues.update([ent.ent_id_ for ent in doc.ents if ent.label_ == EntityLabel.Value.value])
            ents = [ent.ent_id_ for ent in doc.ents if ent.label_ in [EntityLabel.Param.value, EntityLabel.Value.value]]
            if doc._.constraints:
                constraints.append(Constraint(doc._.constraints, involvedParamNames, involvedValues, ents))
        self.updateParam(constraints)
        return constraints

    def updateParam(self, constraints):
        paramNames = set()
        for c in constraints:
            paramNames.update(c.paramNames)
        for factor in self._paramEntities:
            if factor.get_global_name in paramNames:
                factor.is_constraint = True
            else:
                factor.is_constraint = False

    def analyseError(self, errorResponses):
        unresolvedParams = list()
        for message in errorResponses:
            unresolvedParams.extend(self._analyseResponse(message))
        sortedList = sorted(Counter(unresolvedParams).items(), key=lambda item: item[1], reverse=True)
        return [p for p, _ in sortedList]

    def _analyseResponse(self, message):
        records = set()
        message = re.sub(r'["#$%&\'()*+,:;<=>?@^|{}~\s\n]+', " ", str(message))
        message = re.sub(
            r'[\001\002\003\004\005\006\007\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a]+',
            " ", message
        )
        doc = self.nlp(message)
        for ent in doc.ents:
            if ent.label_ == EntityLabel.Param.value:
                records.add(ent.ent_id_)
        return records

class Constraint:
    def __init__(self, template, paramNames, values, ents):
        self._template = template
        self.paramNames = paramNames
        self.valueStr = values
        self.ents = ents  # in order

    def toActs(self, operation, valueDict: dict):
        """
        :param valueDict: parameters' domains. key: paramName, value: domain
        :return: string in acts input format
        """
        formattedStr = self._template
        for matcher in re.finditer(r"(\w)\1\s*(!?=)\s*[\'\"]?(None|(\w)\4)[\'\"]?", self._template):
            if matcher.group(3) == "None":
                paramName, op, value = self.ents[ord(matcher.group(1)) - 65], matcher.group(2), None
            else:
                paramName, op, value = self.ents[ord(matcher.group(1)) - 65], matcher.group(2), self.ents[
                    ord(matcher.group(4)) - 65]
            try:
                global_name = paramName
                for f in operation.get_leaf_factors():
                    if f.name == paramName:
                        global_name = f.get_global_name
                        break
                valueList = [v.val for v in valueDict.get(global_name)]
                valueIndex = valueList.index(value)
            except (ValueError, TypeError):
                return None
            formattedStr = re.sub(matcher.group(), "{} {} {}".format(paramName, op, valueIndex), formattedStr)
        return formattedStr

    def to_pict(self, operation, valueDict: dict):
        """
        :param valueDict: parameters' domains. key: paramName, value: domain
        :return: string in acts input format
        """
        formattedStr = self._template
        for matcher in re.finditer(r"(\w)\1\s*(!?=)\s*[\'\"]?(None|(\w)\4)[\'\"]?", self._template):
            if matcher.group(3) == "None":
                paramName, op, value = self.ents[ord(matcher.group(1)) - 65], matcher.group(2), None
            else:
                paramName, op, value = self.ents[ord(matcher.group(1)) - 65], matcher.group(2), self.ents[
                    ord(matcher.group(4)) - 65]
            try:
                global_name = paramName
                for f in operation.get_leaf_factors():
                    if f.name == paramName:
                        global_name = f.get_global_name
                        break
                valueList = [v.val for v in valueDict.get(global_name)]
                valueIndex = valueList.index(value)
            except (ValueError, TypeError):
                return None
            formattedStr = re.sub(matcher.group(), "{} {} {}".format(f"[{paramName}]", op, valueIndex), formattedStr)
        return formattedStr
