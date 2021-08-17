import os
import logging
import time
from logging import handlers

LOG_FORMAT = "%(asctime)s - %(levelname)s: %(message)s"
DATE_FORMAT = "%m/%d/%Y %H:%M:%S %p"

debug_file_path = './data/track_{0}.log'.format(time.strftime('%Y%m%d_%H%M%S'))
app_file_path = './data/app_{0}.log'.format(time.strftime('%Y%m%d_%H%M%S'))

folder_path = os.path.dirname(debug_file_path)
if not os.path.exists(folder_path):
    os.makedirs(folder_path)

# logging.basicConfig(filename=file_path, filemode='w+',
#                     level=logging.INFO, format=LOG_FORMAT)

#log_runtime = logging.getLogger("scapy.runtime")

log_debug = logging.getLogger("ins401-log.debug")
log_app = logging.getLogger("ins401-log.app")

debug_file_output = logging.FileHandler(
    filename=debug_file_path, mode='w+', encoding='utf-8')
debug_file_output.setFormatter(logging.Formatter(LOG_FORMAT))
log_debug.addHandler(debug_file_output)
log_debug.setLevel(logging.INFO)

app_file_output = logging.FileHandler(
    filename=app_file_path, mode='w+', encoding='utf-8')
app_file_output.setFormatter(logging.Formatter(LOG_FORMAT))
log_app.addHandler(app_file_output)
log_app.setLevel(logging.INFO)

def track_log_status(message, *args):
    log_debug.info(message, *args)
