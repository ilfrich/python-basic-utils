import inspect
import math
import warnings
from datetime import datetime
from typing import Callable, Dict, Iterable, List, Optional, Tuple, Union

import numpy as np

from pbu.date_time import DATETIME_FORMAT
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


def print_start_script(title: Optional[str] = None, add_datetime: bool = True) -> None:
    if title is None:
        print_start_script("Start Script Execution")
        return

    title_date = title if add_datetime is False else f"{title}: {datetime.now().strftime(DATETIME_FORMAT)}"

    buffer = 3
    dash_line = "".join((len(title_date) + (2 * buffer)) * ["="])
    buffer_str = "".join(buffer * [" "])
    print(dash_line)
    print(f"{buffer_str}{title_date}")
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


_DEFAULT_AUDIO_SPEC = {  # (note, octave duration)
    "success": [("F#", 5, 0.2), ("C#", 6, 0.2)],
    "error": [("C#", 5, 0.2), ("F#", 4, 0.5)],
}
_SAMPLE_RATE = 44100
_AMP = 8000.0  # amplitutde

_DEFAULT_ERROR_MSG = ("Could not play beep, because 'simpleaudio' is not installed. 'pip install simpleaudio' will "
                      "solve this, provided the OS dependency ALSA development packages are installed.")


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


_TYPE_NOTES = List[Tuple[Optional[str], Optional[int], Optional[float]]]


def play_beep(spec: _TYPE_NOTES, volume: float = 1.0):
    try:
        from simpleaudio import play_buffer
    except ImportError:
        print(_DEFAULT_ERROR_MSG)
        return

    audio = []
    eff_amp = round(_AMP * volume)

    def add_sine(frequency=440, duration=0.5) -> List[float]:
        sine_list = []
        data_size = int(_SAMPLE_RATE * duration)
        for x in range(int(data_size)):
            sine_list.append(math.sin(2 * math.pi * frequency * (x / _SAMPLE_RATE)))
        return [int(a * eff_amp / 2) for a in sine_list]

    for beep in spec:
        note, octave, duration = beep
        freq = _calculate_frequency(note, octave)
        audio.extend(add_sine(freq, duration))

    audio = np.array(audio).astype(np.int16)
    play_obj = play_buffer(audio, 1, 2, _SAMPLE_RATE)
    play_obj.wait_done()


def wrap_beep(exec_func: callable, volume: float = 1.0, audio_specs: Dict[str, _TYPE_NOTES] = _DEFAULT_AUDIO_SPEC, **kwargs):
    if not isinstance(exec_func, Callable):
        raise ValueError(f"Provided callable {exec_func} ({type(exec_func)}) is not a Callable")
    if not isinstance(audio_specs, dict):
        raise ValueError(f"Provided audio_specs {(type(audio_specs))} is not a dictionary")

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
            success_spec = audio_specs.get("success", _DEFAULT_AUDIO_SPEC["success"])
            play_beep(success_spec, volume)
            return  # done executing
        except BaseException as be:
            error_spec = audio_specs.get("error", _DEFAULT_AUDIO_SPEC["error"])
            play_beep(error_spec, volume)
            raise be
    except ImportError:
        print(_DEFAULT_ERROR_MSG)

    exec_func(**kwargs)
