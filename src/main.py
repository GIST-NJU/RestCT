import argparse
import json
from argparse import Namespace
from pathlib import Path


class Config:
    def __init__(self):
        # swagger file path
        self.swagger = ""

        # operation sequence covering strength
        self.s_strength = 2

        # all parameter covering strength
        self.a_strength = 2

        # essential parameter covering strength
        self.e_strength = 3

        # maximum of op_cover_strength
        self.MAX_OP_COVER_STRENGTH = 5

        # minimum of op_cover_strength
        self.MIN_OP_COVER_STRENGTH = 1

        # maximum of param_cover_strength
        self.MAX_PARAM_COVER_STRENGTH = 5

        # minimum of param_cover_strength
        self.MIN_PARAM_COVER_STRENGTH = 1

        # output folder
        self.output_folder = ""

        # test budget (secs)
        self.budget = 0

        # constraint patterns for nlp recognition
        self.patterns = ""

        # acts jar file
        self.jar = ""

        # auth token
        self.header = dict()

        # auth token
        self.query = dict()

        # experiment unique name
        self.columnId = ""

        # data and log path
        self.dataPath = ""

        # forwarding base url
        # self.forwarding_url = "http://localhost:8081"
        self.forwarding_url = None

    def checkAndPrehandling(self, settings: Namespace):
        curFile = Path(__file__)

        if Path(settings.swagger).exists():
            self.swagger = settings.swagger
        else:
            raise Exception("swagger json does not exist")

        if self.MIN_OP_COVER_STRENGTH <= settings.SStrength <= self.MAX_OP_COVER_STRENGTH:
            self.s_strength = settings.SStrength
        else:
            raise Exception(
                "operation sequence covering strength must be in [{}, {}]".format(self.MIN_OP_COVER_STRENGTH,
                                                                                  self.MAX_OP_COVER_STRENGTH))

        if self.MIN_PARAM_COVER_STRENGTH <= settings.EStrength <= self.MAX_PARAM_COVER_STRENGTH:
            self.e_strength = settings.EStrength
        else:
            raise Exception(
                "essential parameter covering strength must be in [{}, {}]".format(self.MIN_PARAM_COVER_STRENGTH,
                                                                                   self.MAX_PARAM_COVER_STRENGTH))

        if self.MIN_PARAM_COVER_STRENGTH <= settings.AStrength <= self.MAX_PARAM_COVER_STRENGTH:
            self.a_strength = settings.AStrength
        else:
            raise Exception(
                "all parameter covering strength must be in [{}, {}]".format(self.MIN_PARAM_COVER_STRENGTH,
                                                                             self.MAX_PARAM_COVER_STRENGTH))

        folder = Path(settings.dir)

        self.output_folder = settings.dir
        folder.mkdir(exist_ok=True)

        if settings.budget == 0:
            raise Exception("test budget cannot be zero")
        else:
            self.budget = settings.budget

        if settings.patterns == "":
            patterns = curFile.parent.parent / "lib/matchrules.json"
        else:
            patterns = Path(settings.patterns)
        if patterns.exists() and patterns.is_file():
            self.patterns = patterns.as_posix()
        else:
            raise Exception("patterns are not provided")

        if settings.jar == "":
            jarFile = curFile.parent.parent / "lib/acts_2.93.jar"
        else:
            jarFile = Path(settings.jar)
        if jarFile.exists() and jarFile.is_file():
            self.jar = jarFile.as_posix()
        else:
            raise Exception("acts jar is not provided")

        try:
            authToken = json.loads(settings.header)
        except json.JSONDecodeError:
            raise Exception("expecting strings enclosed in double quotes")
        else:
            self.header.update(authToken)

        try:
            authToken = json.loads(settings.query)
        except json.JSONDecodeError:
            raise Exception("expecting strings enclosed in double quotes")
        else:
            self.query.update(authToken)

        if settings.columnId is None or settings.columnId == "":
            self.columnId = Path(settings.swagger).with_suffix("").name
        else:
            self.columnId = settings.columnId

        dataPath = folder / self.columnId
        self.dataPath = dataPath.as_posix()
        if not dataPath.exists():
            dataPath.mkdir()

        os.environ["dataPath"] = self.dataPath
        os.environ["swagger"] = self.swagger
        os.environ["patternFile"] = self.patterns


if __name__ == "__main__":
    import sys
    import os

    curPath = os.path.abspath(os.path.dirname(__file__))
    rootPath = os.path.split(curPath)[0]
    sys.path.append(rootPath)

    parser = argparse.ArgumentParser()

    parser.add_argument('--swagger',
                        help='abs path of swagger file',
                        type=str, required=True)
    parser.add_argument('--SStrength',
                        help='operation sequence covering strength',
                        type=int, required=False, default=2)
    parser.add_argument('--EStrength',
                        help='essential parameter covering strength',
                        type=int, required=False, default=3)
    parser.add_argument('--AStrength',
                        help='all parameter covering strength',
                        type=int, required=False, default=2)
    parser.add_argument('--dir',
                        help='output folder',
                        type=str, required=True)
    parser.add_argument('--budget',
                        help='test budget(Secs), default=3600',
                        type=int, required=False, default=3600)
    parser.add_argument('--patterns',
                        help='constraint patterns for nlp processes',
                        type=str, required=False, default="")
    parser.add_argument('--jar',
                        help='acts jar file',
                        type=str, required=False, default="")
    parser.add_argument('--header',
                        help='auth token: {keyName: token}',
                        type=str, required=False, default="{}")
    parser.add_argument('--query',
                        help='auth token: {keyName: token}',
                        type=str, required=False, default="{}")
    parser.add_argument('--columnId',
                        help='experiment unique name for statistic data',
                        type=str, required=False, default="")
    parser.add_argument('--forwardingURL',
                        help='set if the forwarding proxy is running',
                        type=str, required=False, default="")

    args = parser.parse_args()

    config = Config()
    config.checkAndPrehandling(args)

    from src.restct import RestCT
    from controller import RemoteController

    restCT = RestCT(config)
    restCT.run()
