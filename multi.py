from multiprocessing import (Process, get_start_method,set_start_method)
import os
import time


def info(title):
    print(title)
    print('module name:', __name__)
    print('parent process:', os.getppid())
    print('process id:', os.getpid())


def f(name):
    info('function f')
    print('hello', name)


if __name__ == '__main__':
    print(get_start_method())
    info('main line')
    p = Process(target=f, args=('bob',))
    p.daemon = True
    p.start()
    # p.join()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        p.join()
