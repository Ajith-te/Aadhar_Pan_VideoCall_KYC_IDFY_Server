import os
import time
import uuid
import logging
import requests

from flask import jsonify
from datetime import datetime
from dotenv import load_dotenv

from aadhar.log import log_data

load_dotenv()


# Base URl's for IDfy server
AADHAR_URL = os.getenv("IDFY_AADHAR_URL")
PANCARD_URL = os.getenv("IDFY_PANCARD_URL")
REQUEST_SEND_URL = os.getenv("IDFY_BASE_URL")
PROFILE_URL = os.getenv("IDFY_PRO_URL") 

# Format the current timestamp to include date, time, and AM/PM
def added_time():
    current_time = datetime.now().strftime('%Y-%m-%d %I:%M %p')
    return current_time

# Generate the  id's for send to the IDfy server
def generate_id():
    return uuid.uuid4().hex


def make_idfy_request(url, headers, data=None, method='GET'):

    try:
        if method == 'POST':
            response = requests.post(url, headers=headers, json=data)
        elif method == 'GET':
            response = requests.get(url, headers=headers, params=data)
        else:
            raise ValueError("Unsupported HTTP method")

        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.RequestException as e:
        return None


# <------------------------------------------------------------- IDfy Video verify part ------------------------------------------------------------->


def get_video_verify(headers, data, reference_id):
    from aadhar.aadhar import FIN_VIDEO_KYC

    response_data = make_idfy_request(PROFILE_URL ,headers, data, method='POST')

    if not response_data or "error" in response_data:
        return {"error": "Failed to initiate Video verification"}, 500
    
    request_data = {
        'request_time': added_time(),
        'request_ref_id': reference_id,
        'generated_profile_id': response_data.get('profile_id')
        }
    FIN_VIDEO_KYC.insert_one(request_data)
    log_data(message="Redirect the IDFY url received", event_type = '/generate/link',log_level=logging.INFO)
    return response_data
    

def pass_profile_id(headers, profile_id):
    PROFILE_URL = os.getenv("IDFY_PRO_ID_URL")
    if not PROFILE_URL:
        raise ValueError("Missing IDFY_PRO_ID_URL environment variable")
    pass_url = PROFILE_URL + profile_id
    response_data = make_idfy_request(pass_url ,headers, method='GET')

    if not response_data or "error" in response_data:
        return jsonify({"error": "RESOURCE_NOT_FOUND , Failed to retrieve video verification data"}), 500
    
    return response_data, 200


# <------------------------------------------------------------- IDfy Aadhar Card part ------------------------------------------------------------->

def fetch_aadhar_card_data(headers, data):

    response_data = make_idfy_request(AADHAR_URL,headers, data, method='POST')
    if not response_data or "error" in response_data:
        return {"error": "Failed to initiate Aahdar card verification"}, 500

    request_id = response_data.get('request_id')
    if not request_id:
        return {"error": "Request ID not received for your PAN card"}, 500

    # Make subsequent requests to check the status and get the data
    return check_aadhar_card_status(request_id, headers, num_checks = 2)


# Two time,s check and time different is 5 second's 
def check_aadhar_card_status(request_id, headers, num_checks, delay = 5):

    for _ in range(num_checks):
        time.sleep(delay)  # Add a delay between checks
        response_data = make_idfy_request(REQUEST_SEND_URL, headers, {'request_id': request_id})
        if not response_data or "error" in response_data:
            return {"error": "Failed to check aadhar card status"}, 500

        if response_data:
            task = response_data[0]
            if task.get('status') == 'completed':
                log_data(message ="IDfy Received Digilocker Redirect url successfully", event_type = '/aadharcard',
                                            log_level = logging.INFO, additional_context = str(task))
                return process_completed_aadhar_task(task)
            
            elif task.get('status') == 'in_progress':
                continue
            
            else:
                log_data(message = f"IDfy Redirect the Digilocker url request failed ", event_type = '/aadharcard',
                         log_level = logging.ERROR, additional_context = str(task))
                return {"error": f"Failed to fetch data - {task.get('message', 'Unknown error')}"}, 500

    return {"error": "Reached maximum number of checks without completion"}, 500



def process_completed_aadhar_task(task):

        result = task.get('result', {})
        source_output = result.get('source_output', {})

        redirect_url = source_output.get('redirect_url')  
        reference_id = source_output.get('reference_id')

        return {"reference_id": reference_id,  "redirect_url": redirect_url}, 200



# <-------------------------------------------------------- IDfy Pan Card part -------------------------------------------------------->
    

def fetch_pan_card_data(request_data, headers):

    data = {
        "task_id":  generate_id(),
        "group_id":  generate_id(),
        "data": {
            "id_number": request_data['id_number'],    
            "dob" : request_data['dob'],
            "full_name": request_data['full_name'],
            }
        }

    # Make the first request to initiate document fetching
    response_data = make_idfy_request(PANCARD_URL, headers, data, method='POST')
    if not response_data or "error" in response_data:
        return {"error": "Failed to initiate PAN card verification"}, 500

    request_id = response_data.get('request_id')
    if not request_id:
        return {"error": "Request ID not received for your PAN card"}, 500

    # Make subsequent requests to check the status and get the data
    return check_pan_card_status(request_id, headers, num_checks = 2)


# Two time,s check and time different is 5 second's
def check_pan_card_status(request_id, headers, num_checks, delay = 5):

    for _ in range(num_checks):
        time.sleep(delay)  # Add a delay between checks
        response_data = make_idfy_request(REQUEST_SEND_URL, headers, {'request_id': request_id})

        if not response_data or "error" in response_data:
            return {"error": "Failed to check PAN card status"}, 500

        if response_data:
            task = response_data[0]

            if task.get('status') == 'completed':
                log_data(message=f"IDfy fetch pancard successfully", event_type='/pancard',
                         log_level=logging.INFO, additional_context = str(task))
                return process_completed_pancard_task(task)
            
            elif task.get('status') == 'in_progress':
                continue
           
            else:
                log_data(message=f"IDfy Pan card request failed :{task.get('status')}", event_type='IDfy API Request for pan card data',
                         log_level=logging.ERROR, additional_context = str(task))

                return {"error": f"Failed to fetch data - {task.get('message', 'Unknown error')}"}, 500

    return {"error": "Reached maximum number of checks without completion"}, 500


# Complete the status after serlizer
def process_completed_pancard_task(task):
    result = task.get('result', {})
    source_output = result.get('source_output', {})

    return {
        "status" : task.get('status'),
        "user_input_details" : source_output.get('input_details'),
        "pan_status": source_output.get('pan_status'),
        "dob_match": source_output.get('dob_match'),
        "name_match": source_output.get('name_match'),
        "user_input_details" : source_output.get('input_details'),
        "reference_id" : task.get('task_id')
    }, 200

