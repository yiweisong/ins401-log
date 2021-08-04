import sys
import os
import signal
import traceback
from functools import wraps

def handle_application_exception(func):
    '''
    add exception handler
    '''
    @wraps(func)
    def decorated(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except KeyboardInterrupt:  # response for KeyboardInterrupt such as Ctrl+C
            print('User stop this program by KeyboardInterrupt! File:[{0}], Line:[{1}]'.format(
                __file__, sys._getframe().f_lineno))
            os.kill(os.getpid(), signal.SIGTERM)
            sys.exit()
        except Exception as ex:  # pylint: disable=bare-except
            traceback.print_exc()  # For development
            os._exit(1)
    return decorated