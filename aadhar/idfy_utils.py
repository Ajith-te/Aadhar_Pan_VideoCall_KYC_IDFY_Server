import os
import time
import logging
import requests

from aadhar.utils import added_time, aes_encrypt, generate_id
from config import AADHAR_URL, AGENT_CODE_AUTO_URL, PANCARD_URL, PROFILE_URL, REQUEST_SEND_URL
from aadhar.log import log_data


# <------------------------------------------------------------- IDfy API Call------------------------------------------------------------->

def make_idfy_request(url, headers, data=None, method='GET'):

    try:
        if method == 'POST':
            response = requests.post(url, headers=headers, json=data)
        elif method == 'GET':
            response = requests.get(url, headers=headers, params=data)
        else:
            raise ValueError("Unsupported HTTP method")
        return response.json()
    
    except requests.exceptions.RequestException as e:
        return None


# <------------------------------------------------------------- IDfy Aadhar Card part ------------------------------------------------------------->

def fetch_aadhaar_card_data(headers, data):

    response_data = make_idfy_request(AADHAR_URL,headers, data, method='POST')
    log_data(message="Response data from IDFY aadhaar request id", event_type='/aadharcard', log_level=logging.INFO, 
                 additional_context = {'payload_data_json': data, 'response_data': response_data})

    request_id = response_data.get('request_id')
    
    if not request_id:
        log_data(message ="Aadhaar get error from IDfy Redirect", event_type = '/aadharcard', log_level = logging.ERROR, 
                    additional_context = ({'request_data': data, "return_data" : {"error": "Failed to initiate Aadhaar card verification", "Response": response_data}}))
        return {"error": "Failed to initiate Aadhaar card verification", "Response": response_data}, 500
    
    return check_aadhaar_card_status(request_id, headers, num_checks = 2)


# Two time,s check and time different is 5 second's 
def check_aadhaar_card_status(request_id, headers, num_checks, delay = 5):

    for _ in range(num_checks):
        time.sleep(delay)
        response_data = make_idfy_request(REQUEST_SEND_URL, headers, {'request_id': request_id})
        if not response_data or "error" in response_data:
            log_data(message = "Failed to check aadhaar card status", event_type = '/aadharcard', log_level = logging.ERROR, 
                     additional_context = ({'payload_data_json': {'request_id': request_id}, 'response_data': {"Aadhaar_Error": response_data}}))
            return {"error": "Failed to check aadhaar card status", "Response": response_data}, 500

        if response_data:
            log_data(message = f"IDFY aadhaar response after passed request id", event_type = '/aadharcard', log_level = logging.INFO, 
                     additional_context = ({'payload_data_json': {'request_id': request_id}, 'response_data': response_data}))
            task = response_data[0]
            if task.get('status') == 'completed':
                return process_completed_aadhaar_task(task)
            
            elif task.get('status') == 'in_progress':
                continue
            
            else:
                log_data(message = f"Failed to fetch data - status : {task.get('status')}", event_type = '/aadharcard', log_level = logging.ERROR, 
                         additional_context = ({'request_data': {'request_id': request_id}, 'return_data': {"Aadhaar_Error": response_data}}))
                return {"error": f"Failed to fetch data - status : {task.get('status')}-- error: {task.get('error')}"}, 500
    
    log_data(message = "Reached maximum number of checks without completion", event_type = '/aadharcard', log_level = logging.ERROR, 
             additional_context = ({'request_data': {'request_id': request_id}, 'return_data': {"error": "Reached maximum number of checks without completion"}}))
    return {"error": "Reached maximum number of checks without completion"}, 500


def process_completed_aadhaar_task(task):
    result = task.get('result', {})
    source_output = result.get('source_output', {})

    redirect_url = source_output.get('redirect_url')
    reference_id = source_output.get('reference_id')
    log_data(message= "IDfy Digilocker Redirect url successfully", event_type='/aadharcard', log_level=logging.INFO, 
             additional_context = {'request_data': reference_id, 'return_data': {"reference_id": reference_id,  "redirect_url": redirect_url}})        
                
    return {"reference_id": reference_id,  "redirect_url": redirect_url}, 200


# <-------------------------------------------------------- IDfy Pan Card part -------------------------------------------------------->
    

def fetch_pan_card_data(request_data, headers):

    data = {
        "task_id":  generate_id(),
        "group_id":  generate_id(),
        "data": {
            "id_number": request_data['pan_number'],    
            "dob" : request_data['dob'],
            "full_name": request_data['full_name'],
            }
        }

    # Make the first request to initiate document fetching
    response_data = make_idfy_request(PANCARD_URL, headers, data, method='POST')
    log_data(message="Response data from IDFY Pan verify", event_type='/pancard', log_level=logging.INFO, 
                 additional_context = {'payload_data_json': data, 'response_data': response_data})

    request_id = response_data.get('request_id')
    if not request_id:
        log_data(message ="Pan data missing request id", event_type = '/pancard', log_level = logging.ERROR, 
                 additional_context = ({'request_data': request_data, 'return_data': {"error": "Failed to initiate PAN card verification", "Response": response_data}}))
        return {"error": "Failed to initiate PAN card verification", "Response": response_data}, 500

    return check_pan_card_status(request_id, headers, request_data, num_checks = 5, )


# Two time,s check and time different is 5 second's
def check_pan_card_status(request_id, headers, request_data, num_checks, delay = 5):

    for _ in range(num_checks):
        time.sleep(delay)
        response_data = make_idfy_request(REQUEST_SEND_URL, headers, {'request_id': request_id})
        log_data(message = f"IDFY Pan response after passed request id", event_type = '/pancard', log_level = logging.INFO, 
                     additional_context = ({'payload_data_json': {'request_id': request_id}, 'response_data': response_data}))

        if not response_data or "error" in response_data:
            return {"error": "Failed to check PAN card status", "Response": response_data}, 500

        if response_data:
            task = response_data[0]

            if task.get('status') == 'completed':
                return process_completed_pancard_task(task, request_data)
            
            elif task.get('status') == 'in_progress':
                continue
           
            else:
                log_data(message=f"IDfy Pan card request failed :{task.get('status')}", event_type='pancard',
                         log_level=logging.ERROR, additional_context = ({'request_data': request_data, 'return_data': {"error": f"Failed to fetch data,  status :{task.get('status')}"}}))
                return {"error": f"Failed to fetch data,  status :{task.get('status')}"}, 500
            
    log_data(message = "Reached maximum number of checks without completion", event_type = '/pancard', log_level = logging.ERROR, 
                additional_context = ({'request_data': request_data, 'return_data': {"error": "Reached maximum number of checks without completion"}}))
    return {"error": "Reached maximum number of checks without completion"}, 500


# Complete the status after serlizer
def process_completed_pancard_task(task, request_data):
    from aadhar.aadhar import PANCARD_DATA

    task['recieved_data_time'] = added_time()
    result = task.get('result', {})
    source_output = result.get('source_output', {})
    input_details = source_output.get('input_details', {})
    input_pan_number = input_details.get('input_pan_number')

    encrypted_pan_number = aes_encrypt(input_pan_number)
    input_details['input_pan_number'] = encrypted_pan_number    
    PANCARD_DATA.insert_one(task)

    log_data(message = "IDFY pan card data received", event_type = '/pancard',log_level=logging.INFO,
             additional_context = {'request_data':  request_data, 'return_data': task})
    
    return {
        "status" : task.get('status'),
        "pan_status": source_output.get('pan_status'),
        "dob_match": source_output.get('dob_match'),
        "name_match": source_output.get('name_match'),
        "user_input_details" : source_output.get('input_details'),
        "input_pan_number": input_pan_number, 
        "reference_id" : task.get('task_id')
    }, 200


# <------------------------------------------------------------- IDfy Video verify part ------------------------------------------------------------->


def get_video_verify(headers, data, reference_id, request_data):
    from aadhar.aadhar import FIN_VIDEO_KYC

    response_data = make_idfy_request(PROFILE_URL ,headers, data, method='POST')
    log_data(message="Response data from IDFY video kyc", event_type='/generate/video/link', log_level=logging.INFO, 
                 additional_context = {'payload_data_json': data, 'response_data': response_data})

    if not response_data or "error" in response_data:
        return {"error": "Failed to initiate Video verification"}, 500
    
    user_type = request_data.get('user_type', None)
    
    request_data = {
        'request_time': added_time(),
        'request_ref_id': reference_id,
        'generate_profile_id': response_data.get('profile_id'),
        'aadhar_dob': request_data.get('aadhar_dob'),
        'aadhar_name': request_data.get('aadhar_name'),
        'user_type' : user_type,
        "generate_link_response_data": response_data,
        }

    FIN_VIDEO_KYC.insert_one(request_data)
    log_data(message="Redirect the IDFY Video url received", event_type = '/generate/video/link',log_level=logging.INFO,
             additional_context = ({'request_data': request_data, 'return_data': response_data}))

    return response_data


def pass_profile_id(headers, profile_id, email_address = None, user_name = None):
    
    PROFILE_URL = os.getenv("IDFY_PRO_ID_URL")
    if not PROFILE_URL:
        raise ValueError("Missing IDFY_PRO_ID_URL environment variable")
   
    pass_url = PROFILE_URL + profile_id
    response_data = make_idfy_request(pass_url ,headers, method='GET')
    log_data(message="Response data from IDFY video kyc status", event_type='/video/kyc/status', log_level=logging.INFO, 
                 additional_context = {'payload_data_url': pass_url, 'response_data': response_data})

    if not response_data or "error" in response_data:
        return {"error": "RESOURCE_NOT_FOUND , Failed to retrieve video verification data"}, 500
    
    return response_data, 200


# Video kyc get approved on create the auto Agent code
def agent_code_auto(idfy_received_data, agent_data):
    log_data(message="Recieved agent code auto function", event_type='/callback/video_kyc/automation_agentcode', log_level=logging.INFO, 
             additional_context = {'profile_id': idfy_received_data.get('profile_id')})
    
    resources = idfy_received_data.get('resources', {})
    text = resources.get('text', [])
    
    name = None
    dob = None

    if len(text) > 5 and text[5].get('attr') == 'name':
        name = text[5].get('value')
    if len(text) > 4 and text[4].get('attr') == 'dob':
        dob = text[4].get('value')

    if not name or not dob:
        log_data(message="Name or DOB missing in IDFY data", event_type='/callback/video_kyc/automation_agentcode', 
                 log_level=logging.ERROR, additional_context={'profile_id': idfy_received_data.get('profile_id')})
        return 'Agent code not created due to missing Video KYC data'

    if agent_data.get('aadhar_name', '').lower() != name.lower() or agent_data.get('aadhar_dob') != dob:
        log_data(message="name and dob mismatch in video KYC data", event_type='/callback/video_kyc/automation_agentcode', 
                    log_level=logging.ERROR, additional_context={'profile_id': idfy_received_data.get('profile_id')})
        return 'Received Video KYC data Agent code not create'
        
    log_data(message="name and dob matched pass to next step", event_type='/callback/video_kyc/automation_agentcode', log_level=logging.INFO) 

    json_data = {
        'profile_id': idfy_received_data.get('profile_id'),
        'reviewer_action': idfy_received_data.get('reviewer_action'),
        'status': idfy_received_data.get('status')
    }

    try:
        response = requests.post(AGENT_CODE_AUTO_URL, json=json_data, verify=False)
        log_data(message="Received a response from agent code URL", event_type='/callback/video_kyc/automation_agentcode', log_level=logging.INFO, 
                 additional_context={'json_data': json_data, 'status_code': response.status_code, 'response_text': response.text, 'soap_api_url': AGENT_CODE_AUTO_URL})
        
        if response.status_code == 200:
            try:
                response_json = response.json()
                if "error" in response_json:
                    log_data(message="Error in agent code creation response", event_type='/callback/video_kyc/automation_agentcode', log_level=logging.ERROR)
                    return 'Received Video KYC data Agent code not created'
                
                log_data(message="Agent code creation succeeded", event_type='/callback/video_kyc/automation_agentcode', log_level=logging.INFO,
                         additional_context={'profile_id': idfy_received_data.get('profile_id')})
                return 'Received Video KYC data Agent code created'
            
            except ValueError:
                log_data(message="Response is not JSON formatted", event_type='/callback/video_kyc/automation_agentcode', log_level=logging.ERROR)
                return 'Received Video KYC data Agent code not created'
        else:
            log_data(message=f"Agent code creation failed with status code: {response.status_code}", event_type='/callback/video_kyc/automation_agentcode', log_level=logging.ERROR,
                     additional_context={'profile_id': idfy_received_data.get('profile_id')})
            return 'Received Video KYC data Agent code not created'

    except requests.RequestException as e:
        log_data(message=f"Request to agent code URL failed: {e}", event_type='/callback/video_kyc/automation_agentcode', log_level=logging.ERROR,
                 additional_context={'profile_id': idfy_received_data.get('profile_id')})
        return 'Received Video KYC data Agent code not created'

