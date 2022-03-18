import argparse
import sys
import os
import signal
import traceback
from functools import wraps

def _build_args():
    """parse input arguments
    """
    parser = argparse.ArgumentParser(
        description='Aceinna python driver input args command:', allow_abbrev=False)

    parser.add_argument("-R", "--reset", dest="reset",  action='store_true',
                        help="Reset local ethernet cache", default=False)

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