from pytz import timezone, utc, BaseTzInfo
from datetime import datetime, date, time
from typing import Union, Optional


def to_timezone(localized_datetime: datetime, target_timezone: Union[BaseTzInfo, str]) -> datetime:
    """
    Translates a localized or unlocalized datetime into a date of the given timezone. The resulting datetime object will
    be offset b the number of hours difference between the input timezone and the target timezone.
    :param localized_datetime: a datetime object with or without a tz info set
    :param target_timezone: the timezone to translate the input to, this can be provided as string (name)or pytz
    timezone object.
    :return: a datetime object in the provided timezone with a different hour value than the input parameter.
    """
    if isinstance(target_timezone, str):
        tz = timezone(target_timezone)
        return to_timezone(localized_datetime, tz)

    return datetime.fromtimestamp(localized_datetime.timestamp(), tz=target_timezone)


def to_utc(localized_datetime: datetime) -> datetime:
    """
    Translates a localized datetime of some timezone into an UTC date. The resulting datetime object will be offset by
    the number of hours difference between the input timezone and UTC.
    :param localized_datetime: a datetime object with or without a tz info set.
    :return: a datetime object in UTC with different hour value than the input parameter.
    """
    return to_timezone(localized_datetime, utc)


def combine_date_time(date_obj: date, time_obj: time, opt_timezone: Optional[Union[BaseTzInfo, str]]) -> datetime:
    """
    Combines a date and time object into a datetime object and optionally sets the timezone as well. If the timezone is
    provided, the datetime object will NOT be shifted/translated from your local timezone, but merely it will set the
    tzinfo value for the resulting datetime object.
    :param date_obj: the date component for the resulting datetime object
    :param time_obj: the time component for the resulting datetime object
    :param opt_timezone: (optional) timezone specification for the resulting datetime object. This can be either
    provided as string (name of the timezone) or pytz timezone object.
    :return: a datetime object as combination of the provided date and time elements with an optional timezone info.
    """
    base_dt = datetime(date_obj.year, date_obj.month, date_obj.day, time_obj.hour, time_obj.minute, time_obj.second,
                       time_obj.microsecond)
    if opt_timezone is None:
        return base_dt

    tz = timezone(opt_timezone) if isinstance(opt_timezone, str) else opt_timezone
    return tz.localize(base_dt)


def set_timezone(unlocalized_datetime: datetime, target_timezone: Union[BaseTzInfo, str]) -> datetime:
    """
    Simply sets the timezone part of the datetime for a given datetime object. The provided datetime can already have a
    tzinfo set, in which case it will simply be replaced.
    :param unlocalized_datetime: a datetime object with or without a tz info
    :param target_timezone: a timezone either provided as string (name of timezone) or pytz timezone object.
    :return: a datetime object with the same hour/minute values as the provided input, but the timezone set according to
    the provided parameter.
    """
    if unlocalized_datetime.tzinfo is not None:
        # remove current tz info and call this function again
        return set_timezone(unlocalized_datetime.replace(tzinfo=None), target_timezone)

    if isinstance(target_timezone, str):
        return set_timezone(unlocalized_datetime, timezone(target_timezone))

    return target_timezone.localize(unlocalized_datetime)
