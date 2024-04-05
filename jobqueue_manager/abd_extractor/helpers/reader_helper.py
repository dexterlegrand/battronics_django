import re


def get_number(str):
    return int(re.findall(r'\d+', str)[0])


def cast_datetime_to_float(dt):
    total_seconds = (dt.hour * 3600) + (dt.minute * 60) + dt.second  # convert to total seconds since midnight
    total_milliseconds = (total_seconds * 1000) + (dt.microsecond // 1000)  # convert to total milliseconds

    my_float = total_milliseconds / 1000.0  # convert to float, showing seconds with decimal places for milliseconds

    return my_float
