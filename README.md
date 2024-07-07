# Digilocker Document Fetching API

This Flask app provides an API endpoint to fetch documents from Digilocker. It uses IDfy credentials for authentication.

## Prerequisites

- Python installed (version X.X.X)
- Flask (`pip install flask`)
- Flasgger (`pip install flasgger`)
- dotenv (`pip install python-dotenv`)

## Configuration

Before running the application, set the following environment variables in a `.env` file:


## Installation

1. Clone the repository.
2. Install dependencies using `pip install -r requirements.txt`.
3. Set up the environment variables in a `.env` file.
4. Run the application with `python app.py`.

## Usage

API_KEY=YOUR_API_KEY
ACCOUNT_ID=YOUR_ACCOUNT_ID
KEY_ID=YOUR_KEY_ID
SECRET_KEY=YOUR_SECRET_KEY
SECRET_BASE64=YOUR_SECRET_BASE64
OU_ID=YOUR_OU_ID


### Fetching Documents

Send a POST request to `/digilocker/fetch_documents` with the following JSON payload:

```json
{
  "key_id": "YOUR_KEY_ID",
  "ou_id": "YOUR_OU_ID",
  "callback_url": "YOUR_CALLBACK_URL",
  "doc_type": "ADHAR",
  "file_format": "xml",
  "extra_fields": {
    "any_additional_field": "value"
  }
}


Here's a basic README.md template for your Flask app handling Digilocker document fetching:

markdown
Copy code
# Digilocker Document Fetching API

This Flask app provides an API endpoint to fetch documents from Digilocker. It uses IDfy credentials for authentication.

## Prerequisites

- Python installed (version X.X.X)
- Flask (`pip install flask`)
- Flasgger (`pip install flasgger`)
- dotenv (`pip install python-dotenv`)

## Configuration

Before running the application, set the following environment variables in a `.env` file:

API_KEY=YOUR_API_KEY
ACCOUNT_ID=YOUR_ACCOUNT_ID
KEY_ID=YOUR_KEY_ID
SECRET_KEY=YOUR_SECRET_KEY
SECRET_BASE64=YOUR_SECRET_BASE64
OU_ID=YOUR_OU_ID

csharp
Copy code

## Installation

1. Clone the repository.
2. Install dependencies using `pip install -r requirements.txt`.
3. Set up the environment variables in a `.env` file.
4. Run the application with `python app.py`.

## Usage

### Fetching Documents

Send a POST request to `/digilocker/fetch_documents` with the following JSON payload:

```json
{
  "key_id": "YOUR_KEY_ID",
  "ou_id": "YOUR_OU_ID",
  "callback_url": "YOUR_CALLBACK_URL",
  "doc_type": "ADHAR",
  "file_format": "xml",
  "extra_fields": {
    "any_additional_field": "value"
  }
}
This endpoint will return a redirect URL for fetching documents from Digilocker.

Callback Handling
Digilocker's callback data will be received at /digilocker/callback endpoint.
Handle the callback data accordingly within the handle_callback() function.

Documentation
The API documentation is available using Swagger UI integrated into the application. Access it at http://localhost:5000/apidocs.

Contributing
Feel free to contribute by submitting issues or pull requests.

License
This project is licensed under the [License Name] - see the LICENSE file for details.

Contact
For any questions or support, contact [Your Contact Information].


You can follow the previous steps to create a `README.md` file using a 
