import os
import logging

from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient

from config import DB_CLIENT, FIN_CALLBACK_URL, FIN_KEY_ID, FIN_OU_ID, FIN_SECRET_BASE64, MONGO_URI
from aadhar.log import log_data

from aadhar.pancard import pan_bp
from aadhar.bharat import bharat_bp
from aadhar.video_profile import profile_bp, video_kyc_reject_resend_link
from aadhar.utils import added_time, aes_decrypt, aes_encrypt, ds_flow_server_auto_approved, found_file_link_idfy, generate_id, upload_files_to_s3
from aadhar.idfy_utils import agent_code_auto, fetch_aadhaar_card_data
# from flasgger import Swagger


app = Flask(__name__)
CORS(app)
# swagger = Swagger(app)

app.register_blueprint(pan_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(bharat_bp)

# MongoDB's  connection string
client = MongoClient(MONGO_URI)
mongodb = client[DB_CLIENT]
FIN_AADHAR = mongodb['Finvesta_Aadhar']
FIN_VIDEO_KYC = mongodb['Finvesta_video_kyc']
IDFY_DATA = mongodb['Idfy_data']
PANCARD_DATA = mongodb['Finvesta_PanCard']
FINVESTA_USERS = mongodb['finvesta_users']
MDB_BHARAT_API_RECORDS = mongodb['bharat_api_records']
DISTRIBUTOR_USERS = mongodb['distributor_users']

# index 
@app.route('/', methods=['GET'])
def index():
    """
    Welcome Endpoint
    ---
    tags:
      - Home
    summary: Basic check to confirm the server is running
    responses:
      200:
        description: Server is running successfully
        schema:
          type: string
          example: Hello world IDfy Server K8 v.02
    """
    # log_data(message = 'home', event_type='/', log_level=logging.INFO)
    return "Hello world IDfy Server K8 v.02"

# <-------------------------------------------------------- IDfy Aadhar -------------------------------------------------------------->


@app.route('/aadharcard', methods=['POST'])
def aadharcard():
    """
    Aadhaar Card Verification - IDfy Digilocker url generate
    ---
    operationId: "1. Generate the digilocker url"
    tags:
      - Aadhaar Verification via IDFY
    summary: Initiates Aadhaar card verification using IDfy API
    parameters:
      - name: Aadhar-no
        in: header
        type: string
        required: true
        description: Aadhaar number of the user (will be encrypted before transmission)
    responses:
      200:
        description: Aadhaar verification initiated successfully
        schema:
          type: object
          properties:
            reference_id:
              type: string
              example: 2311a23213rwe123
            redirect_url:
              type: string
              example: https://test.idfy.com/digilocker/auth/xxx
      400:
        description: Bad request or missing Aadhaar number
        schema:
          type: object
          properties:
            error:
              type: string
              example: Aadhaar number not provided
      500:
        description: Internal server error during Aadhaar verification process
        schema:
          type: object
          properties:
            error:
              type: string
              example: Failed to initiate Aadhaar card verification
    """
    try:
        aadhar_number = request.headers.get('Aadhar-no')

        reference_id = generate_id()
        
        if aadhar_number:
            encrypted_aadhar_number = aes_encrypt(aadhar_number)
            request_data = {
                    'request_time': added_time(),
                    'request_ref_id': reference_id,
                    'aadhar_number': encrypted_aadhar_number
                }
            FIN_AADHAR.insert_one(request_data)
        
        headers = {
        'Content-Type': 'application/json',
        'api-key': os.getenv('FIN_API_KEY'),
        'account-id': os.getenv('FIN_ACCOUNT_ID'),
        }

        data = {
            "task_id": reference_id,
            "group_id": generate_id(),
            "data":{
                "reference_id": reference_id,
                "key_id": FIN_KEY_ID,
                "ou_id": FIN_OU_ID,
                "secret": FIN_SECRET_BASE64,
                "callback_url": FIN_CALLBACK_URL,
                "doc_type": "ADHAR",
                "file_format": "xml",
                "extra_fields": {}
                }
            }
        return fetch_aadhaar_card_data(headers, data)
    
    except Exception as e:
        error_message = {"error": str(e)}
        log_data(message = error_message, event_type='/aadharcard', log_level=logging.ERROR)
        return error_message, 500


# IDfy aadhar card callback /callback
@app.route('/callback', methods=['GET', 'POST'])
def callback():
    if request.method == 'GET':
        try:
            log_data(message="Enter the callback API GET method", event_type="/callback/GET", log_level=logging.INFO)
            get_params = request.args.to_dict()
            get_json = request.get_json()
            
            response_data = {
                "idfy_callback_get_response_data": {
                    "params": get_params,
                    "json": get_json,
                }
            }
            log_data(message="Received GET request from IDFY", event_type="/callback/GET", log_level=logging.INFO,
                    additional_context={"response_data": response_data})
            
            return jsonify(response_data), 200
        
        except Exception as e:
            log_data(message = {"error": str(e)}, event_type = "/callback/GET", log_level=logging.ERROR)
            return jsonify({"error": str(e)}), 500
    
    if request.method == 'POST':
        try:
            idfy_received_data = request.json
            log_data(message="Enter the callback API POST method", event_type="/callback/POST", log_level=logging.INFO, 
                     additional_context={"received_data": idfy_received_data})
            
            data_type = idfy_received_data.get('doc_type', None)

            # Aadhar card Reference id check 
            if data_type == 'ADHAR':
                reference_id = idfy_received_data.get('reference_id')
            
                if FIN_AADHAR.find_one({'reference_id': reference_id}):
                    return jsonify({"error": "Reference id already exists"}), 400
                
                idfy_received_data['data_received_time'] = added_time()
                FIN_AADHAR.update_one({'request_ref_id': reference_id}, {'$set': idfy_received_data}, upsert=True)

                log_data(message="Received Aadhar data", event_type='/callback/aadhar/data', log_level=logging.INFO,
                          additional_context = {'reference_id': idfy_received_data['reference_id']})
                
                return "Received IDFY Aadhar Data", 200
            
            # Video KYC Profile id check 
            profile_id = idfy_received_data.get('profile_id')
            if profile_id:
                idfy_received_data['data_received_time'] = added_time()
                idfy_received_data['received_type'] = 'callback_url'

                if idfy_received_data['reviewer_action'] == 'rejected':
                    video_kyc_reject_resend_link(idfy_received_data, profile_id)
                    FIN_VIDEO_KYC.update_one({'generate_profile_id': profile_id}, {'$set': idfy_received_data}, upsert=True)
                    return "Received Video KYC data", 200
                
                profile_id = idfy_received_data.get('profile_id')
                file_data = found_file_link_idfy(idfy_received_data)

                s3_file_urls = upload_files_to_s3(file_data, profile_id)

                idfy_received_data['file_url_s3'] = s3_file_urls

                FIN_VIDEO_KYC.update_one({'generate_profile_id': profile_id}, {'$set': idfy_received_data}, upsert=True)
                log_data(message="Received Video KYC data", event_type='/callback/video/KYC', log_level=logging.INFO, 
                         additional_context = {'profile_id': idfy_received_data['profile_id'], 'reviewer_action': idfy_received_data['reviewer_action']}) 
                
                agent_data = FIN_VIDEO_KYC.find_one({'generate_profile_id': profile_id})
                log_data(message="check the agent data", event_type='/callback/video/KYC', log_level=logging.INFO, 
                         additional_context = {'profile_id': idfy_received_data['profile_id']}) 
                
                if agent_data and agent_data.get('user_type') == 'agent' and idfy_received_data['status'] == 'completed':
                    agent_code_auto(idfy_received_data, agent_data)

                if (agent_data and agent_data.get('user_type') in ['ds', 'mds', 'fos'] and idfy_received_data.get('status') == 'completed'):
                    ds_flow_server_auto_approved(idfy_received_data, agent_data)

                return "Received Video KYC data", 200

            IDFY_DATA.insert_one(idfy_received_data)
            log_data(message="Received IDFY data", event_type='/callback/IDFY/data', log_level=logging.INFO, 
                     additional_context ={'profile_id': idfy_received_data.get('type', None)}) 
            return "Received IDFY data", 200

        except Exception as e:
            error_message = {"error": str(e)}
            log_data(message = error_message, event_type='/callback', log_level=logging.ERROR)
            return error_message, 500


# Aadhar verification data retrive api
@app.route('/aadhar_data', methods=["POST"])
def aadhar_data():
    """
    Retrieve Aadhaar Verification Data
    ---
    operationId: "2. Aadhaar verfication data from IDFY"
    tags:
      - Aadhaar Verification via IDFY
    summary: Fetches parsed Aadhaar data using reference_id from the header
    parameters:
      - name: Reference-id
        in: header
        type: string
        required: true
        description: Reference ID from Aadhaar verification
    responses:
      200:
        description: Aadhaar data retrieved successfully
        schema:
          type: object
          properties:
            aadhaar_name:
              type: string
              example: Ravi Kumar
            uid_number:
              type: string
              example: 123412341234
            dob:
              type: string
              example: 1990-01-01
            gender:
              type: string
              example: M
            home_house:
              type: string
              example: 123
            home_village:
              type: string
              example: Example Village
            home_district:
              type: string
              example: Mumbai
            home_state:
              type: string
              example: Maharashtra
            home_pincode:
              type: string
              example: 400001
            home_address:
              type: string
              example: 123 Example Street
      400:
        description: Aadhaar number does not match or is missing
        schema:
          type: object
          properties:
            error:
              type: string
              example: Aadhar Number not match
      404:
        description: No data found or status is not SUCCESS
        schema:
          type: object
          properties:
            error:
              type: string
              example: No Aadhar data found for the provided reference_id
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
              example: Decryption Aadhar number failed
    """
    try:
        reference_id = request.headers.get('Reference-id')
        if not reference_id:
            return {"error": "Reference-id header is missing"}, 400

        aadhar_data = FIN_AADHAR.find_one({'reference_id': reference_id})
        if not aadhar_data:
            message = "No Aadhar data found for the provided reference_id"
            log_data(message = f"{message}:: {reference_id}", event_type = '/aadhar_data', log_level = logging.ERROR)
            return {"error": message}, 404
        
        if aadhar_data.get('status') !=  'SUCCESS':
            return {"error": aadhar_data.get('status')}, 404

        parsed_details = aadhar_data.get('parsed_details', [])
        if aadhar_data.get('aadhar_number'):
            decrypted_aadhar_number = aes_decrypt(aadhar_data.get('aadhar_number'))
            if decrypted_aadhar_number is None:
                return jsonify({"error": "Decryption Aadhar number failed"}), 500
        
            if decrypted_aadhar_number[-4:] == parsed_details.get('uid')[-4:]:
                retrieve_data = {
                            "aadhaar_name": parsed_details.get('name'),
                            "uid_number": parsed_details.get('uid'),
                            "dob": parsed_details.get('dob'),
                            "gender": parsed_details.get('gender'),
                            "home_house": parsed_details.get('house'),
                            "home_village": parsed_details.get('vtc'),
                            "home_district": parsed_details.get('dist'),
                            "home_state": parsed_details.get('state'),
                            "home_pincode": parsed_details.get('pc'), 
                            "home_address": parsed_details.get('street')
                        }

                
                log_data(message= "Aadhar Number matched, Aadhar data retrieved successfully", event_type='/aadhar_data', log_level=logging.INFO, 
                            additional_context = {'request_data': reference_id, 'return_data': retrieve_data})        
                return retrieve_data, 200
            
            else:
                log_data(message= "Aadhar Number not match", event_type='/aadhar_data', log_level=logging.ERROR, 
                        additional_context = {'request_data': reference_id, 'return_data': {"error": "Aadhar Number not match", "aadhar_number": decrypted_aadhar_number,"uid_number": parsed_details.get('uid')}})        
                
                return {
                    "error": "Aadhar Number not match",
                    "aadhar_number": decrypted_aadhar_number,
                    "uid_number": parsed_details.get('uid')
                }, 400
        
        else:
            log_data(message=  "Aadhar Data retrieved", event_type='/aadhar_data', log_level=logging.ERROR, 
                        additional_context = {'request_data': reference_id, 'return_data': parsed_details})        
            return parsed_details, 200
    
    except Exception as e:
        log_data(message=str(e), event_type='/aadhar_data', log_level=logging.ERROR,
                 additional_context = {'request_data': reference_id, 'return_data': str(e)})
        return {"error": str(e)}, 500

