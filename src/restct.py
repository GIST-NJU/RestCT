import argparse
import json
from argparse import Namespace
from pathlib import Path


class Config:
    # swagger file path
    swagger = ""

    # operation sequence covering strength
    s_strength = 0

    # all parameter covering strength
    a_strength = 0

    # essential parameter covering strength
    e_strength = 0

    # maximum of op_cover_strength
    MAX_OP_COVER_STRENGTH = 5

    # minimum of op_cover_strength
    MIN_OP_COVER_STRENGTH = 1

    # maximum of param_cover_strength
    MAX_PARAM_COVER_STRENGTH = 5

    # minimum of param_cover_strength
    MIN_PARAM_COVER_STRENGTH = 1

    # output folder
    output_folder = ""

    # test budget (secs)
    budget = 0

    # constraint patterns for nlp recognition
    patterns = ""

    # acts jar file
    jar = ""

    # auth token
    header = dict()

    # auth token
    query = dict()

    # experiment unique name
    columnId = ""

    # data and log path
    dataPath = ""


def checkAndPrehandling(settings: Namespace):
    curFile = Path(__file__)

    if Path(settings.swagger).exists():
        Config.swagger = settings.swagger
    else:
        raise Exception("swagger json does not exist")

    if Config.MIN_OP_COVER_STRENGTH <= settings.SStrength <= Config.MAX_OP_COVER_STRENGTH:
        Config.s_strength = settings.SStrength
    else:
        raise Exception("operation sequence covering strength must be in [{}, {}]".format(Config.MIN_OP_COVER_STRENGTH,
                                                                                          Config.MAX_OP_COVER_STRENGTH))

    if Config.MIN_PARAM_COVER_STRENGTH <= settings.EStrength <= Config.MAX_PARAM_COVER_STRENGTH:
        Config.e_strength = settings.EStrength
    else:
        raise Exception(
            "essential parameter covering strength must be in [{}, {}]".format(Config.MIN_PARAM_COVER_STRENGTH,
                                                                               Config.MAX_PARAM_COVER_STRENGTH))

    if Config.MIN_PARAM_COVER_STRENGTH <= settings.AStrength <= Config.MAX_PARAM_COVER_STRENGTH:
        Config.a_strength = settings.AStrength
    else:
        raise Exception(
            "all parameter covering strength must be in [{}, {}]".format(Config.MIN_PARAM_COVER_STRENGTH,
                                                                         Config.MAX_PARAM_COVER_STRENGTH))

    folder = Path(settings.dir)

    Config.output_folder = settings.dir
    folder.mkdir(exist_ok=True)

    if settings.budget == 0:
        raise Exception("test budget cannot be zero")
    else:
        Config.budget = settings.budget

    if settings.patterns == "":
        patterns = curFile.parent.parent / "lib/matchrules.json"
    else:
        patterns = Path(settings.patterns)
    if patterns.exists() and patterns.is_file():
        Config.patterns = patterns.as_posix()
    else:
        raise Exception("patterns are not provided")

    if settings.jar == "":
        jarFile = curFile.parent.parent / "lib/acts_2.93.jar"
    else:
        jarFile = Path(settings.jar)
    if jarFile.exists() and jarFile.is_file():
        Config.jar = jarFile.as_posix()
    else:
        raise Exception("acts jar is not provided")

    try:
        authToken = json.loads(settings.header)
    except json.JSONDecodeError:
        raise Exception("expecting strings enclosed in double quotes")
    else:
        Config.header.update(authToken)

    try:
        authToken = json.loads(settings.query)
    except json.JSONDecodeError:
        raise Exception("expecting strings enclosed in double quotes")
    else:
        Config.query.update(authToken)

    if settings.columnId is None or settings.columnId == "":
        Config.columnId = Path(settings.swagger).with_suffix("").name
    else:
        Config.columnId = settings.columnId

    dataPath = folder / Config.columnId
    Config.dataPath = dataPath.as_posix()
    if not dataPath.exists():
        dataPath.mkdir()


if __name__ == "__main__":
    import sys
    import os

    curPath = os.path.abspath(os.path.dirname(__file__))
    rootPath = os.path.split(curPath)[0]
    sys.path.append(rootPath)

    from src.algorithm import RESTCT
    from src.restct import Config

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

    args = parser.parse_args()

    checkAndPrehandling(args)

    RESTCT.outputFolder = Config.output_folder
    RESTCT.dataPath = Config.dataPath
    RESTCT.budget = Config.budget
    RESTCT.columnId = Config.columnId
    RESTCT.SStrength = Config.s_strength
    RESTCT.EStrength = Config.e_strength
    RESTCT.AStrength = Config.a_strength
    RESTCT.run()
