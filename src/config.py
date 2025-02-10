import argparse
import json
import os
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

        # output folder
        self.output_folder = ""

        # test budget (secs)
        self.budget = 0

        # constraint patterns for nlp recognition
        self.patterns = ""

        # acts jar file
        self.jar = ""
        self.pict = ""

        # auth token
        self.header = dict()

        # auth token
        self.query = dict()

        # experiment unique name
        self.exp_name = ""

        # data and log path
        self.data_path = ""

        # snapshot interval
        self.interval = .10

        self.server = None

    def check(self, settings: Namespace):
        curFile = Path(__file__)

        if Path(settings.swagger).exists():
            self.swagger = settings.swagger
        else:
            raise Exception("swagger json does not exist")

        if 1 <= settings.SStrength <= 5:
            self.s_strength = settings.SStrength
        else:
            raise Exception(f"operation sequence covering strength must be in [{1}, {5}]")

        if 1 <= settings.EStrength <= 5:
            self.e_strength = settings.EStrength
        else:
            raise Exception(f"essential parameter covering strength must be in [{1}, {5}]")

        if 1 <= settings.AStrength <= 5:
            self.a_strength = settings.AStrength
        else:
            raise Exception(f"all parameter covering strength must be in [{1}, {5}]")

        self.output_folder = settings.dir
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)

        if settings.budget == 0:
            raise Exception("test budget cannot be zero")
        else:
            self.budget = settings.budget

        self.interval = settings.interval

        self.patterns = Path(settings.patterns)
        if self.patterns.exists() and self.patterns.is_file():
            self.patterns = self.patterns.as_posix()
        else:
            raise Exception("patterns are not provided")

        self.jar = Path(settings.jar)
        if self.jar.exists() and self.jar.is_file():
            self.jar = self.jar.as_posix()
        else:
            raise Exception("acts jar is not provided")

        try:
            auth_token = json.loads(settings.header)
        except json.JSONDecodeError:
            raise Exception("expecting strings enclosed in double quotes")
        else:
            self.header.update(auth_token)

        try:
            auth_token = json.loads(settings.query)
        except json.JSONDecodeError:
            raise Exception("expecting strings enclosed in double quotes")
        else:
            self.query.update(auth_token)

        if settings.exp_name is None or settings.exp_name == "":
            self.exp_name = Path(settings.swagger).with_suffix("").name
        else:
            self.exp_name = settings.exp_name

        if settings.server is not None and settings.server != "":
            self.server = settings.server

        data_path = Path(f"{self.output_folder}/{self.exp_name}")
        self.data_path = data_path.as_posix()
        if not data_path.exists():
            data_path.mkdir()

        os.environ["patternFile"] = self.patterns


def parse_args(root_path) -> Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument('--swagger',
                        help='abs path of swagger file',
                        type=str, required=True)
    parser.add_argument('--dir',
                        help='output folder',
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
    parser.add_argument('--budget',
                        help='test budget(Secs), default=3600',
                        type=int, required=False, default=3600)
    parser.add_argument('--patterns',
                        help='constraint patterns for nlp processes',
                        type=str, required=False, default=f"{root_path}/lib/matchrules.json")
    parser.add_argument('--jar',
                        help='acts jar file',
                        type=str, required=False, default=f"{root_path}/lib/acts_2.93.jar")
    parser.add_argument('--header',
                        help='auth token: {keyName: token}',
                        type=str, required=False, default="{}")
    parser.add_argument('--query',
                        help='auth token: {keyName: token}',
                        type=str, required=False, default="{}")
    parser.add_argument('--exp_name',
                        help='experiment unique name for statistic data',
                        type=str, required=False, default="")
    parser.add_argument('--interval',
                        help='snapshot interval',
                        type=float, required=False, default=.10)
    parser.add_argument('--server',
                        help='set if the forwarding proxy is running',
                        type=str, required=False, default="")

    args = parser.parse_args()
    return args
