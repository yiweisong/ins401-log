import os
import logging
import time

LOG_FORMAT = "%(asctime)s - %(levelname)s: %(message)s"
DATE_FORMAT = "%m/%d/%Y %H:%M:%S %p"

file_path = './data/track_{0}.log'.format(time.strftime('%Y%m%d_%H%M%S'))

folder_path = os.path.dirname(file_path)
if not os.path.exists(folder_path):
    os.makedirs(folder_path)

logging.basicConfig(filename=file_path, filemode='w+',
                    level=logging.INFO, format=LOG_FORMAT)

#log_runtime = logging.getLogger("scapy.runtime")

log_debug = logging.getLogger("ins401-log.debug")

def track_log_status(message, *args):
    log_debug.info(message, *args)
