import os
import json
from typing import Optional, Union
from pbu.default_options import default_options


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


def ensure_directory(path: str):
    """
    Makes sure a certain directory exists. If it doesn't exist, the directory will be created.
    :param path: a path reference (absolute or relative) to the directory that should exist.
    """
    if not os.path.isdir(path):
        os.makedirs(path)


def convert_to_path(identifier: Optional[str], custom_replacements={}) -> Optional[str]:
    if identifier is None:
        return None

    default_replacements = {
        "-": [" ", "(", ")", "|", "[", "]", ".", ",", "/", "\\"],  # replace these values with hyphen
        "": ["`", '"', "'"]  # replace these values with empty string
    }

    replacement_map = {}
    for replacement, searches in default_replacements.items():
        for search in searches:
            replacement_map[search] = replacement

    if custom_replacements is not None:
        replacement_map = default_options(replacement_map, custom_replacements)

    for search, replace in replacement_map:
        identifier = identifier.replace(search, replace)

    return identifier



