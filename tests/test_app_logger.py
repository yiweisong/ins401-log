import sys
import os
import sys

try:
    from app import app_logger
except:
    sys.path.append(os.getcwd())
    from app import app_logger


app_logger.new_session()
app_logger.create_logger('rtcm_rover')
app_logger.create_logger(os.path.join('SN123', 'user'))
