from typing import Iterable, List, Optional, Union

from pbu.default_options import list_join


class DebugObject:
    def __init__(self, debug=False, logger=None):
        self._debug = debug
        self._logger = logger

    def debug(self, *kwargs):
        if self._debug:
            if self._logger is not None:
                self._logger.info(list_join(kwargs, " "))
            else:
                print(*kwargs)


def get_coverage_string(covered: Union[int, Iterable], total: Union[int, Iterable], precision: int = 2) -> str:
    if isinstance(covered, (Iterable)):
        return get_coverage_string(len(covered), total)
    if isinstance(total, (Iterable)):
        return get_coverage_string(covered, len(total))

    if not isinstance(covered, int) or not isinstance(total, int):
        return f"Unable to determine coverage string for inputs ({type(covered)}, {type(total)})"

    if total == 0:
        return f"{covered} / {total} (n/a)"

    percent = (covered / total) * 100
    if percent >= 1 or percent == 0.0:
        return f"{covered} / {total} ({round(percent, precision)}%)"

    # find the first non-0
    pct_str, first_non_zero = str(percent), None
    for i in range(0, len(pct_str)):
        if pct_str[i] == "0" or pct_str[i] == ".":
            continue
        first_non_zero = i
        break

    percent = pct_str[0:first_non_zero + precision]
    return f"{covered} / {total} ({percent}%)"


def print_start_script(title: Optional[str] = None) -> None:
    if title is None:
        print_start_script("Start Script Execution")
        return

    buffer = 3
    dash_line = "".join((len(title) + (2 * buffer)) * ["="])
    buffer_str = "".join(buffer * [" "])
    print(dash_line)
    print(f"{buffer_str}{title}")
    print(dash_line)


def get_debug_steps(total: Union[Iterable, int], percentage_step: int = 10) -> List[int]:
    """
    Creates a list of numbers between 0 and total at given percentage steps.
    """
    total_parsed = total if isinstance(total, int) else len(total)
    perf_steps = [round((pct / 100) * total_parsed) for pct in range(percentage_step, 100, percentage_step)]
    return perf_steps
