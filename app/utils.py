import os
from datetime import datetime, timedelta
from functools import wraps

def list_files(dirname, filter=['.json']):
    result = []
    for maindir, subdir, file_name_list in os.walk(dirname):
        for filename in file_name_list:
            apath = os.path.join(maindir, filename)
            ext = os.path.splitext(apath)[1]

            if ext in filter:
                result.append(apath)

    return result

def throttle(seconds=0, minutes=0, hours=0):
    throttle_period = timedelta(seconds=seconds, minutes=minutes, hours=hours)

    def throttle_decorator(fn):
        time_of_last_call = datetime.min

        @wraps(fn)
        def wrapper(*args, **kwargs):
            nonlocal time_of_last_call
            now = datetime.now()
            if now - time_of_last_call > throttle_period:
                time_of_last_call = now
                return fn(*args, **kwargs)
        return wrapper
    return throttle_decorator