import sys
import os
import time
from pathlib import Path
from unittest import TestCase
from enum import Enum

class ValueType(Enum):
    Enum = "enum"
    Default = "default"
    Example = "example"
    Random = "random"
    Dynamic = "dynamic"
    NULL = "Null"


class TestACTS(TestCase):

    def test_main(self):
        rootPath = "D:\Python_Codes\RestCT"
        sys.path.append(rootPath)

        from src.generateCA import ACTS
        from src.Dto.constraint import Constraint

        parameters = ['key', 'bounds', 'rows', 'cols']
        domain = list()
        t1 = list()
        d1 = list()
        d1.append(ValueType.Enum)
        d1.append("AtI47DZkFsqZK_2Ks7A_68EwjlpTLNI2imXFZey-6jt_YnFE1n3SXVZ6umljRFch")
        t1.append(tuple(d1))
        domain.append(t1)
        t2 = list()
        d2 = list()
        d2.append(ValueType.Random)
        d2.append('45.219,-122.234,4J7.61,-122.07')
        t2.append(tuple(d2))
        d3 = list()
        d3.append(ValueType.Default)
        d3.append('45.219,-122.234,47.61,-122.07')
        t2.append(tuple(d3))
        domain.append(t2)

        t3 = list()
        d4 = list()
        d4.append(ValueType.Random)
        d4.append(7)
        t3.append(tuple(d4))
        d5 = list()
        d5.append(ValueType.Default)
        d5.append(30)
        t3.append(tuple(d5))
        domain.append(t3)

        t4 = list()
        d6 = list()
        d6.append(ValueType.Random)
        d6.append(6)
        t4.append(tuple(d6))
        d7 = list()
        d7.append(ValueType.Default)
        d7.append(15)
        t4.append(tuple(d7))
        domain.append(t4)

        print(domain)

        constraint1 = "(P0 = 0) => (P1 = 0)"
        constraint2 = "(P0 = 0) => (P2 = 0)"
        constraint3 = "(P0 = 0) => (P3 = 0)"
        c = list()
        c.append(constraint1)
        c.append(constraint2)
        c.append(constraint3)
        acts = ACTS(parameters, domain, c, 2)
        # acts = ACTS(parameters, domain, [], 2)
        t = acts.main()
        print(t)
        print(len(t))

