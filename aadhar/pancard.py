import logging
from flask import Blueprint, jsonify, request

from config import FIN_ACCOUNT_ID, FIN_API_KEY
from aadhar.log import log_data
from aadhar.utils import aes_decrypt
from aadhar.idfy_utils import fetch_pan_card_data


# Create a Blueprint instance
pan_bp = Blueprint('pancard', __name__)

@pan_bp.route('/pancard', methods=['POST'])
def pancard_document():
    try:
        request_data = request.json
        mandatory_fields = ['pan_number', 'dob', 'full_name']
        missing_fields = [field for field in mandatory_fields if field not in request_data]
        
        if missing_fields:
            return jsonify({"error": f"Missing mandatory fields: {', '.join(missing_fields)}"}), 400

        headers = {
                'account-id':FIN_ACCOUNT_ID,
                'api-key': FIN_API_KEY,
                'Content-Type': 'application/json',
            } 
        return fetch_pan_card_data(request_data, headers)

    except Exception as e:
        log_data(message=str(e), event_type='/pancard', log_level=logging.ERROR, additional_context = {'request_data': request_data, 'return_data': str(e)})
        return jsonify({"error": str(e)}), 500


# PAN Number Decryption data retrive api
@pan_bp.route('/get/pan/number', methods=["POST"])
def get_pan_number():
    try:
        from aadhar.aadhar import PANCARD_DATA

        reference_id = request.headers.get('Reference-id')

        if not reference_id:
            return jsonify({"error": f"Missing mandatory fields: Reference id"}), 400

        pancard_data = PANCARD_DATA.find_one({'task_id': reference_id})
        if pancard_data:

            result = pancard_data.get('result', {})
            source_output = result.get('source_output', {})
            input_details = source_output.get('input_details', {})

            decrypted_pan_number = aes_decrypt(input_details.get('input_pan_number'))
            if decrypted_pan_number is None:
                return jsonify({"error": "Decryption Pan number failed"}), 500
            
            log_data(message= "Pan Number retrived", event_type='/get/pan/number', log_level=logging.INFO, 
                     additional_context = {'request_data': reference_id, 'return_data': {"input_name" : input_details.get('input_name'),"input_dob": input_details.get('input_dob'),"input_pan_number": decrypted_pan_number, "reference_id" : pancard_data.get('task_id')}})
            return {
                "input_name" : input_details.get('input_name'),
                "input_dob": input_details.get('input_dob'),
                "input_pan_number": decrypted_pan_number, 
                "reference_id" : pancard_data.get('task_id'),
                }, 200

        else:
            message = "No Pan data found in reference_id"
            log_data(message=  message, event_type='/get/pan/number', log_level=logging.ERROR, 
                     additional_context = {'request_data': reference_id, 'return_data': message})
            return message
        
    except Exception as e:
        log_data(message=str(e), event_type='/pan_data', log_level=logging.ERROR, additional_context = {'request_data': reference_id, 'return_data': str(e)})
        return {"error": str(e)}, 500
