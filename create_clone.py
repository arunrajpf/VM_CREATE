import requests
import json
import pandas as pd
import os
import pymysql
from time import sleep
import subprocess
from datetime import datetime
import sys
import random
import re


AZURE_TENANT_ID = "906aefe9-76a7-4f65-b82d-5ec20775d5aa"
SCOPE = "api://xcloud/.default"


role_id=""
secret_id=""

headers_ccp = {'Content-Type': 'application/json', 'Accept': 'application/vnd.api+json'}

data = {"role_id":role_id,"secret_id":secret_id}
resp = requests.post("https://or.vault.comcast.com/v1/auth/approle/login",data=data)

json_data = json.loads(resp.text)
token = json_data['auth']['client_token']
headers_vault = {"X-Vault-Token": token}

SCOPE = "api://xcloud/.default"
account_id = ''
account_name = ''


def get_client_id(acc):
    connection = pymysql.connect(host='10.124.133.36',
                                    user='automation',
                                    password="autom@tprd",
                                    db='ccp',
                                    charset='utf8mb4',
                                    port=3306,
                                    cursorclass=pymysql.cursors.DictCursor)
    try:
        with connection.cursor() as cursor:
            sql = str("SELECT AZURE_CLIENT_ID from ccp.account WHERE account_name='" + acc + "'")
            cursor.execute(sql)
            client_id = cursor.fetchone()
            if not client_id:
                print("client_id not found in database for the account:", account_name)
                return None
            AZURE_CLIENT_ID = client_id['AZURE_CLIENT_ID']
            return AZURE_CLIENT_ID
    finally:
        connection.close()

def get_account_id(acc):
    connection = pymysql.connect(host='10.124.133.36',
                                    user='automation',
                                    password="autom@tprd",
                                    db='ccp',
                                    charset='utf8mb4',
                                    port=3306,
                                    cursorclass=pymysql.cursors.DictCursor)
    try:
        with connection.cursor() as cursor:
            sql = str("SELECT account_id from ccp.account WHERE account_name='" + acc + "'")
            cursor.execute(sql)
            account_id = cursor.fetchone()
            if not account_id:
                print("account_id not found in database for the account:", account_name)
                return None
            account_id = account_id['account_id']
            return account_id
    finally:
        connection.close()


def get_token():
    token_url = "https://login.microsoftonline.com/" + AZURE_TENANT_ID + "/oauth2/v2.0/token"
    resp = requests.post(url=token_url, data=body)
    cred = json.loads(resp.text)['access_token']
    return cred


def get_project(acct, zone, region):
    # zone= 1 , region = 'chicago'
    headers = {'accept': 'application/json', 'x-xca-xcloudaccount': acct, 'Authorization': get_token()}
    baseUrl = "https://api.xcloud.comcast.com/api/account/v1/account/projectid?accountId="
    fullUrl = baseUrl + "{0}&az=az{1}&region={2}".format(acct, zone, region)
    result = requests.get(url=fullUrl, headers=headers)
    print(result.text)
    project = json.loads(result.text)
    project = project['projectId']
    print("Project Id for acctID {0} zone: {1} region: {2} is : {3}".format(acct, zone, region, project))
    return project

def get_client_secret(acc):
    connection = pymysql.connect(host='10.124.133.36',
                                    user='automation',
                                    password="autom@tprd",
                                    db='ccp',
                                    charset='utf8mb4',
                                    port=3306,
                                    cursorclass=pymysql.cursors.DictCursor)
    try:
        with connection.cursor() as cursor:
            sql = str("SELECT AZURE_CLIENT_SECRET_PATH_KV2 from ccp.account WHERE account_name='" + acc + "'")
            cursor.execute(sql)
            secret_path = cursor.fetchone()
            if not secret_path:
                print("Secret path not found for account:", account_name)
                return None
            AZURE_CLIENT_SECRET_PATH = secret_path['AZURE_CLIENT_SECRET_PATH_KV2']
            resp = requests.get('https://or.vault.comcast.com/v1/kv2/data/' +  AZURE_CLIENT_SECRET_PATH, headers=headers_vault)
            json_resp = json.loads(resp.text)
            AZURE_CLIENT_SECRET = json_resp['data']['data']['ccp_token']
            if resp.status_code != 200:
                if 'error performing token check: failed to persist lease entry: cannot write to readonly storage' in resp.text:
                    print(
                        'error performing token check: failed to persist lease entry: cannot write to readonly storage')
                    print('sleeping for 5 minutes')
                    time.sleep(300)
                    resp = requests.get('https://or.vault.comcast.com/v1/kv2/data/' +  AZURE_CLIENT_SECRET_PATH, headers=headers_vault)
                    json_data = json.loads(resp.text)
                    AZURE_CLIENT_SECRET = json_data['data']['data']['ccp_token']
                else:
                    print(resp)
            return AZURE_CLIENT_SECRET
    finally:
        connection.close()

# read excel input
excel_data_fragment = pd.read_excel('ccp_create_server_list.xlsx', sheet_name='Input')
json_data = json.loads(excel_data_fragment.to_json(orient='records'))


# list of hostnames$

with open('hostnames.txt', 'r') as file:
    hostnames = [line.strip() for line in file if line.strip().endswith('.net')]
print(hostnames)
# select a random host
current_host = random.choice(hostnames)
mirror_host = current_host.split('.')[0]
print(f'Host to mirror: {mirror_host}')

# extract the numbers from the hostnames

# extract the numbers and the following letters from the hostnames and store them with their respective hostnames
hostname_number_pairs = []
for hostname in hostnames:
    match = re.search(r'a(\d+)([sdqiutp])', hostname)  # adjusted to capture any of the specified letters
    if match:
        number = int(match.group(1))
        letter = match.group(2)
        hostname_number_pairs.append((hostname, number, letter))

# if there are numbers in the hostnames
if hostname_number_pairs:
    # find the highest number
    max_pair = max(hostname_number_pairs, key=lambda pair: pair[1])
    max_number = max_pair[1]
    max_letter = max_pair[2]

    # generate the next hostname based on the hostname with the highest number
    max_hostname = max_pair[0]
    next_number = max_number + 1
    next_hostname = max_hostname.replace('a'+str(max_number)+max_letter, 'a'+str(next_number)+max_letter)
    server_name = next_hostname.split('.')[0]
    print(f'server to create: {server_name}')
else:
    print("Could not generate a hostname based on the patern.")


#ret = os.system('terraform init')
for x in json_data:
    f = open(str(server_name) + ".tfvars", "w")
    account_name = x['CCP Account name']
    account_id = get_account_id(account_name)
    account_secret = get_client_secret(account_name)
    az = x['AZ'].lower()
    body = {'grant_type': 'client_credentials', 'client_id': get_client_id(account_name), 'client_secret': account_secret, 'scope': SCOPE}
    f.write('access_token = "' + get_token() + '"\n')
    if x['DC'] == 'as':
        DC = "ashburn"
        f.write(
            'url = "https://api.xcloud.comcast.com/api/terraformassist/v1/vRA/ashburn/' + az + '/' + account_id + '"\n')
    elif x['DC'] == 'ho':
        DC = "hillsboro"
        f.write(
            'url = "https://api.xcloud.comcast.com/api/terraformassist/v1/vRA/hillsboro/' + az + '/' + account_id + '"\n')
    elif x['DC'] == 'ch' or x['DC'] == 'ch2':
        DC = "chicago"
        f.write(
            'url = "https://api.xcloud.comcast.com/api/terraformassist/v1/vRA/chicago/' + az + '/' + account_id + '"\n')
    zone_num = az[-1]
    f.write('project = "' + account_name + '-' + account_id + '"\n')
    # get the VM specific details by connecting to CCP CLI
    ccp_login = ("xcloud", "login",  "-t", get_token())
    result = subprocess.run(ccp_login, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    dep_list = ("xcloud", "deployment", "list-deployments", az , DC , account_id)
    dep_result = subprocess.run(dep_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    dep_json = json.loads(dep_result.stdout)
    if dep_result.returncode == 0:
        dep_json = json.loads(dep_result.stdout)
        filtered_data = [
            {
                'id': item['id'],
                'name': item['name'],
                'description': item['description'],
                'inputs': item['inputs']
            }
        for item in dep_json['content']
        if item['inputs'].get('vmName') == mirror_host
        ]
        result = json.dumps(filtered_data, indent=2)
        print("result")
        print(result)


    result_json = json.loads(result)
    f.write('deployement = "' + result_json[0]['name']+ '"\n')
#    f.write('catalog_item_name = "' + result_json[0]['inputs']['inCMI']+ '"\n')
#    f.write('catalog_item_name = "' + result_json[0]['inputs']['_catalogItemName'] + '"\n')
    f.write('catalog_item_name = "Linux with Extra Disk"\n')
    f.write('vmname = "' + server_name+ '"\n')
    f.write('flavor = "' + result_json[0]['inputs']['inFlavor']+ '"\n')
    f.write('rail = "' + result_json[0]['inputs']['inRail'] + '"\n')
#    f.write('cmi = "' + result_json[0]['inputs']['inCMI'] + '"\n')
    f.write('cmi = "' + x['CMI'] + '"\n')
    f.write('ipv = "' + result_json[0]['inputs']['inIpv'] + '"\n')
    tags = (result_json[0]['inputs']['inTags'])
    # split the string into a list of tags
    tags_list = tags.split(',')
    # use list comprehension to filter out unwanted tags
    filtered_tags_list = [tag for tag in tags_list if not tag.startswith(('comcastapplicationenvironment:', 'comcastiopapplicationid:'))]
    # join the list back into a string
    filtered_tags = ','.join(filtered_tags_list)
    f.write('tags = "' + ','.join(filtered_tags_list) + '"\n')
    f.write('bootcapacity = "' + str(result_json[0]['inputs']['inBootCapacity']) + '"\n')
    f.write('extracapacity = "' + str(result_json[0]['inputs']['inSize']) + '"\n')
    f.write('description = "' + result_json[0]['description'] + '"\n')
    now = datetime.now()
    current_time = now.strftime("%Y%m%d%H%M%S")
    f.write('deployment_name = "' + account_name + '-' + current_time + '"\n')
    f.write('insecure = "false"\n')
    f.write('tenant = "'+ result_json[0]['inputs']['inTenant'] + '"\n')
    f.write('deployment_count = "1"\n')
    f.write('instance_count = "1"\n')
    f.write('''cloud_init = <<-EOF''' + '\n')
    f.write( result_json[0]['inputs']['inConfig'] + '\n')
    f.write('''EOF
tocreate = "180m"
todelete = "180m"
''')
    f.close()
#    ret = os.system('terraform apply -auto-approve -var-file=' + server_name + '.tfvars')
#    os.rename('terraform.tfstate', server_name + '.tfstate')
    tfstate = open(str(server_name) + ".tfstate", "r")
    content = tfstate.read()
    y = json.loads(content)
    host_ip = y['outputs']['vm_name_with_ip']['value'][str(y['outputs']['vm_name_with_ip']['value']).split("'")[1]]
    if 'g' in str(x['swap']):
        swap = str(x['swap'])
    else:
        swap = str(x['swap']) + 'g'
    if x['Tier'].lower() == 'app' or x['Tier'].lower() == 'web':
        hosts.write(
            host_ip + ' swap_size=' + swap + ' filesystem_name=app hostname=' + x['Hostname'] + '.sys.comcast.net')
    if x['Tier'].lower() == 'db':
        hosts.write(
            host_ip + ' swap_size=' + swap + ' filesystem_name=db hostname=' + x['Hostname'] + '.sys.comcast.net')
    if x['nas_path'] != 'NA' and x['nas_path'] != '' and x['nas_path'] is not None:
        hosts.write(' ' + x['nas_path'])
    if 'RHEL' in x['OS']:
        hosts.write(' ansible_user=cloud-user\n')
    else:
        hosts.write(' ansible_user=centos\n')

print("End of script")
