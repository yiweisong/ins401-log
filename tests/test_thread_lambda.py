import threading
import time


def print_message():
    print('method start')
    time.sleep(1)
    print('method end')


th = threading.Thread(target=lambda: print_message())
print('next invoke')
th.start()
