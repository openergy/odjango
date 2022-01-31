from rest_framework.exceptions import ValidationError
import pytz
from pandas.tseries.frequencies import to_offset


def validate_timezone(timezone):
    if timezone not in pytz.all_timezones:
        raise ValidationError(
            "Unknown timezone: '%s'. List of available timezones in pytz.all_timezones."% str(timezone))


def validate_timezone_allow_none(timezone):
    if timezone is None:
        return
    validate_timezone(timezone)


def validate_freq(freqstr, allow_empty=False):
    if allow_empty and freqstr == "":
        return
    try:
        to_offset(freqstr)
    except ValueError:
        raise ValidationError("Could not parse freq: '%s'." % freqstr)

