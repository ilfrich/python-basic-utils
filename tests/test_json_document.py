import json as sysjson
from pbu.json_document import JsonDocument
from pbu.date_time import DATETIME_FORMAT
from pbu.default_options import default_options
from datetime import datetime


class BasicTestParent(JsonDocument):
    def __init__(self):
        super().__init__()
        self.str_attr = "Yes"
        self.num_attr = 1
        self.bool_attr = False
        self.list_attr = []
        self.dict_attr = {}
        self.none_attr = None

    @staticmethod
    def from_json(json: dict):
        tp = BasicTestParent()
        tp.extract_system_fields(json)
        return tp

    def get_attribute_mapping(self) -> dict:
        return {
            "str_attr": "str",
            "num_attr": "num",
            "bool_attr": "bool",
            "list_attr": "list",
            "dict_attr": "dict",
            "none_attr": "none"
        }


def test_basic_json():
    tp = BasicTestParent()
    clone = BasicTestParent.from_json(sysjson.loads(sysjson.dumps(tp.to_json())))
    assert clone.str_attr == tp.str_attr
    assert clone.num_attr == tp.num_attr
    assert clone.bool_attr == tp.bool_attr
    assert clone.list_attr == tp.list_attr
    assert clone.dict_attr == tp.dict_attr
    assert clone.none_attr == tp.none_attr


class ComplexTestParent(BasicTestParent):
    def __init__(self):
        super().__init__()
        self.dt_attr = datetime.now()
        self.obj_attr = None

    @staticmethod
    def from_json(json: dict):
        tp = ComplexTestParent()
        tp.extract_system_fields(json)
        return tp

    def get_custom_mapping(self):
        return {"dt_attr": DATETIME_FORMAT, "obj_attr": BasicTestParent}

    def get_attribute_mapping(self) -> dict:
        return default_options(super().get_attribute_mapping(), {
            "dt_attr": "dt",
            "obj_attr": "obj",
        })


def test_complex_json():
    ctp = ComplexTestParent()
    test_dt = datetime(2023, 7, 5, 16, 43)
    ctp.dt_attr = test_dt
    ctp.obj_attr = BasicTestParent()
    clone = ComplexTestParent.from_json(sysjson.loads(sysjson.dumps(ctp.to_json())))
    # assert basic attributes of instance
    assert clone.str_attr == ctp.str_attr
    assert clone.num_attr == ctp.num_attr
    assert clone.bool_attr == ctp.bool_attr
    assert clone.list_attr == ctp.list_attr
    assert clone.dict_attr == ctp.dict_attr
    assert clone.none_attr == ctp.none_attr
    assert clone.dt_attr == test_dt
    # assert basic json object attributes of child
    assert clone.obj_attr.str_attr == ctp.obj_attr.str_attr
    assert clone.obj_attr.num_attr == ctp.obj_attr.num_attr
    assert clone.obj_attr.bool_attr == ctp.obj_attr.bool_attr
    assert clone.obj_attr.list_attr == ctp.obj_attr.list_attr
    assert clone.obj_attr.dict_attr == ctp.obj_attr.dict_attr
    assert clone.obj_attr.none_attr == ctp.obj_attr.none_attr


class ListCustomObject(BasicTestParent):
    def get_custom_mapping(self):
        return {
            "list_attr": BasicTestParent,
        }

    @staticmethod
    def from_json(json: dict):
        tp = ListCustomObject()
        tp.extract_system_fields(json)
        return tp


def test_list_of_json_docs():
    parent = ListCustomObject()
    parent.list_attr.append(BasicTestParent())
    parent.list_attr.append(BasicTestParent())

    clone = ListCustomObject.from_json(sysjson.loads(sysjson.dumps(parent.to_json())))
    assert len(clone.list_attr) == 2
    assert clone.list_attr[0].str_attr == parent.list_attr[0].str_attr
    assert clone.list_attr[1].str_attr == parent.list_attr[1].str_attr


class DatetimeObject(BasicTestParent):
    def get_custom_mapping(self):
        return {
            "dict_attr": DATETIME_FORMAT,
            "list_attr": DATETIME_FORMAT,
        }

    @staticmethod
    def from_json(json: dict):
        tp = DatetimeObject()
        tp.extract_system_fields(json)
        return tp


def test_datetime_in_dict():
    do = DatetimeObject()
    test_dt = datetime(2023, 7, 5, 16, 43)
    do.dict_attr = {"test": test_dt}
    do.list_attr.append(test_dt)
    do.list_attr.append(test_dt)
    clone = DatetimeObject.from_json(sysjson.loads(sysjson.dumps(do.to_json())))
    assert clone.dict_attr["test"] == test_dt
    assert clone.list_attr[0] == test_dt
    assert clone.list_attr[1] == test_dt
