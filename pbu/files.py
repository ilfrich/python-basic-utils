import os
import json
from typing import Optional, Union


def write_json(data: Union[dict, list], path: str):
    """
    Writes an object to a json file. This function will take care of opening and closing the file.
    :param data: a list of dictionary - has to be possible to serialise it as JSON.
    :param path: the file path where to write the file to
    """
    if data is None or not isinstance(data, (list, dict)):
        raise ValueError("No or invalid data provided")
    fp = open(path, "w")
    json.dump(data, fp)
    fp.close()


def read_json(path: str) -> Optional[Union[dict, list]]:
    """
    Reads from a json file if it exists and returns the content. This function will take care of opening and closing the
    file.
    :param path: the file path of the json file
    :return: the list of dictionary contained in the json file
    """
    if not os.path.exists(path):
        return None
    fp = open(path)
    data = json.load(fp)
    fp.close()
    return data
