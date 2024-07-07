import os
import logging

from flask import Flask, jsonify, request
from dotenv import load_dotenv
from flask_cors import CORS
from pymongo import MongoClient

from aadhar.log import log_data
from aadhar.pancard import pan_bp
from aadhar.video_profile import profile_bp
from aadhar.utils import added_time, fetch_aadhar_card_data, generate_id

load_dotenv()

app = Flask(__name__)
CORS(app)
app.register_blueprint(pan_bp)
app.register_blueprint(profile_bp)

# MongoDB's  connection string
client = MongoClient(os.getenv('DS_MONGO_URI'))
mongodb = client["FINVESTA"]
FIN_AADHAR = mongodb['Finvesta_Aadhar']
FIN_VIDEO_KYC = mongodb['Finvesta_video_kyc']
IDFY_DATA = mongodb['Idfy_data']

FIN_CALLBACK_URL = os.getenv('FIN_CALLBACK_URL')

# index 
@app.route('/', methods=['GET'])
def index():
    return "Hello world IDfy Server - Finvesta v.01"

# <-------------------------------------------------------- IDfy Aadhar -------------------------------------------------------------->


@app.route('/aadharcard', methods=['POST'])
def aadharcard():
    try:
        aadhar_number = request.headers.get('Aadhar-no')
        
        reference_id = generate_id()
        print("reference_id", reference_id)
        if aadhar_number:
            request_data = {
                    'request_time': added_time(),
                    'request_ref_id': reference_id,
                    'aadhar_number': aadhar_number
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
                "key_id": os.getenv('FIN_KEY_ID'),
                "ou_id": os.getenv('FIN_OU_ID'),
                "secret": os.getenv('FIN_SECRET_BASE64'),
                "callback_url": FIN_CALLBACK_URL,
                "doc_type": "ADHAR",
                "file_format": "xml",
                "extra_fields": {}
                }
            }
        return fetch_aadhar_card_data(headers, data)
    
    except Exception as e:
        error_message = {"error": str(e)}
        log_data(message = error_message, event_type='/aadharcard', log_level=logging.ERROR)
        return error_message, 500
        

# IDfy aadhar card callback /callback
@app.route('/callback', methods=['GET', 'POST'])
def callback():
    if request.method == 'GET':
        log_data(message="Enter the callback API GET method", event_type="/callback", log_level=logging.INFO)
        get_params = request.args.to_dict()
        get_json = request.get_json(silent=True)
        get_headers = dict(request.headers)
        response_data = {
            "idfy_callback_get_response_data" :
            {
                "params": get_params,
                "json": get_json,
                "headers": get_headers
            } 
        }
        log_data(message="Received GET request", event_type="/callback", log_level=logging.INFO,
                 additional_context={"response_data": response_data})
        return jsonify(response_data), 200
    
    if request.method == 'POST':
        try:
            idfy_received_data = request.json            
            data_type = idfy_received_data.get('doc_type', None)

            if data_type == 'ADHAR':
                reference_id = idfy_received_data.get('reference_id')
            
                check_ref_number = FIN_AADHAR.find_one({'reference_id': reference_id})
                if check_ref_number:
                    return jsonify({"error": "Reference id already exists"}), 400
                
                idfy_received_data['data_received_time'] = added_time()
                FIN_AADHAR.update_one({'request_ref_id': reference_id}, {'$set': idfy_received_data}, upsert=True)

                log_data(message="Received IDFY Aadhar data", event_type='/callback', log_level=logging.INFO) 
                return "Received IDFY Aadhar Data", 200
            
            profile_id = idfy_received_data.get('profile_id')
            if profile_id:
                check_task_id = FIN_VIDEO_KYC.find_one({'profile_id': profile_id})
                if check_task_id:
                    return jsonify({"error": "profile id already exists"}), 400
                    
                idfy_received_data['data_received_time'] = added_time()
                FIN_VIDEO_KYC.update_one({'generated_profile_id': profile_id}, {'$set': idfy_received_data}, upsert=True)

                log_data(message="Received IDFY Video KYC data", event_type='/callback', log_level=logging.INFO) 
                return "Received Video KYC data", 200
            
            IDFY_DATA.insert_one(idfy_received_data)

            log_data(message="Received IDFY data", event_type='/callback', log_level=logging.INFO) 
            return "Received IDFY data", 200
            
        except Exception as e:
            error_message = {"error": str(e)}
            log_data(message = error_message, event_type='/callback', log_level=logging.ERROR)
            return error_message, 500


# Aadhar verification data retrive api
@app.route('/aadhar_data', methods=["POST"])
def aadhar_data():

    try:
        reference_id = request.headers.get('Reference-id')
        if not reference_id:
            return {"error": "Reference-id header is missing"}, 400

        aadhar_data = FIN_AADHAR.find_one({'request_ref_id': reference_id})
        if not aadhar_data:
            message = "No Aadhar data found for the provided reference_id"
            log_data(message = message, event_type = '/aadhar_data', log_level = logging.ERROR)
            return {"error": message}, 404

        parsed_details = aadhar_data.get('parsed_details', [])
        if not parsed_details:
            message = "No parsed details found in the received data"
            log_data(message = message, event_type = '/aadhar_data', log_level = logging.ERROR)
            return {"error": message}, 404

        retrieve_data = {
                    "aadhaar_name": parsed_details.get('name'),
                    "aadhaar_number" : aadhar_data.get('aadhar_number'),
                    "dob": parsed_details.get('dob'),
                    "gender": parsed_details.get('gender'),
                    "home_house": parsed_details.get('house'),
                    "home_village": parsed_details.get('vtc'),
                    "home_district": parsed_details.get('dist'),
                    "home_state": parsed_details.get('state'),
                    "home_pincode": parsed_details.get('pc'), 
                    "home_address": parsed_details.get('street')
                }

        log_data(message="Aadhar data retrieved successfully", event_type='/aadhar_data', log_level=logging.INFO)
        return retrieve_data, 200

    except Exception as e:
        log_data(message=str(e), event_type='/aadhar_data', log_level=logging.ERROR)
        return {"error": "Internal server error"}, 500

