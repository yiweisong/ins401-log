import signal
import os
from app.bootstrap import Bootstrap

def kill_app(signal_int, call_back):
    '''Kill main thread
    '''
    os.kill(os.getpid(), signal.SIGTERM)

if __name__ == '__main__':
    #signal.signal(signal.SIGINT, kill_app)
    Bootstrap().start()