import base64
import io
import logging

import uuid
import boto3

from PIL import Image 
from datetime import datetime
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
from botocore.exceptions import NoCredentialsError
import requests
import pytz

from config import AES_ENCRYPT_SECRET_KEY, AWS_ACCESS_KEY_ID, AWS_S3_BUCKET_NAME, AWS_SECRET_ACCESS_KEY
from aadhar.log import log_data

s3_client  = boto3.client('s3', aws_access_key_id = AWS_ACCESS_KEY_ID, aws_secret_access_key = AWS_SECRET_ACCESS_KEY)

# Format the current timestamp to include date, time, and AM/PM
def added_time():
    current_time = datetime.now().strftime('%Y-%m-%d %I:%M %p')
    return current_time

# Generate the  id's for send to the IDfy server
def generate_id():
    return uuid.uuid4().hex

def get_current_time_in_ist():
    ist_timezone = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist_timezone).strftime('%Y-%m-%dT%H:%M:%S%z')

# < ----------------------------------------------- AWS S3 Store the IDFY video File ------------------------------------------->

def found_file_link_idfy(idfy_received_data):
    resources = idfy_received_data.get('resources', {})
    
    file_data = {}

    documents = resources.get('documents', [])
    for document in documents:
        key = f"document_{document['ref_id']}"
        file_data[key] = document['value']

    images = resources.get('images', [])
    for image in images:
        key = f"image_{image['ref_id']}"
        file_data[key] = image['value']

    videos = resources.get('videos', [])
    for video in videos:
        key = f"video_{video['ref_id']}"
        file_data[key] = video['value']

    return file_data


def upload_files_to_s3(file_data, profile_id):
    s3_file_urls = {}
    for key, url in file_data.items():
        try:
            response = requests.get(url)
            response.raise_for_status()

            if 'document' in key:
                s3_object_name = f"{profile_id}_{key}.pdf"
            elif 'image' in key:
                s3_object_name = f"{profile_id}_{key}.jpg"
            elif 'video' in key:
                s3_object_name = f"{profile_id}_{key}.mp4"
            else:
                s3_object_name = f"{profile_id}_{key}"

            s3_client.put_object(Bucket=AWS_S3_BUCKET_NAME, Key=s3_object_name, Body=response.content)
            
            s3_file_url = f"https://{AWS_S3_BUCKET_NAME}.s3.amazonaws.com/{s3_object_name}"
            s3_file_urls[key] = s3_file_url
        
        except requests.RequestException as e:
            log_data(message = f"Failed to download file from {url}: {e}", event_type='video_kyc/s3/file', log_level=logging.ERROR)
            s3_file_urls[key] = f"Error: Failed to download file from {url}"

        except NoCredentialsError:
            log_data(message = "Credentials not available", event_type='video_kyc/s3/file', log_level=logging.ERROR)
            s3_file_urls[key] = "Error: AWS credentials not available"
        
        except Exception as e:        
            log_data(message=f"Error uploading file to S3: {e}", event_type='video_kyc/s3/file', log_level=logging.ERROR)
            s3_file_urls[key] = f"Error uploading file to S3: {e}"

    return s3_file_urls


# <--------------------------------------------------  AES Encrypt ----------------------------------------------------->

aes_key = base64.urlsafe_b64decode(AES_ENCRYPT_SECRET_KEY.encode())
fixed_iv = b'0000000000000000'

def pad(data):
    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded_data = padder.update(data.encode()) + padder.finalize()
    return padded_data

def unpad(data):
    unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
    unpadded_data = unpadder.update(data) + unpadder.finalize()
    return unpadded_data

def aes_encrypt(data):
    cipher = Cipher(algorithms.AES(aes_key), modes.CBC(fixed_iv), backend=default_backend())
    encryptor = cipher.encryptor()
    padded_data = pad(data)
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
    return base64.urlsafe_b64encode(encrypted_data).decode()

def aes_decrypt(encrypted_data):
    cipher = Cipher(algorithms.AES(aes_key), modes.CBC(fixed_iv), backend=default_backend())
    decryptor = cipher.decryptor()
    encrypted_data_bytes = base64.urlsafe_b64decode(encrypted_data)
    decrypted_padded_data = decryptor.update(encrypted_data_bytes) + decryptor.finalize()
    decrypted_data = unpad(decrypted_padded_data)
    return decrypted_data.decode()


# <-------------------------------------------------- Bharat  Aadhaar image upload S3 ----------------------------------------------------->

# Upload file s3 bucket
def upload_files_to_s3_bharat(file_object, profile_id):
    try:

        s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY
        )

        s3_object_name = f"bharat_aadhaar_image_{profile_id}.jpg"
        image_data = base64.b64decode(file_object)
        image_file = io.BytesIO(image_data)
        img = Image.open(image_file)

        image_byte_array = io.BytesIO()
        img.save(image_byte_array, format='JPEG')
        image_byte_array.seek(0)

        s3_client.upload_fileobj(
            Fileobj=image_byte_array,
            Bucket=AWS_S3_BUCKET_NAME,
            Key=s3_object_name,
            ExtraArgs={'ContentType': 'image/jpeg'}
        )

        file_url = f"https://{AWS_S3_BUCKET_NAME}.s3.amazonaws.com/{s3_object_name}"

        return {'link': file_url}

    except Exception as e:
        return {'error': str(e)}
    


# <-------------------------------------------------- Auto Approved ds,mds,fos ----------------------------------------------------->

def ds_flow_server_auto_approved(idfy_received_data, agent_data):
    from aadhar.aadhar import DISTRIBUTOR_USERS

    log_data(message="Received ds vkyc status update function", event_type='/callback/video_kyc/ds_auto_approved', log_level=logging.INFO,
        additional_context={'profile_id': idfy_received_data.get('profile_id')})

    generate_profile_id = agent_data.get("generate_profile_id")
    if not generate_profile_id:
        log_data(message="Missing profile_id in agent_data", event_type='/callback/video_kyc/ds_auto_approved', log_level=logging.ERROR,
            additional_context={'profile_id': idfy_received_data.get('profile_id')}
        )
        return "Received Video KYC data", 200

    kyc_approve = {
        "ops_vky_status": 'Approved',
        "ops_vky_status_updated_time": get_current_time_in_ist(),
        "user_code": "Pending",
        "vky_auto_approved": True,
    }

    DISTRIBUTOR_USERS.update_one(
        {"video_kyc.profile_id": generate_profile_id},
        {"$set": kyc_approve}
    )

    log_data(message="Vkyc status updated successfully in distributor_users", event_type='/callback/video_kyc/ds_auto_approved', log_level=logging.INFO,
        additional_context={'profile_id': idfy_received_data.get('profile_id')})
    return "Received Video KYC data", 200

