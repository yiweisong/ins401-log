import os
import time
from io import FileIO


class LogContext:
    root_path = None
    data_folder_path = None
    session_path = None
    initalized = False

    def update(ctx: dict):
        for attr_name in ctx:
            setattr(LogContext, attr_name, ctx[attr_name])

    def to_dict():
        attrs = [attr_name for attr_name in dir(
            LogContext) if not attr_name.startswith('__')]

        dict_obj = {}
        for attr_name in attrs:
            dict_obj[attr_name] = getattr(LogContext, attr_name)

        return dict_obj


class FileLogger:
    _internal_file_access: FileIO

    def __init__(self, path, mode):
        self._internal_file_access = open(file=path, mode=mode)

    def append(self, data):
        self._internal_file_access.write(data)

    def flush(self):
        self._internal_file_access.flush()


def new_session():
    if LogContext.initalized:
        return

    root_path = os.getcwd()
    data_folder_path = os.path.join(root_path, 'data')
    if not os.path.isdir(data_folder_path):
        os.makedirs(data_folder_path)

    formatted_dir_time = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    session_path = os.path.join(data_folder_path,
                                'session_{0}'.format(formatted_dir_time))
    os.mkdir(session_path)

    LogContext.root_path = root_path
    LogContext.data_folder_path = data_folder_path
    LogContext.session_path = session_path
    LogContext.initalized = True


def create_logger(file_path, mode='wb') -> FileLogger:
    file_path = '{0}.bin'.format(file_path)
    abs_file_path = os.path.join(LogContext.session_path, file_path)
    dir_name = os.path.dirname(abs_file_path)
    if not os.path.isdir(dir_name):
        os.makedirs(dir_name, exist_ok=True)

    return FileLogger(abs_file_path, mode)
