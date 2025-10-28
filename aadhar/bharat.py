import logging
from flask import request, jsonify, Blueprint
from dotenv import load_dotenv
from aadhar.log import log_data
from config import AADHAAR_OTP_SENT_URL, AADHAAR_OTP_SUBMIT_URL, CUSTOMER_ID, PRIVATE_API_KEY, BHARAT_PAN_VERIFY_URL, BHARAT_BANK_ACCOUNT_VERIFY_PENNYLESS, BANK_ACCOUNT_PENNYDROP_SEND_URL, BANK_ACCOUNT_PENNYDROP_GET_STATUS_URL, SERVICE_VENDOR
import requests
from aadhar.utils import get_current_time_in_ist, generate_id, upload_files_to_s3_bharat


load_dotenv()

bharat_bp = Blueprint('api/', __name__)


@bharat_bp.route('/get_service_vendor', methods=['GET'])
def get_service_vendor():
    """
    Get Current Service Vendor
    ---
    tags:
      - Vendor API
    summary: Retrieve the configured service vendor (e.g., IDFY or Bharat)
    responses:
      200:
        description: Successfully fetched the service vendor
        schema:
          type: object
          properties:
            service_vendor:
              type: string
              example: IDFY
      500:
        description: SERVICE_VENDOR not set or internal server error
        schema:
          type: object
          properties:
            error:
              type: string
              example: SERVICE_VENDOR not set
    """
    try:
        service_vendor = SERVICE_VENDOR
        log_data(message=f"Service vendor sent it IDFY or Bharat", event_type='/get_service_vendor', log_level=logging.INFO, additional_context = {"service_vendor": service_vendor})
        if service_vendor:
            return jsonify({"service_vendor": service_vendor}), 200
        else:
            return jsonify({"error": "SERVICE_VENDOR not set"}), 500
    except Exception as e:
        log_data(message=f"Exception error: {str(e)}", event_type='/get_service_vendor', log_level=logging.ERROR)
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@bharat_bp.route('/aadhaar/send-otp', methods=['POST'])
def send_otp():
    """
    Send Aadhaar OTP 
    ---
    operationId: "1. Send otp to aadhaar user"

    tags:
      - Aadhaar Verification via Bharat API
    summary: Initiate Aadhaar OTP request
    description: Sends OTP to the provided 12-digit Aadhaar number using Bharat API
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - aadhaar_no
          properties:
            aadhaar_no:
              type: string
              example: "123412341234"
              description: 12-digit Aadhaar number without spaces
    responses:
      200:
        description: OTP sent successfully
        schema:
          type: object
          properties:
            message:
              type: string
              example: Otp has sent successfully
            request_id:
              type: string
              example: req_abc123456
            result_id:
              type: string
              example: res_def7890
      400:
        description: Invalid Aadhaar number
        schema:
          type: object
          properties:
            status:
              type: string
              example: error
            code:
              type: integer
              example: 400
            error:
              type: string
              example: Invalid 'aadhaar'. Must be a 12-digit number without spaces.
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
        from aadhar.aadhar import MDB_BHARAT_API_RECORDS
        data = request.get_json()
        aadhaar_no = data.get("aadhaar_no", "").replace(" ", "")

        if not aadhaar_no or not aadhaar_no.isdigit() or len(aadhaar_no) != 12:
            return jsonify({
                "status": "error",
                "code": 400,
                "error": "Invalid 'aadhaar'. Must be a 12-digit number without spaces."
            }), 400
        request_id = generate_id()

        payload = {
            "request_id": request_id,
            "aadhaar": aadhaar_no
        }

        # Set headers using env values
        headers = {
            "Content-Type": "application/json",
            "customer-id": CUSTOMER_ID,
            "private-api-key": PRIVATE_API_KEY
        }
   
        response = requests.post(AADHAAR_OTP_SENT_URL, json=payload, headers=headers)
        log_data(message="Recevied the response from bharat aadhaar sent otp", event_type='/aadhaar/send-otp', log_level=logging.INFO, 
                 additional_context = {'payload_data_json': payload, 'response_data': response.json()})
        
        if response.status_code == 200:
            MDB_BHARAT_API_RECORDS.insert_one({
                "aadhaar_no": aadhaar_no,
                "request_id": request_id,
                "status": "pending",
                "created_at": get_current_time_in_ist(),
                "sent_response": response.json() if response.json() else {},
                "result_id": response.json().get("data", {}).get("result_id") if response.json().get("data") else None,
                "updated_at": get_current_time_in_ist(),
                "type":"aadhaar"
            })

            log_data(message="User request and response data", event_type='/aadhaar/send-otp', log_level=logging.INFO, 
                     additional_context = {'request_data': data, 'return_data': {"message":"Otp has sent successfully","request_id":request_id, "result_id":response.json().get("data",{}).get("result_id")}, 'status_code': 200})
            return jsonify({"message":"Otp has sent successfully","request_id":request_id, "result_id":response.json().get("data",{}).get("result_id")}), 200
        
        else:
            MDB_BHARAT_API_RECORDS.insert_one({
                "aadhaar_no": aadhaar_no,
                "request_id": request_id,
                "status": "failed",
                "created_at": get_current_time_in_ist(),
                "sent_response": response.json() if response.json() else {},
                "updated_at": get_current_time_in_ist(),
                "type":"aadhaar"
            })

            log_data(message="User request and response data", event_type='/aadhaar/send-otp', log_level=logging.ERROR, 
                     additional_context = {'request_data': data, 'return_data': {"error": response.json().get("error", "aadhaar must be correct")}, 'status_code': response.status_code})
            return jsonify({"error": response.json().get("error", "aadhaar must be correct")}), response.status_code


    except Exception as e:
        log_data(message=f"Exception error: {str(e)}", event_type='/aadhaar/send-otp', log_level=logging.ERROR)
        return jsonify({"error": str(e)}), 500
    

@bharat_bp.route('/aadhaar/verify-otp', methods=['POST'])
def submit_verify_otp():
    """
    Verify Aadhaar OTP
    ---
    operationId: "2.Verification otp from Bharat API"
    tags:
      - Aadhaar Verification via Bharat API
    summary: Submit Aadhaar OTP for verification
    description: Verifies the Aadhaar OTP using request_id and result_id provided during OTP request
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - request_id
            - result_id
            - otp
          properties:
            request_id:
              type: string
              example: req_abc123456
            result_id:
              type: string
              example: res_def7890
            otp:
              type: string
              example: "123456"
    responses:
      200:
        description: OTP verified successfully
        schema:
          type: object
          properties:
            name:
              type: string
              example: AJITH KUMAR
            dob:
              type: string
              example: 1995-03-12
            gender:
              type: string
              example: M
            image:
              type: string
              example: https://example.com/aadhaar-photo.jpg
            uid:
              type: string
              example: 123456789012
      400:
        description: Missing required fields
        schema:
          type: object
          properties:
            error:
              type: string
              example: All fields ('request_id', 'result_id', 'otp') are required
      422:
        description: Verification failed due to incorrect OTP or expired result
        schema:
          type: object
          properties:
            error:
              type: string
              example: Invalid OTP entered
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
        from aadhar.aadhar import MDB_BHARAT_API_RECORDS
        data = request.get_json()

        request_id = data.get("request_id")
        result_id = data.get("result_id")
        otp = data.get("otp")

        if not all([request_id, result_id, otp]):
            return jsonify({"error": "All fields ('request_id', 'result_id', 'otp') are required"}), 400
        
        old_data = MDB_BHARAT_API_RECORDS.find({"request_id":request_id, "result_id":result_id})
        if old_data is None:
            return jsonify({"error":"Record not found"})
        
        payload = {
            "request_id": request_id,
            "result_id": result_id,
            "otp": otp
        }

        headers = {
            "Content-Type": "application/json",
            "customer-id": CUSTOMER_ID,
            "private-api-key": PRIVATE_API_KEY
        }

        response = requests.post(AADHAAR_OTP_SUBMIT_URL, json=payload, headers=headers)
        response_json = response.json()
        log_data(message="Recevied the response form Bharat aadhaar verify", event_type='/aadhaar/verify-otp', log_level=logging.INFO, 
                 additional_context = {'payload_data_json': payload, 'response_data': response_json})
        
        if response_json.get("error"):
            log_data(message="User request and response data", event_type='/aadhaar/verify-otp', log_level=logging.ERROR, 
                     additional_context = {'request_data': data, 'return_data': {"error": response_json.get("error", "unable to verify")}, 'status_code': 422})
            return jsonify({"error": response_json.get("error", "unable to verify")}), 422

        if response.status_code == 200:
            image_file  = response_json.get("data").get("image")
            s3_file_urls = None
            if image_file:
                s3_file_urls = upload_files_to_s3_bharat(image_file, request_id)
                if s3_file_urls.get("error"):
                    log_data(message="Error on s3 in image upload", event_type='/aadhaar/verify-otp', log_level=logging.INFO, 
                             additional_context = {'request_id': request_id, 'result_id': result_id, 's3_file_urls': s3_file_urls}) 

                    return jsonify({"error": s3_file_urls.get("error")}), 500
           
            MDB_BHARAT_API_RECORDS.update_one(
                {"request_id": request_id, "result_id": result_id},
                {
                    "$set": {
                        "status": "completed",
                        'image_file_url': s3_file_urls.get("link") if s3_file_urls else None,
                        "updated_at": get_current_time_in_ist(),
                        "verify_response": response_json if response_json else {}
                    }
                }
            )

            log_data(message="User request and response data", event_type='/aadhaar/verify-otp', log_level=logging.INFO, 
                     additional_context = {'request_data': data, 'return_data': response_json.get("data", {}), 'status_code': 200})
            return jsonify(response_json.get("data", {})), 200
        
        else:
            MDB_BHARAT_API_RECORDS.update_one(
                {"request_id": request_id, "result_id": result_id},
                {
                    "$set": {
                        "status": "verification_failed",
                        "updated_at": get_current_time_in_ist(),
                        "verify_response": response_json if response_json else {}
                    }
                }
            )

            log_data(message="User request and response data", event_type='/aadhaar/verify-otp', log_level=logging.ERROR, 
                     additional_context = {'request_data': data, 'return_data': {"error": response_json.json().get("error", "unable to verify")}, 'status_code': response.status_code})
            return jsonify({"error": response_json.json().get("error", "unable to verify")}), response.status_code

    except Exception as e:
        log_data(message=f"Exception error: {str(e)}", event_type='/aadhaar/verify-otp', log_level=logging.ERROR)
        return jsonify({"error": str(e)}), 500
    
    
@bharat_bp.route('/pan/verify', methods=['POST'])
def verify_pan():
    """
    PAN Verification
    ---
    tags:
      - PAN Verification via Bharat API
    summary: Verifies PAN card details using full name and date of birth
    description: Sends a request to Bharat API to verify PAN details based on the provided full name, date of birth, and PAN number.
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - full_name
            - date_of_birth
            - pan_number
          properties:
            full_name:
              type: string
              example: "Rahul Sharma"
              description: Full name as printed on PAN card
            date_of_birth:
              type: string
              example: "1995-01-15"
              description: Date of birth in YYYY-MM-DD format
            pan_number:
              type: string
              example: "ABCDE1234F"
              description: 10-digit PAN number
    responses:
      200:
        description: PAN verification successful
        schema:
          type: object
          properties:
            message:
              type: string
              example: "PAN verification successful"
            response:
              type: object
              description: API response from Bharat
      400:
        description: Missing or invalid input fields
        schema:
          type: object
          properties:
            status:
              type: string
              example: "error"
            error:
              type: string
              example: "Fields 'full_name', 'date_of_birth', and 'pan' are required."
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Internal server error: [error details]"
    """
    try:
        from aadhar.aadhar import MDB_BHARAT_API_RECORDS
        data = request.get_json()
        full_name = data.get("full_name", "").strip()
        dob = data.get("date_of_birth", "").strip()
        pan = data.get("pan_number", "").strip().upper()
        # Input validation
        if not (full_name and dob and pan):
            return jsonify({
                "status": "error",
                "code": 400,
                "error": "Fields 'full_name', 'date_of_birth', and 'pan' are required."
            }), 400

        request_id = generate_id()
        payload = {
            "request_id": request_id,
            "full_name": full_name,
            "date_of_birth": dob,
            "pan": pan
        }

        headers = {
            "Content-Type": "application/json",
            "customer-id": CUSTOMER_ID,
            "private-api-key": PRIVATE_API_KEY
        } 

        response = requests.post(BHARAT_PAN_VERIFY_URL, json=payload, headers=headers)
        log_data(message="Response data from bharat pan verify", event_type='/pan/verify', log_level=logging.INFO, 
                 additional_context = {'payload_data_json': payload, 'response_data': response.json(), 'response_status_code': response.status_code}) 

        MDB_BHARAT_API_RECORDS.insert_one({
            "full_name": full_name,
            "date_of_birth": dob,
            "pan": pan,
            "request_id": request_id,
            "status": "success" if response.status_code == 200 else "failed",
            "created_at": get_current_time_in_ist(),
            "sent_response": response.json() if response.json() else {},
            "updated_at": get_current_time_in_ist(),
            "type": "pan"
        })

        if response.status_code == 200:
            log_data(message="User request and response data", event_type='/pan/verify', log_level=logging.INFO, 
                     additional_context = {'request_data': data, 'return_data': {"message": "PAN verification successful","response": response.json()}, 'status_code': 200})
            return jsonify({
                "message": "PAN verification successful",
                "response": response.json()
            }), 200
    
        else:
            log_data(message="User request and response data", event_type='/pan/verify', log_level=logging.ERROR, 
                     additional_context = {'request_data': data, 'return_data': {"message": "PAN verification failed", "response": response.json()}, 'status_code': response.status_code})
            return jsonify({
                "message": "PAN verification failed",
                "response": response.json()
            }), response.status_code

    except Exception as e:
        log_data(message=f"Exception error: {str(e)}", event_type='/pan/verify', log_level=logging.ERROR)
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@bharat_bp.route('/bank-account/send-request', methods=['POST'])
def bank_account_send_request():
    """
    Initiate Bank Account Verification (Penny Drop)
    ---
    operationId: "1. Send request to Bharat API"
    tags:
      - Bank Account Verification via Bharat API
    summary: Send a request to verify bank account and IFSC using Bharat API
    description: Validates the bank account number and IFSC code, sends a verification request to Bharat API (Penny Drop), and stores the result.
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - bank_account
            - ifsc
          properties:
            bank_account:
              type: string
              example: "123456789012"
              description: Bank account number (only digits)
            ifsc:
              type: string
              example: "HDFC0001234"
              description: Valid 11-character IFSC code
    responses:
      200:
        description: Request sent successfully or already verified
        schema:
          type: object
          properties:
            message:
              type: string
              example: Request sent successfully
            request_id:
              type: string
              example: "REQ-1698752345234"
            result_id:
              type: string
              example: "RESULT-98012313213"
      400:
        description: Invalid input (bank account or IFSC code)
        schema:
          type: object
          properties:
            error:
              type: string
              example: Invalid IFSC code
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
              example: An unexpected error occurred
    """
    try:
        from aadhar.aadhar import MDB_BHARAT_API_RECORDS
        data = request.get_json()

        bank_account = data.get("bank_account", "").strip()
        ifsc = data.get("ifsc", "").strip()

        if not bank_account or not bank_account.isdigit():
            return jsonify({"status": "error", "code": 400, "error": "Invalid bank account"}), 400
        if not ifsc or len(ifsc) != 11:
            return jsonify({"status": "error", "code": 400, "error": "Invalid IFSC code"}), 400
     
        # Check if the bank account and IFSC already exist in the database that responded with a completed status
        exists_data = MDB_BHARAT_API_RECORDS.find_one({"type": "bank_account", "status": "completed", "bank_account": bank_account, "ifsc": ifsc})
        if exists_data:
            log_data(message="User request and response data", event_type='/bank-account/send-request', log_level=logging.INFO, 
                     additional_context = {'request_data': data, 'return_data': exists_data.get('verify_response').get("data", {}), 'status_code': 200}) 
            return jsonify(exists_data.get('verify_response').get("data", {})), 200

        request_id = generate_id()
        payload = {
            "request_id": request_id,
            "bank_account": bank_account,
            "ifsc": ifsc
        }

        headers = {
            "Content-Type": "application/json",
            "customer-id": CUSTOMER_ID,
            "private-api-key": PRIVATE_API_KEY
        }
       
        response = requests.post(BANK_ACCOUNT_PENNYDROP_SEND_URL, json=payload, headers=headers)
        log_data(message="Response data from bharat bank-account", event_type='/bank-account/send-request', log_level=logging.INFO, 
                 additional_context = {'payload_data_json': payload, 'response_data': response.json(), 'status_code': response.status_code}) 

        result_id = response.json().get("data", {}).get("result_id")

        MDB_BHARAT_API_RECORDS.insert_one({
            "bank_account": bank_account,
            "ifsc": ifsc,
            "request_id": request_id,
            "result_id": result_id,
            "status": "pending" if response.status_code == 200 else "failed",
            "created_at": get_current_time_in_ist(),
            "updated_at": get_current_time_in_ist(),
            "sent_response": response.json(),
            "type": "bank_account"
        })

        if response.status_code == 200:
            log_data(message="User request and response data", event_type='/bank-account/send-request', log_level=logging.INFO, 
                     additional_context = {'request_data': data, 'return_data': {"message": "Request sent successfully", "request_id": request_id,
                                                                                 "result_id": result_id}, 'status_code': 200}) 
            return jsonify({
                "message": "Request sent successfully",
                "request_id": request_id,
                "result_id": result_id
            }), 200
        
        else:
            log_data(message="User request and response data", event_type='/bank-account/send-request', log_level=logging.ERROR, 
                     additional_context = {'request_data': data, 'return_data': {"error": response.json().get("error", "Invalid request"), 'status_code': response.status_code}}) 
            return jsonify({"error": response.json().get("error", "Invalid request")}), response.status_code

    except Exception as e:
        log_data(message=f"Exception error: {str(e)}", event_type='/bank-account/send-request', log_level=logging.ERROR)
        return jsonify({"error": str(e)}), 500


@bharat_bp.route('/bank-account/get-status', methods=['POST'])
def bank_account_get_status():
    """
    Get Bank Account Verification Status (Penny Drop)
    ---
    operationId: "2. Get verification status from Bharat API"
    tags:
      - Bank Account Verification via Bharat API
    summary: Check the status of a bank account verification request
    description: Returns the verification result for a previously submitted bank account and IFSC combination using request_id and result_id.
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - request_id
            - result_id
          properties:
            request_id:
              type: string
              example: "REQ-1698752345234"
              description: Request ID received during initiation
            result_id:
              type: string
              example: "RESULT-98012313213"
              description: Result ID returned by Bharat API
    responses:
      200:
        description: Verification status returned successfully
        schema:
          type: object
          properties:
            status:
              type: string
              example: "SUCCESS"
            account_name:
              type: string
              example: "RAHUL SHARMA"
            account_status:
              type: string
              example: "ACTIVE"
            bank_name:
              type: string
              example: "HDFC Bank"
      400:
        description: Missing required fields
        schema:
          type: object
          properties:
            error:
              type: string
              example: Both 'request_id' and 'result_id' are required
      404:
        description: Record not found
        schema:
          type: object
          properties:
            error:
              type: string
              example: Record not found
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
              example: Unexpected error occurred
    """
    try:
        from aadhar.aadhar import MDB_BHARAT_API_RECORDS
        data = request.get_json()

        request_id = data.get("request_id")
        result_id = data.get("result_id")

        if not all([request_id, result_id]):
            return jsonify({"error": "Both 'request_id' and 'result_id' are required"}), 400

        record = MDB_BHARAT_API_RECORDS.find_one({"request_id": request_id, "result_id": result_id})
        if not record:
            return jsonify({"error": "Record not found"}), 404

        payload = {
            "request_id": request_id,
            "result_id": result_id
        }

        headers = {
            "Content-Type": "application/json",
            "customer-id": CUSTOMER_ID,
            "private-api-key": PRIVATE_API_KEY
        }
        
        response = requests.post(BANK_ACCOUNT_PENNYDROP_GET_STATUS_URL, json=payload, headers=headers)
        log_data(message="Response data from bharat bank-account", event_type='/bank-account/get-status', log_level=logging.INFO, 
                 additional_context = {'payload_data_json': payload, 'response_data': response.json(), 'status_code': response.status_code}) 

        if response.status_code == 200:
            MDB_BHARAT_API_RECORDS.update_one(
                {"request_id": request_id, "result_id": result_id},
                {
                    "$set": {
                        "status": "completed" if response.json().get("data", {}).get("status") == "SUCCESS" else "failed",
                        "updated_at": get_current_time_in_ist(),
                        "verify_response": response.json()
                    }
                }
            )

            log_data(message="User request and response data", event_type='/bank-account/get-status', log_level=logging.INFO, 
                     additional_context = {'request_data': data, 'return_data': response.json().get("data", {}), 'status_code': 200}) 
            return jsonify(response.json().get("data", {})), 200
        
        else:
            log_data(message="User request and response data", event_type='/bank-account/get-status', log_level=logging.ERROR, 
                     additional_context = {'request_data': data, 'return_data': {"error": response.json().get("error", "Unable to get status"), 'status_code': response.status_code}}) 
            return jsonify({"error": response.json().get("error", "Unable to get status")}), response.status_code

    except Exception as e:
        log_data(message=f"Exception error: {str(e)}", event_type='/bank-account/get-status', log_level=logging.ERROR)
        return jsonify({"error": str(e)}), 500


# Bank Account Verification with Pennyless
@bharat_bp.route('/bank-account/verify', methods=['POST'])
def verify_bank_account():
    """
    Verify Bank Account (Pennyless)
    ---
    tags:
      - Bank Account Verification via Bharat API
    summary: Instantly verifies a bank account using IFSC (Pennyless Verification)
    description: Uses Bharat API to verify whether a bank account and IFSC combination is valid. This does not perform a transaction but confirms ownership.
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - bank_account
            - ifsc
          properties:
            bank_account:
              type: string
              example: "123456789012"
              description: Bank account number to verify
            ifsc:
              type: string
              example: "HDFC0001234"
              description: IFSC code of the bank
    responses:
      200:
        description: Bank account verification successful
        schema:
          type: object
          properties:
            message:
              type: string
              example: "Bank account verification successful"
            response:
              type: object
              properties:
                status:
                  type: string
                  example: "SUCCESS"
                account_holder_name:
                  type: string
                  example: "RAHUL SHARMA"
      400:
        description: Invalid input
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Both 'bank_account' and 'ifsc' are required."
      500:
        description: Internal server error
        schema:
          type: object
          properties:
            error:
              type: string
              example: "Internal server error: [error details]"
    """
    try:
        from aadhar.aadhar import MDB_BHARAT_API_RECORDS
        data = request.get_json()

        bank_account = data.get("bank_account", "").strip()
        ifsc = data.get("ifsc", "").strip().upper()

        if not bank_account or not ifsc:
            return jsonify({
                "status": "error",
                "code": 400,
                "error": "Both 'bank_account' and 'ifsc' are required."
            }), 400

        request_id = generate_id()
        payload = {
            "request_id": request_id,
            "bank_account": bank_account,
            "ifsc": ifsc
        }

        headers = {
            "Content-Type": "application/json",
            "customer-id": CUSTOMER_ID,
            "private-api-key": PRIVATE_API_KEY
        }

        response = requests.post(BHARAT_BANK_ACCOUNT_VERIFY_PENNYLESS, json=payload, headers=headers)
        response_data = response.json()
        log_data(message="Response data from bharat", event_type='/bank-account/verify', log_level=logging.INFO, 
                 additional_context = {'payload_data_json': payload, 'response_data': response_data, 'status_code': response.status_code}) 

        MDB_BHARAT_API_RECORDS.insert_one({
            "bank_account": bank_account,
            "ifsc": ifsc,
            "request_id": request_id,
            "status": "success" if response.status_code == 200 else "failed",
            "created_at": get_current_time_in_ist(),
            "sent_response": response_data,
            "updated_at": get_current_time_in_ist(),
            "type": "bank_ifsc"
        })

        if response.status_code == 200:

            log_data(message="User request and response data", event_type='/bank-account/verify', log_level=logging.INFO, 
                     additional_context = {'request_data': data, 'return_data': {"message": "Bank account verification successful", "response": response_data, 'status_code': 200}}) 
            return jsonify({
                "message": "Bank account verification successful",
                "response": response_data
            }), 200
        
        else:
            log_data(message="User request and response data", event_type='/bank-account/verify', log_level=logging.ERROR, 
                     additional_context = {'request_data': data, 'return_data': {"message": "Bank account verification failed", "response": response_data, 'status_code': response.status_code}}) 

            return jsonify({
                "message": "Bank account verification failed",
                "response": response_data
            }), response.status_code

    except Exception as e:
        log_data(message=f"Exception error: {str(e)}", event_type='/bank-account/verify', log_level=logging.ERROR)
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500
    