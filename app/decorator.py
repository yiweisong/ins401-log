import argparse
import sys
import os
import signal
import traceback
from functools import wraps

IS_WINDOWS = sys.platform.__contains__('win32') or sys.platform.__contains__('win64')

def _build_args():
    """parse input arguments
    """
    parser = argparse.ArgumentParser(
        description='Aceinna python driver input args command:', allow_abbrev=False)

    parser.add_argument("-R", "--reset", dest="reset",  action='store_true',
                        help="Reset local ethernet cache", default=False)
    parser.add_argument("--keep-detect", dest="keep_detect",  action='store_true',
                        help="Skip Detect Confirm", default=False)

    return parser.parse_args()

def handle_application_exception(func):
    '''
    add exception handler
    '''
    @wraps(func)
    def decorated(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except KeyboardInterrupt as ex:  # response for KeyboardInterrupt such as Ctrl+C
            # print('User stop this program by KeyboardInterrupt! File:[{0}], Line:[{1}]'.format(
            #     func.__name__, sys._getframe().f_lineno))
            os.kill(os.getpid(), signal.SIGTERM)
            sys.exit()
        except Exception as ex:  # pylint: disable=bare-except
            traceback.print_exc()  # For development
            os._exit(1)
    return decorated

def receive_args(func):
    '''
    build arguments in options
    '''
    @wraps(func)
    def decorated(*args, **kwargs):
        options = _build_args()
        kwargs['options'] = options
        func(*args, **kwargs)
    return decorated

def platform_setup(func):
    '''
    do some prepare work for different platform
    '''
    if IS_WINDOWS:
        from .platform import win
        win.disable_console_quick_edit_mode()
    
    @wraps(func)
    def decorated(*args, **kwargs):
        func(*args, **kwargs)
    return decorated