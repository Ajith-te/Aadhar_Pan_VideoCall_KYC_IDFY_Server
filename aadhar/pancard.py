
import logging
import os
from bson import json_util
from flask import Blueprint, jsonify, request

from aadhar.log import log_data
from aadhar.utils import fetch_pan_card_data


# Create a Blueprint instance
pan_bp = Blueprint('pancard', __name__)


@pan_bp.route('/pancard', methods=['POST'])
def pancard_document():
    try:
        request_data = request.json

        # Check for mandatory fields
        mandatory_fields = ['id_number', 'dob', 'full_name']
        missing_fields = [field for field in mandatory_fields if field not in request_data]
        
        # If any mandatory field is missing, return an error
        if missing_fields:
            return jsonify({"error": f"Missing mandatory fields: {', '.join(missing_fields)}"}), 400

        headers = {
                'account-id': os.getenv("FIN_ACCOUNT_ID"),
                'api-key': os.getenv("FIN_API_KEY"),
                'Content-Type': 'application/json',
            } 
        return fetch_pan_card_data(request_data, headers)

    except Exception as e:
        log_data(message={"error": str(e)}, event_type = '/aadharcard',log_level=logging.ERROR)
        # Handle any exceptions
        return jsonify({"error": str(e)}), 500


# PAN card verification data retrive api
@pan_bp.route('/pan_data', methods=["POST"])
def pan_data():
    try:
        from aadhar.aadhar import FIN_AADHAR

        reference_id = request.headers.get('Reference-id')
        pancard_data = FIN_AADHAR.find_one({'task_id' : reference_id})

        if pancard_data:
            # Convert ObjectId to string
            pancard_data['_id'] = str(pancard_data['_id'])

            # Serialize using bson.json_util
            log_data(message="Pan data retrived", event_type = '/pan_data', log_level=logging.INFO)
            return json_util.dumps(pancard_data), 200
            
        else:
            message = "No Pan data found in reference_id"
            log_data(message = message, event_type = '/pan_data',log_level=logging.ERROR)
            return message
        
    except Exception as e:
        log_data(message=str(e), event_type = '/pan_data',log_level=logging.ERROR)
        return {"error": str(e)}, 500
