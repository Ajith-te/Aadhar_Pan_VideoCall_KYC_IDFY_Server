import logging

from logging.handlers import TimedRotatingFileHandler
from flask import request, Flask

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)
formatter = logging.Formatter('%(asctime)s --- %(levelname)s --- %(message)s')
log_file = "FIN_IDfy.logs"
file_handler = TimedRotatingFileHandler(log_file, when="D", interval=1, backupCount=5)
file_handler.setFormatter(formatter)
app.logger.addHandler(file_handler)
logging.shutdown()

# Logger modify
def log_data(message, event_type, log_level, additional_context=None):

    browser_info = request.headers.get('User-Agent')
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr)

    log_message = (f"message: {message}  ----  Event: {event_type} ---- browser_info: {browser_info} ---- ip_address: {ip_address} ---- "
                   f"{additional_context}")

    app.logger.log(log_level, log_message)

