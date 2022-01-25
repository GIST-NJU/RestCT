import argparse
from pathlib import Path
from typing import List


SWAGGER_DIR = ""
OUTPUT_DIR = ""
SCRIPTS_DIR = ""
BING_MAP_AUTH = "{\"key\": \"Am5K5mBbQyBZAkcz9lwRFSavr2XNYgDxWdG2YpQcrOgQqk92tVR8EsnaRGy3-5Ms\"}"
GITLAB_AUTH = "{\"Authorization\": \"Bearer 298befc034818a461ad31f4a7d4bfe8448bec16c16931fe578c438d145ed503c\"}"

EXP_OBJS = {
    "GitLab": {"Branch", "Commit", "Groups", "Issues", "Project", "Repository"},
    "BingMap": {"Elevations", "Imagery", "Locations", "Route", "TimeZone"}
}

SELECTED_OBJS = list()


class SUT:
    def __init__(self, SStrength, EStrength, AStrength, budget, swagger, repeat):
        self.SStrength = SStrength
        self.EStrength = EStrength
        self.AStrength = AStrength
        self.budget = budget
        self.swagger = swagger
        self.repeat = repeat

    @classmethod
    def build(cls, info: List[str]):
        name = info[0]
        SStrength = 0
        AStrength = 0
        EStrength = 0
        repeat = 0
        budget = 0

        for item in info[1:]:
            if item.startswith("s"):
                SStrength = int(item[1:])
            elif item.startswith("e"):
                EStrength = int(item[1:])
            elif item.startswith("a"):
                AStrength = int(item[1:])
            elif item.startswith("r"):
                repeat = int(item[1:])
            else:
                budget = parseTime(item)

        assert budget > 0
        assert repeat > 0
        assert AStrength > 0
        assert EStrength > 0
        assert SStrength > 0

        sFile = Path(SWAGGER_DIR) / (name + ".json")

        return cls(SStrength, EStrength, AStrength, budget, sFile.as_posix(), repeat)

    def generateScript(self):



def parseTime(s:str):
    budget = 0
    if s.endswith("s"):
        budget = int(s[1:])
    elif s.endswith("m"):
        budget = 60 * int(s[1:])
    elif s.endswith("h"):
        budget = 3600 * int(s[1:])
    else:
        raise Exception(s + " can not be parsed")
    return budget


def generateScripts():



def checkAndPrehandling(settings):
    global SWAGGER_DIR
    global SELECTED_OBJS
    global OUTPUT_DIR
    global SCRIPTS_DIR

    swaggerDir = Path(settings.swaggerDir)
    if not swaggerDir.exists():
        raise Exception("the folder of swagger docs does not exists")
    if not swaggerDir.is_dir():
        raise Exception("swaggerDir must be a folder")
    SWAGGER_DIR = swaggerDir.as_posix()

    objs = [objStr.split("_") for objStr in settings.expObj]
    for o in objs:
        assert len(o) == 5
        if o[0] in EXP_OBJS.keys():
            for item in EXP_OBJS[o[0]]:
                itemSwagger = swaggerDir / (item + ".json")
                if not itemSwagger.exists():
                    raise Exception(item + " swagger doc does not exist")
                newList = [item]
                newList.extend(o[1:])
                SELECTED_OBJS.append(newList)
        elif o[0] in EXP_OBJS["GitLab"]:
            sFile = swaggerDir / (o[0] + ".json")
            if not sFile.exists():
                raise Exception(o[0] + " swagger doc dox")
            SELECTED_OBJS.append(o)
        elif o[0] in EXP_OBJS["BingMap"]:
            sFile = swaggerDir / (o[0] + ".json")
            if not sFile.exists():
                raise Exception(o[0] + " swagger doc dox")
            SELECTED_OBJS.append(o)
        else:
            raise Exception(o[0] + " is not a obj")

    output = Path(settings.dir)
    if not output.exists():
        output.mkdir(parents=True)
    elif output.is_file():
        raise Exception(output.as_posix() + " must be a folder")
    OUTPUT_DIR = output.as_posix()

    scriptDir = Path(settings.scriptFolder)
    if not scriptDir.exists():
        scriptDir.mkdir(parents=True)
    elif scriptDir.is_file():
        raise Exception(scriptDir.as_posix() + " must be a folder")
    SCRIPTS_DIR = scriptDir.as_posix()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('--swaggerDir',
                        help='abs folder of swagger file',
                        type=str, required=True)
    parser.add_argument('--expObj',
                        help='specify the expObjs, e.g. "gitlab_s2_e3_a2_r1_1h"',
                        type=str, required=True)
    parser.add_argument('--dir',
                        help='output folder',
                        type=str, required=True)
    parser.add_argument('--scriptFolder',
                        help='the folder of generated scripts',
                        type=str, required=True)

    args = parser.parse_args()

    checkAndPrehandling(args)

    generateScripts()
