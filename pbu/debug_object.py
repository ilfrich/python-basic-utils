import inspect
import math
import warnings
from typing import Callable, Iterable, List, Optional, Union

import numpy as np

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


# ##################
# BEEP FUNCTIONALITY
# ##################


_DEFAULT_AUDIO_SPEC = {  # note, octave duration
    "success": [(None, None, 0.2), ("C", 5, 0.4), (None, None, 0.2), ("C", 5, 0.2), (None, None, 0.2), ("G", 5, 1)],
    "error": [("G", 5, 0.3), (None, None, 0.2), ("C", 5, 1)], 
}
_SAMPLE_RATE = 44100
_AMP = 8000.0  # amplitutde

_DEFAULT_ERROR_MSG = ("Could not play beep, because 'beepy' is not installed. 'pip install simpleaudio' will solve "
                      "this, provided the OS dependency ALSA development packages are installed.")


def _calculate_frequency(note, octave):
    """
    Calculate the frequency for a given note and octave
    :param note: The note for which to calculate the frequency (e.g., "A", "C#", etc.)
    :param octave: The octave of the note
    :return: The frequency of the note in Hz
    """
    NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    if note is None or octave is None:
        return 0.0
    
    reference_note = "A"
    reference_frequency = 440.0
    reference_octave = 4

    note_number = NOTES.index(note)
    reference_note_number = NOTES.index(reference_note)

    frequency = reference_frequency * 2 ** (octave - reference_octave + (note_number - reference_note_number) / 12)
    return frequency


def play_beep(success: bool = True, audio_specs=_DEFAULT_AUDIO_SPEC):
    try:
        from simpleaudio import play_buffer
    except ImportError:
        print(_DEFAULT_ERROR_MSG)
        return

    audio = []

    def add_sine(frequency=440, duration=0.5) -> List[float]:
        sine_list = []
        data_size = int(_SAMPLE_RATE * duration)
        for x in range(int(data_size)):
            sine_list.append(math.sin(2 * math.pi * frequency * (x / _SAMPLE_RATE)))
        return [int(a * _AMP / 2) for a in sine_list]

    spec = audio_specs["success"] if success is True else audio_specs["error"]

    for beep in spec:
        note, octave, duration = beep
        freq = _calculate_frequency(note, octave)
        audio.extend(add_sine(freq, duration))

    audio = np.array(audio).astype(np.int16)
    play_obj = play_buffer(audio, 1, 2, _SAMPLE_RATE)
    play_obj.wait_done()


def wrap_beep(exec_func: callable, **kwargs):
    if not isinstance(exec_func, Callable):
        raise ValueError(f"Provided callable {exec_func} ({type(exec_func)}) is not a Callable")

    if "title" in kwargs:
        print_start_script(kwargs["title"])

    # clean up kwargs for exec
    sig = inspect.signature(exec_func)
    param_names = sig.parameters.keys()
    remove_keys = []
    for k in kwargs:
        if k not in param_names:
            remove_keys.append(k)
            if k != "title":
                warnings.warn(
                    f"Filtering out provided parameter '{k}' because the exec callable {exec_func} does not support "
                    "this in its signature"
                )
    for k in remove_keys:
        del kwargs[k]

    try:
        # this ensures we inform the user before the script starts that there's no beep available, if the lib is missing
        from simpleaudio import play_buffer
        try:
            exec_func(**kwargs)
            play_beep(success=True)
            return  # done executing
        except BaseException as be:
            play_beep(success=False)
            raise be
    except ImportError:
        print(_DEFAULT_ERROR_MSG)

    exec_func(**kwargs)
