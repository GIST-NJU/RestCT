import argparse
from pathlib import Path
from typing import List

SWAGGER_DIR = ""
OUTPUT_DIR = ""
SCRIPTS_DIR = ""
TOOL_DIR = ""
BING_MAP_AUTH = ""
GITLAB_AUTH = ""

EXP_OBJS = {
    "GitLab": {"Branch", "Commit", "Groups", "Issues", "Project", "Repository"},
    "BingMap": {"Elevations", "Imagery", "Locations", "Route", "TimeZone"}
}

SELECTED_OBJS = list()


class SUT:
    def __init__(self, name, SStrength, EStrength, AStrength, budget, swagger, repeat):
        self.name = name
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

        return cls(name, SStrength, EStrength, AStrength, budget, sFile.as_posix(), repeat)

    def generateScript(self):
        scriptFile = Path(SCRIPTS_DIR) / "scripts/{0}_{1}_{2}_{3}.sh".format(self.name, self.SStrength, self.EStrength,
                                                                             self.AStrength)
        if not scriptFile.parent.exists():
            scriptFile.parent.mkdir(parents=True)
        command = "nohup python3.8 " + TOOL_DIR
        command += " --swagger " + self.swagger
        command += " --dir " + OUTPUT_DIR
        command += " --SStrength " + str(self.SStrength)
        command += " --EStrength " + str(self.EStrength)
        command += " --AStrength " + str(self.AStrength)
        command += " --budget " + str(self.budget)
        command += " --columnId {}_s{}_e{}_a{}_r{}_$repeat".format(self.name, self.SStrength, self.EStrength,
                                                                   self.AStrength, self.repeat)
        if self.name in EXP_OBJS["GitLab"]:
            assert GITLAB_AUTH != ""
            command += " --header " + "\"{\\\"Authorization\\\": \\\"Bearer " + GITLAB_AUTH + "\\\"}\""
        elif self.name in EXP_OBJS["BingMap"]:
            assert BING_MAP_AUTH != ""
            command += " --query " + "\"{\\\"key\\\": \\\"" + BING_MAP_AUTH + "\\\"}\""
        command += " > " + self.name + "_{}_{}_{}_$repeat.log".format(self.SStrength, self.EStrength, self.AStrength)
        command += " 2>&1"
        with scriptFile.open("w") as fp:
            fp.write("#!/bin/bash \n\n")
            fp.write("repeat=1\n")
            fp.write("while(( $repeat<={} ))\n".format(self.repeat))
            fp.write("do\n")
            # fp.write(" " * 4 + "echo " + command + "\n")
            fp.write(" " * 4 + command + "\n")
            fp.write(" " * 4 + "let \"repeat++\"\n")
            fp.write("done\n")


def parseTime(s: str):
    if s.endswith("s"):
        budget = int(s[:-1])
    elif s.endswith("m"):
        budget = 60 * int(s[:-1])
    elif s.endswith("h"):
        budget = 3600 * int(s[:-1])
    else:
        raise Exception(s + " can not be parsed")
    return budget


def generateScripts():
    for sut in SELECTED_OBJS:
        sut = SUT.build(sut)
        sut.generateScript()

    runScriptFile = Path(SCRIPTS_DIR) / "runAll.sh"
    with runScriptFile.open("w") as fp:
        fp.write("#!/bin/bash \n\n")
        fp.write("for file in {}/scripts/*\n".format(SCRIPTS_DIR))
        fp.write("do\n")
        fp.write(" " * 4 + "chmod a+x $file\n")
        fp.write(" " * 4 + "echo $file\n")
        fp.write(" " * 4 + "$file\n")
        fp.write("done\n\n")
        fp.write("echo 'Done!'")


def RQ1():
    global SCRIPTS_DIR
    global OUTPUT_DIR

    SELECTED_OBJS.clear()

    if GITLAB_AUTH != "":
        SELECTED_OBJS.extend([(name, "s2", "e3", "a2", "r1", "1h") for name in EXP_OBJS["GitLab"]])
        SCRIPTS_DIR = (Path(SWAGGER_DIR).parent.parent / "runScripts/GitLab_RQ1").as_posix()
        OUTPUT_DIR = (Path(SWAGGER_DIR).parent.parent / "output/GitLab_RQ1").as_posix()

    elif BING_MAP_AUTH != "":
        SELECTED_OBJS.extend([(name, "s2", "e3", "a2", "r1", "1h") for name in EXP_OBJS["BingMap"]])
        SCRIPTS_DIR = (Path(SWAGGER_DIR).parent.parent / "runScripts/BingMap_RQ1").as_posix()
        OUTPUT_DIR = (Path(SWAGGER_DIR).parent.parent / "output/BingMap_RQ1").as_posix()
    else:
        pass

    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)


def RQ2():
    global SCRIPTS_DIR
    global OUTPUT_DIR

    SELECTED_OBJS.clear()

    for s, e, a in [(1, 3, 2), (3, 3, 2), (2, 2, 2), (2, 4, 2), (2, 3, 1), (2, 3, 3)]:
        if GITLAB_AUTH != "":
            SELECTED_OBJS.extend(
                [(name, "s" + str(s), "e" + str(e), "a" + str(a), "r1", "5h") for name in EXP_OBJS["GitLab"]])
            SCRIPTS_DIR = (Path(SWAGGER_DIR).parent.parent / "runScripts/GitLab_RQ2").as_posix()
            OUTPUT_DIR = (Path(SWAGGER_DIR).parent.parent / "output/GitLab_RQ2").as_posix()

        elif BING_MAP_AUTH != "":
            SELECTED_OBJS.extend(
                [(name, "s" + str(s), "e" + str(e), "a" + str(a), "r1", "5h") for name in EXP_OBJS["BingMap"]])
            SCRIPTS_DIR = (Path(SWAGGER_DIR).parent.parent / "runScripts/BingMap_RQ2").as_posix()
            OUTPUT_DIR = (Path(SWAGGER_DIR).parent.parent / "output/BingMap_RQ2").as_posix()
        else:
            pass

    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)


def checkAndPrehandling(settings):
    global SWAGGER_DIR
    global SELECTED_OBJS
    global OUTPUT_DIR
    global SCRIPTS_DIR
    global TOOL_DIR
    global GITLAB_AUTH
    global BING_MAP_AUTH

    curFile = Path(__file__)

    if settings.swaggerDir is not None and settings.swaggerDir != "":
        swaggerDir = Path(settings.swaggerDir)
    else:
        if settings.gitlabAuth is not None and settings.gitlabAuth != "":
            swaggerDir = curFile.parent / "swagger/GitLab"
        elif settings.bingMapAuth is not None and settings.bingMapAuth != "":
            swaggerDir = curFile.parent / "swagger/BingMap"
        else:
            raise Exception("specify --gitlabAuth or --bingMapAuth")
    if not swaggerDir.exists():
        raise Exception("the folder of swagger docs does not exists")
    if not swaggerDir.is_dir():
        raise Exception("swaggerDir must be a folder")
    SWAGGER_DIR = swaggerDir.as_posix()

    if settings.expObj is not None and settings.expObj != "":
        objs = [objStr.split("_") for objStr in settings.expObj.split(",")]
        for o in objs:
            assert len(o) == 6
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

    if settings.dir is None or settings.dir == "":
        output = curFile.parent / "output"
    else:
        output = Path(settings.dir)
    if not output.exists():
        output.mkdir(parents=True)
    elif output.is_file():
        raise Exception(output.as_posix() + " must be a folder")
    OUTPUT_DIR = output.as_posix()

    if settings.scriptFolder is None or settings.dir == "":
        scriptDir = curFile.parent / "runScripts"
    else:
        scriptDir = Path(settings.scriptFolder)
    if not scriptDir.exists():
        scriptDir.mkdir(parents=True)
    elif scriptDir.is_file():
        raise Exception(scriptDir.as_posix() + " must be a folder")
    SCRIPTS_DIR = scriptDir.as_posix()

    if settings.toolDir is None or settings.toolDir == "":
        toolDir = curFile.parent.parent / "src/restct.py"
    else:
        toolDir = Path(settings.toolDir)
    if not toolDir.exists():
        raise Exception("tool does not exist")
    if not toolDir.is_file():
        raise Exception("tool must be a .py file")
    TOOL_DIR = toolDir.as_posix()

    if settings.gitlabAuth is not None and settings.gitlabAuth != "":
        GITLAB_AUTH = settings.gitlabAuth

    if settings.bingMapAuth is not None and settings.bingMapAuth != "":
        BING_MAP_AUTH = settings.bingMapAuth


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument('--swaggerDir',
                        help='abs folder of swagger file',
                        type=str, required=False, default="")
    parser.add_argument('--expObj',
                        help='specify the expObjs, e.g. "GitLab_s2_e3_a2_r1_1h"',
                        type=str, required=False, default="")
    parser.add_argument('--dir',
                        help='output folder',
                        type=str, required=False, default="")
    parser.add_argument('--scriptFolder',
                        help='the folder of generated scripts',
                        type=str, required=False, default="")
    parser.add_argument('--toolDir',
                        help='tool file path',
                        type=str, required=False, default="")
    parser.add_argument('--gitlabAuth',
                        help='update oauth token for gitlab',
                        type=str, required=False, default="")
    parser.add_argument('--bingMapAuth',
                        help='update key token for bingmap',
                        type=str, required=False, default="")

    args = parser.parse_args()

    checkAndPrehandling(args)

    if len(SELECTED_OBJS):
        generateScripts()
    else:
        RQ1()
        generateScripts()
        RQ2()
        generateScripts()
