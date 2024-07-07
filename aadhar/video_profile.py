import json
import os
import logging
from flask import Blueprint, jsonify, request

from aadhar.log import log_data
from aadhar.utils import added_time, generate_id, get_video_verify, pass_profile_id


# Create a Blueprint instance
profile_bp = Blueprint('profile', __name__)


@profile_bp.route('/generate/link', methods=['POST'])
def generate_video_link():
    try:
        request_data = request.json
        if not request_data:
            return jsonify({"error": "Request data is missing"}), 400
        
        required_fields = [
            'home_house', 'home_address', 'home_district',
            'home_pincode', 'home_village', 'home_state'
        ]

        for field in required_fields:
            if field not in request_data:
                return jsonify({"error": f"'{field}' is missing"}), 400
       
        headers = {
                'account-id': os.getenv("PRO_ACCOUNT_ID"),
                'api-key': os.getenv("PRO_API_KEY"),
                'Content-Type': 'application/json',
            }
        
        reference_id = generate_id()
        data = {
            "reference_id": reference_id,
            "config": {
            "id": os.getenv("IDFY_CONFIG_ID")
            },
            "data": {
                "addresses": [
                    {   
                        "type": [" "],
                        "house_number": request_data['home_house'],
                        "street_address": request_data['home_address'],
                        "district": request_data['home_district'],
                        "pincode": request_data['home_pincode'],
                        "city": request_data['home_village'],
                        "state": request_data['home_state'],
                        "country_code": "+91",
                        "country": "India"
                    }
                ]
            }
        }
        
        return get_video_verify(headers, data, reference_id)

    except Exception as e:
        log_data(message={"error": str(e)}, event_type = '/generate/link',log_level=logging.ERROR)
        return jsonify({"error": str(e)}), 500


@profile_bp.route('/video/kyc/status', methods=['POST'])
def video_kyc_status():
    from aadhar.aadhar import FIN_VIDEO_KYC

    try:
        profile_id = request.headers.get('Profile-id')
        if not profile_id:
            return jsonify({"error": "Profile-id is missing in request headers"}), 400
        
        headers = {
                'account-id': os.getenv("PRO_ACCOUNT_ID"),
                'api-key': os.getenv("PRO_API_KEY"),
                'Content-Type': 'application/json',
            }
        response_data, status_code  =  pass_profile_id(headers, profile_id)
      
        if status_code != 200:
            return jsonify({"error": "Failed to update check the profile ID"}), status_code

        kyc_data = FIN_VIDEO_KYC.find_one({'generated_profile_id': profile_id})
        if not kyc_data:
            return jsonify({"error": "KYC data not found"}), 404
        
        response_data['update_status_time'] = added_time()
        FIN_VIDEO_KYC.update_one({'generated_profile_id': profile_id}, {'$set': response_data}, upsert=True)
        
        retrieve_data = {
                    "reviewer_action": response_data.get('reviewer_action', None),
                    "status": response_data.get('status'),
                    "request_time" : kyc_data.get('request_time'),
                    "profile_id": response_data.get('profile_id'), 
                    "reference_id": response_data.get('reference_id'), 
                }
      
        log_data(message="KYC data retrieved successfully", event_type='/video/kyc/status', log_level=logging.INFO)
        return jsonify(retrieve_data), 200

    except Exception as e:
        log_data(message={"error": str(e)}, event_type = '/video/kyc/status',log_level=logging.ERROR)
        return jsonify({"error": str(e)}), 500
    

@profile_bp.route('/video/kyc/document', methods=['POST'])
def video_view_document():
    try:
        profile_id = request.headers.get('Profile-id')
        if not profile_id:
            raise ValueError("Missing 'Profile-id' in request headers")
        
        headers = {
                'account-id': os.getenv("PRO_ACCOUNT_ID"),
                'api-key': os.getenv("PRO_API_KEY"),
                'Content-Type': 'application/json',
            }
        return pass_profile_id(headers, profile_id)

    except Exception as e:
        log_data(message = {"error": str(e)}, event_type = '/verify/data',log_level=logging.ERROR)
        return jsonify({"error": str(e)}), 500
