import pandas
import json
import requests
import os
from datetime import datetime
from time import sleep

account_id = ''
account_name = ''
AZURE_CLIENT_ID = os.environ['client_id']
AZURE_CLIENT_SECRET = os.environ['client_secret']
#AZURE_TENANT_ID = os.environ['tenant_id']
SCOPE = "api://xcloud/.default"
body = {'grant_type': 'client_credentials', 'client_id': AZURE_CLIENT_ID, 'client_secret': AZURE_CLIENT_SECRET,
        'scope': SCOPE}


def get_token():
    token_url = "https://login.microsoftonline.com/" + AZURE_TENANT_ID + "/oauth2/v2.0/token"
    resp = requests.post(url=token_url, data=body)
    cred = json.loads(resp.text)['access_token']
    return cred


def get_project(acct, zone, region):
    # zone= 1 , region = 'chicago'
    headers = {'accept': 'application/json', 'x-xca-xcloudaccount': acct, 'Authorization': get_token()}
    baseUrl = "https://api.xcloud.comcast.com/api/compute/v2/swagger-ui/#/compute-controller"
    fullUrl = baseUrl + "/createComputeThroughBluePrintUsingPOST"
    result = requests.get(url=fullUrl, headers=headers)
