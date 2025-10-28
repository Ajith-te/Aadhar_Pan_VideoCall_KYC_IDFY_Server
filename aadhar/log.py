import logging
from logging.handlers import TimedRotatingFileHandler
import os
from flask import Flask, request

from aadhar.db_logging import database_logging

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
formatter = logging.Formatter('%(asctime)s --- {%(pathname)s:%(lineno)d} --- %(levelname)s --- %(message)s')
log_file = "aadhar_logs/FIN_IDFY.logs"
log_dir = os.path.dirname(log_file)
 
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
    
file_handler = TimedRotatingFileHandler(log_file, when="midnight", interval=1, backupCount=90, delay=True, encoding="utf-8")
file_handler.setFormatter(formatter)
app.logger.addHandler(file_handler)
# logging.shutdown()


def log_data(message, event_type, log_level, additional_context=None):
    browser_info = request.headers.get('User-Agent')
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)
    database_logging(message, event_type, additional_context)

    try:
        log_message = (f"message: {message}  ---- Event: {event_type} ---- browser_info: {browser_info} ---- "
                    f"ip_address: {ip_address} ---- {additional_context}")

        app.logger.log(log_level, log_message, stacklevel=2)

    except Exception as e:
        app.logger.error(f"Failed to log data: {str(e)}")

