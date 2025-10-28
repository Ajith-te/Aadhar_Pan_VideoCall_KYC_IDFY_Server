import psycopg2
import json
from datetime import datetime
import pytz

from config import POSTGRESQL_LOG_DATABASE, POSTGRESQL_LOG_HOST, POSTGRESQL_LOG_PASSWORD, POSTGRESQL_LOG_PORT, POSTGRESQL_LOG_USERNAME

username = POSTGRESQL_LOG_USERNAME
password = POSTGRESQL_LOG_PASSWORD
hostname = POSTGRESQL_LOG_HOST
port     = POSTGRESQL_LOG_PORT
database = POSTGRESQL_LOG_DATABASE


ist_timezone = pytz.timezone('Asia/Kolkata')

def database_logging(message=None, event_type=None, additional_context=None):
    """
    Logs an event to the ccaveunelogging PostgreSQL table.
    
    :param message: Log message
    :param event_type: Route or event type
    :param additional_context: Dictionary of additional data
    """
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(
            host=hostname,
            port=port,
            database=database,
            user=username,
            password=password
        )
        cur = conn.cursor()

        insert_query = """
            INSERT INTO public.idfy_logging (api_route, message, data, data_received_time)
            VALUES (%s, %s, %s, %s)
        """

        api_route = event_type
        log_message = message
        data = additional_context or {}
        data_received_time = datetime.now(ist_timezone).strftime('%Y-%m-%dT%H:%M:%S%z')

        cur.execute(insert_query, (
            api_route,
            log_message,
            json.dumps(data),
            data_received_time
        ))

        conn.commit()

    except Exception:
        conn.rollback()

    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

