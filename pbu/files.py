import json
import os
from typing import List, Optional, Union

from pbu.default_options import default_options, not_none


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
    return path


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

    for search, replace in replacement_map.items():
        identifier = identifier.replace(search, replace)

    return identifier


def check_filesystem_name(file_or_folder_name, allow_dot=False) -> bool:
    # check for relative path specs
    if ".." in file_or_folder_name:
        return False

    # check for invalid characters
    invalid_chars = [" ", "/", "\\", "'", '"', "+", "{", "}", "~", ";", ":", "<", ">", "(", ")", "[", "]", "*", "$",
                     "@", "%", "^", "&", "!", "`", "?", ",", "=", "#", "|"]
    if allow_dot is False:
        invalid_chars.append(".")
    for ch in invalid_chars:
        if ch in file_or_folder_name:
            raise False

    return True


def _search_files(
    search_dir: str,
    search_tokens: List[str],
    ext_filter: List[str] = [],
    ignore_folders: List[str] = [],
    max_depth: Optional[int] = None,
    current_depth: int = 0,
) -> List[str]:
    if max_depth is not None and current_depth > max_depth:
        return []  # abort, we are going too deep
    if ignore_folders is not None and len(ignore_folders) > 0 and os.path.basename(search_dir) in ignore_folders:
        # ignore this folder as we've been asked to
        return []
    if not os.path.exists(search_dir) or not os.path.isdir(search_dir):
        return []  # soft fail, let the main caller check this and throw an error if they want to

    # list files and directories in current search dir
    result = []
    for fn in os.listdir(search_dir):
        fn_path = os.path.join(search_dir, fn)
        if os.path.isdir(fn_path):
            # call search files again
            result.extend(
                _search_files(fn_path, search_tokens, ext_filter, ignore_folders, max_depth, current_depth + 1)
            )
            continue  # that's this folder handled

        # we have a file
        if ext_filter is not None and len(ext_filter) > 0:
            filter_match = False
            # an extension filter has been provided, check if the current file extension is asked for 
            for ext in ext_filter:
                if fn.endswith(ext):
                    # provided extension matches the current file, remember this and we can skip the remaining ones
                    filter_match = True
                    break
            if filter_match is False:
                continue  # skip this file as it doesn't have one of the allowed file extensions

        match = True
        for token in search_tokens:
            if token not in fn:
                # missing token in file name, can immediately stop processing and remember the mismatch
                match = False
                break
        if match is False:
            continue  # does not contain all the search tokens

        result.append(fn_path)

    return result


def search_files(
    search_dirs: Union[str, List[str]], 
    search_tokens: Union[str, List[str]],
    ext_filter: Union[str, List[str]] = [],  # e.g. csv, json, log
    ignore_folders: Union[str, List[str]] = [],  # e.g. _data, _raw, _temp
    max_depth: Optional[int] = None,
    ignore_invalid: bool = False,
) -> List[str]:
    """
    Searches for files in the provided directories and returns a list of file paths for any files that match the search
    criteria
    :param search_dirs: a single path to a directory or a list of directories. If directories are provided that don't 
    exist an error will be thrown by default, unless ignore_invalid is set to True.
    :param search_tokens: a single token or a list of tokens that have all to be contained in any filename that is to
    be returned.
    :param ext_filter: list of file extensions that are whitelisted. If an empty list is provided, no extension filter
    will be applied.
    :param ignore_folders: a list of folder names to ignore. If an empty list is provided, no folders will be ignored.
    This can be used to exclude log folders, temporary folders or other folders that you don't want to search.
    :param max_depth: search the provided dirs to the provided maximum depth. A max_depth of 1 implies, that each 
    provided search_dir is scanned and each of its sub-directories, but not their sub-directories.
    :param ignore_invalid: a boolean flag that controls the behaviour of invalid search folders. By default, if an 
    invalid search_dir is provided, a ValueError will be raised. If this flag is set to True, the error is ignored and
    the invalid folder skipped.
    :returns: a list of file paths that match the search criteria. Each found file path is combined with the search_dir
    they correspond to.
    :raises ValueError: in case a folder in the provided search_dirs does not exist or is not a directory.
    """
    root_folders = search_dirs if isinstance(search_dirs, list) else not_none([search_dirs])
    tokens = search_tokens if isinstance(search_tokens, list) else not_none([search_tokens])
    ext = ext_filter if isinstance(ext_filter, list) else not_none([ext_filter])
    ignore = ignore_folders if isinstance(ignore_folders, list) else not_none([ignore_folders])
    results = []
    for folder in root_folders:
        if not os.path.exists(folder) or not os.path.isdir(folder):
            if ignore_invalid:
                continue  # skip this folder in search
            # invalid directories by default will cause an error
            raise ValueError(f"Supplied search folder '{folder}' does not exist or is not a directory.")

        results.extend(_search_files(folder, tokens, ext, ignore, max_depth, 0))

    return results
