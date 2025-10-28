import os
import logging
from flask import Blueprint, jsonify, request

from aadhar.email_html import video_kyc_resend_html_agent
from aadhar.video_status_email import send_email
from config import PRO_ACCOUNT_ID, PRO_API_KEY, VIDEO_KYC_RESEND_SUB_AGENT
from aadhar.log import log_data
from aadhar.utils import added_time, generate_id
from aadhar.idfy_utils import get_video_verify, pass_profile_id


# Create a Blueprint instance
profile_bp = Blueprint('profile', __name__)


@profile_bp.route('/generate/link', methods=['POST'])
def generate_video_link():
    """
    Generate IDFY Video KYC Link
    ---
    operationId: "1. Generate the link"
    tags:
      - Video KYC via IDFY
    summary: Generate a video KYC link via IDFY
    description: Validates user KYC data and sends a request to IDFY to generate a video verification link.
    consumes:
      - application/json
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - home_house
            - home_address
            - home_district
            - home_pincode
            - home_village
            - home_state
            - aadhar_dob
            - aadhar_name
          properties:
            home_house:
              type: string
              example: "12A"
            home_address:
              type: string
              example: "Main Street"
            home_district:
              type: string
              example: "Bhopal"
            home_pincode:
              type: string
              example: "462001"
            home_village:
              type: string
              example: "Kotra"
            home_state:
              type: string
              example: "Madhya Pradesh"
            aadhar_dob:
              type: string
              example: "1990-01-01"
            aadhar_name:
              type: string
              example: "Ravi Kumar"
    responses:
      200:
        description: Video KYC link generated successfully
        schema:
          type: object
      400:
        description: Missing or invalid fields
        schema:
          type: object
          properties:
            error:
              type: string
              example: "'home_house' is missing"
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
              example: Internal server error occurred
    """
    try:
        request_data = request.json
        if not request_data:
            return jsonify({"error": "Request data is missing"}), 400
        
        required_fields = [
            'home_house', 'home_address', 'home_district',
            'home_pincode', 'home_village', 'home_state', 'aadhar_dob', 'aadhar_name'
        ]

        for field in required_fields:
            if field not in request_data:
                return jsonify({"error": f"'{field}' is missing"}), 400
       
        headers = {
                'account-id': PRO_ACCOUNT_ID,
                'api-key': PRO_API_KEY,
                'Content-Type': 'application/json',
            }
        
        reference_id = generate_id()
        json_data = {
            "reference_id": reference_id,
            "config": {
            "id": os.getenv("IDFY_CONFIG_ID")
            },
            "data": {
                "name": {
                    "first_name": request_data['aadhar_name'], "last_name": " ","middle_name": " "},
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
                        "country": "India",
                    }
                ]
            }
        }
        
        return get_video_verify(headers, json_data, reference_id, request_data)

    except Exception as e:
        log_data(message={"error": str(e)}, event_type = '/generate/link',log_level=logging.ERROR)
        return jsonify({"error": str(e)}), 500


@profile_bp.route('/video/kyc/status', methods=['POST'])
def video_kyc_status():
    """
    Get Video KYC Status (IDFY)
    ---
    operationId: "2. Get video kyc status"

    tags:
      - Video KYC via IDFY
    summary: Check the status of video KYC using IDFY
    description: Retrieves KYC status for a user based on profile ID. Compares Aadhaar name and DOB with extracted data.
    consumes:
      - application/json
    parameters:
      - name: Profile-id
        in: header
        required: true
        type: string
        description: IDFY generated profile ID
      - name: body
        in: body
        required: false
        schema:
          type: object
          properties:
            email_address:
              type: string
              example: "user@example.com"
            user_name:
              type: string
              example: "Ravi Kumar"
    responses:
      200:
        description: Video KYC status retrieved successfully
        schema:
          type: object
          properties:
            reviewer_action:
              type: string
              example: "approved"
            status:
              type: string
              example: "completed"
            profile_id:
              type: string
              example: "abc123xyz"
            reference_id:
              type: string
              example: "ref-202406281134"
            request_time:
              type: string
              example: "2024-06-28T11:34:00"
      400:
        description: Missing profile-id in headers
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Profile-id is missing in request headers"
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Internal server error"
    """
    from aadhar.aadhar import FIN_VIDEO_KYC

    try:
        profile_id = request.headers.get('Profile-id')
        data = request.get_json()
        email_address = data.get('email_address') if data else None
        user_name = data.get('user_name') if data else None

        if not profile_id:
            return jsonify({"error": "Profile-id is missing in request headers"}), 400
        
        headers = {
                'account-id': PRO_ACCOUNT_ID,
                'api-key': PRO_API_KEY,
                'Content-Type': 'application/json',
            }
        response_data, status_code  =  pass_profile_id(headers, profile_id, email_address, user_name)
 
        if status_code != 200:
            return jsonify({"error": "Failed to update check the profile ID"}), status_code
        
        '''
        if response_data['reviewer_action'] == 'rejected':
            send_email_kyc_reject(profile_id, email_address, user_name)
        '''

        response_data['update_status_time'] = added_time()

        FIN_VIDEO_KYC.update_one({'generate_profile_id': profile_id}, {'$set': response_data}, upsert=True)
        kyc_data = FIN_VIDEO_KYC.find_one({'generate_profile_id': profile_id})

        resources = kyc_data.get('resources', {})
        text = resources.get('text', [])
        name = None
        dob = None

        if len(text) > 5 and text[5].get('attr') == 'name':
            name = text[5].get('value')
        if len(text) > 4 and text[4].get('attr') == 'dob':
            dob = text[4].get('value')

        if name and dob:
            if (kyc_data.get('aadhar_name', '').lower() != name.lower() or 
                    kyc_data.get('aadhar_dob') != dob):
                log_data(message="Aadhaar verification name or dob mismatch in video KYC data", event_type='/video/kyc/status', log_level=logging.ERROR, 
                    additional_context={'profile_id': profile_id,'database_aadhar_name': kyc_data.get('aadhar_name'),'database_aadhaar_dob': kyc_data.get('aadhar_dob'),
                        'video_kyc_aadhaar_name': name,'video_kyc_aadhar_dob': dob})
                return jsonify({
                    "error": "Aadhar verification name or dob mismatch in video KYC data",
                    'aadhaar_data': {
                        'name': kyc_data.get('aadhar_name'),
                        'dob': kyc_data.get('aadhar_dob')
                    },
                    'video_kyc_aadhaar_data': {
                        'name': name,
                        'dob': dob
                    }
                }), 200

        retrieve_data = {
            "reviewer_action": response_data.get('reviewer_action'),
            "status": response_data.get('status'),
            "request_time": kyc_data.get('request_time'),
            "profile_id": response_data.get('profile_id'),
            "reference_id": response_data.get('reference_id')
        }

        log_data(message="Video KYC data retrieved successfully", event_type='/video/kyc/status', log_level=logging.INFO,
            additional_context={'profile_id': response_data['profile_id'], 'reviewer_action': response_data.get('reviewer_action')})

        return jsonify(retrieve_data), 200

    except Exception as e:
        log_data(message={"error": str(e)}, event_type = '/video/kyc/status',log_level=logging.ERROR)
        return jsonify({"error": str(e)}), 500


@profile_bp.route('/video/kyc/document', methods=['POST'])
def video_view_document():
    try:
        from aadhar.aadhar import FIN_VIDEO_KYC

        profile_id = request.headers.get('Profile-id')
        data = request.get_json()
        email_address = data.get('email_address') if data else None
        user_name = data.get('user_name') if data else None

        if not profile_id:
            raise ValueError("Missing 'Profile-id' in request headers")
        
        headers = {
                'account-id': PRO_ACCOUNT_ID,
                'api-key': PRO_API_KEY,
                'Content-Type': 'application/json',
            }
        response_data, status_code  =  pass_profile_id(headers, profile_id, email_address, user_name)
 
        if status_code != 200:
            return jsonify({"error": "Failed to update check the profile ID"}), status_code
    
        '''
        if response_data['reviewer_action'] == 'rejected':
            send_email_kyc_reject(profile_id, email_address, user_name, response_data)
            '''

        response_data['update_status_time'] = added_time()
        FIN_VIDEO_KYC.update_one({'generate_profile_id': profile_id}, {'$set': response_data}, upsert=True)
        kyc_data = FIN_VIDEO_KYC.find_one({'generate_profile_id': profile_id})

        resources = kyc_data.get('resources', {})
        text = resources.get('text', [])
        
        name = None
        dob = None

        if len(text) > 0:
            attr_0 = text[0].get('attr')
            if attr_0 == 'name':
                name = text[0].get('value')
        
        if len(text) > 1:
            attr_1 = text[1].get('attr')
            if attr_1 == 'dob':
                dob = text[1].get('value')

        if name is not None and dob is not None:
            if kyc_data.get('aadhar_name', '').lower() != name.lower() or kyc_data.get('aadhar_dob') != dob:
                log_data(message="Aadhar verification name and dob mismatch in video KYC data",
                        event_type='/video/kyc/document', log_level=logging.ERROR, additional_context={'profile_id': profile_id})

                return jsonify({
                    "error": "Aadhar verification name and dob mismatch in video KYC data",
                    'aadhar_data': {
                        'name': kyc_data.get('aadhar_name'),
                        'dob': kyc_data.get('aadhar_dob')
                    },
                    'video_kyc_data': {
                        'name': name,
                        'dob': dob
                    }
                }), 200

        log_data(message="Video kyc data retrieved successfully", event_type = '/video/kyc/document', log_level=logging.INFO,
                    additional_context={'profile_id': response_data['profile_id'], 'reviewer_action': response_data['reviewer_action']})
        return jsonify(response_data), 200

    except Exception as e:
        log_data(message = {"error": str(e)}, event_type = '/video/kyc/document',log_level=logging.ERROR)
        return jsonify({"error": str(e)}), 500




# After video kyc rejected ( tm/sh )
def video_kyc_reject_resend_link(idfy_received_data, profile_id):
    from aadhar.aadhar import FINVESTA_USERS

    try:
        agent_data = FINVESTA_USERS.find_one({'video_kyc.profile_id': profile_id})
        if not agent_data:
            log_data(message="Agent data not found in FINVESTA USERS collection", event_type='/callback/new/video/link', log_level=logging.ERROR)
            return "Received Video KYC data", 200
        
        new_video_kyc = video_kyc_generate_link(idfy_received_data)
        remarks = idfy_received_data.get('status_detail', '')
        new_link = new_video_kyc.get('capture_link')
        new_profile_id = new_video_kyc.get('profile_id')
    
        html_body = video_kyc_resend_html_agent(agent_data['first_name'], remarks, new_link, new_profile_id)
        send_email(VIDEO_KYC_RESEND_SUB_AGENT, agent_data['email_address'], html_body)
        
        log_data(message=f"Video KYC re-send link sent successfully to Agent {agent_data['email_address']} {agent_data['first_name']} {new_profile_id}", 
                 event_type='/callback/new/video/link', log_level=logging.INFO)
        
        # Update the new profile_id in the video_kyc object of the agent's data
        FINVESTA_USERS.update_one({'_id': agent_data['_id']}, {'$set': {'video_kyc.profile_id': new_profile_id}})
        
        return "Received Video KYC data", 200

    except Exception as e:
        log_data(message=str(e), event_type='/callback/new/video/link', log_level=logging.ERROR)
        return "Received Video KYC data", 200


def video_kyc_generate_link(idfy_received_data):
    old_data = idfy_received_data.get('tasks', [])[8]
   
    result = old_data.get('result', {})
    automated_response = result.get('automated_response', {})
    result = automated_response.get('result', {})
    xml_output = result.get('xml_output', {})
    address = xml_output.get('address', {})
    
    request_data = {
        'user_type': 'agent',
        'aadhar_dob': xml_output.get('dob'),
        'aadhar_name': xml_output.get('name'),
    }

    headers = {
        'account-id': PRO_ACCOUNT_ID,
        'api-key': PRO_API_KEY,
        'Content-Type': 'application/json',
    }

    reference_id = generate_id()
    json_data = {
        "reference_id": reference_id,
        "config": {
            "id": os.getenv("IDFY_CONFIG_ID")
        },
        "data": {
            "name": {
                "first_name": xml_output.get('name', ""), 
                "last_name": " ", 
                "middle_name": " "
            },
            "addresses": [
                {
                    "type": [" "],
                    "house_number": address.get("house", ""),
                    "street_address": xml_output.get("street_address", ""),
                    "district": address.get("dist", ""),
                    "pincode": address.get("pc", ""),
                    "city": address.get("vtc", ""),
                    "state": address.get("state", ""),
                    "country_code": "+91",
                    "country": "India",
                }
            ]
        }
    }
    new_video_kyc = get_video_verify(headers, json_data, reference_id, request_data)
    return new_video_kyc
