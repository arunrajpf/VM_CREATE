import pandas
import json
import requests
import os
import pymysql
from datetime import datetime
from time import sleep

role_id=os.environ['role_id']
secret_id=os.environ['secret_id']

headers_ccp = {'Content-Type': 'application/json', 'Accept': 'application/vnd.api+json'}

data = {"role_id":role_id,"secret_id":secret_id}
resp = requests.post("https://or.vault.comcast.com/v1/auth/approle/login",data=data)

json_data = json.loads(resp.text)
token = json_data['auth']['client_token']
headers_vault = {"X-Vault-Token": token}
AZURE_CLIENT_ID = os.environ['client_id']
AZURE_TENANT_ID = os.environ['tenant_id']
SCOPE = "api://xcloud/.default"
account_id = ''
account_name = ''

def get_token():
    token_url = "https://login.microsoftonline.com/" + AZURE_TENANT_ID + "/oauth2/v2.0/token"
    print(body)
    print(token_url)
    resp = requests.post(url=token_url, data=body)
    print(resp)
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
    connection = pymysql.connect(host='10.142.93.2',
                                    user='automation',
                                    password=os.environ['sqlPasswd'],
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

def cmi_name(os_name, az, dc, acct):
    final = []
    # project_id = account_id
    if dc == 'as':
        ndc = 'ashburn'
    elif dc == 'ho':
        ndc = 'hillsboro'
    elif dc == 'ch':
        ndc = 'chicago'
    project_id = get_project(acct, az, ndc)
    headers = {'Content-Type': 'application/json', 'x-xca-xcloudaccount': acct, 'Authorization': get_token()}
    d = '{\"uri\":\"com.vmware.xcloud.common/getCMINamesByProject\",\"dataSource\":\"scriptAction\",\"parameters\":[{\"name\":\"showCustom\",\"value\":\"false\",\"useResultFromRequestId\":-1},{\"name\":\"projectId\",\"value\":\"' + project_id + '\",\"useResultFromRequestId\":-1}],\"requestId\":0}'
    httpresp = requests.post('https://api.xcloud.comcast.com/api/catalog/v2/catalogItems/forms/render?az=az' + str(
        az) + '&region=' + ndc + '&projectId=' + project_id, data=d, headers=headers)
    print(httpresp.text)
    sleep(8) #this was 10
    if httpresp.status_code == 200:
        cmi = json.loads(httpresp.text)
        dates = []
        print(cmi)
        if 'data' not in cmi:
            print("Data response is blank while fetching Catalog items from api.xcloud")
            exit(-1)
        for z in cmi['data']:
            if 'Centos' in os_name:
                if 'Comcast-CentOS-7-' in z:
                    dates.append(z)
            if 'RHEL 7' in os_name:
                if 'Comcast-RHEL-7-' in z:
                    dates.append(z)
            if 'RHEL 8' in os_name:
                if 'Comcast-RHEL-8-' in z:
                    dates.append(z)
            if 'Rocky 8' in os_name:
                if 'Comcast-Rocky-8-' in z:
                    dates.append(z)
        if not dates:
            print('failed to retrieve cmi dates for ' + ndc)
            exit(-1)
        max_date = ''
        time_stamp = ''
        for date in dates:
            time_stamp = {'date': date, 'ts': date.split('-')[3]}
            if max_date == '':
                max_date = time_stamp
                max_date_dt_obj = datetime.strptime(time_stamp['ts'], '%Y%m%d')
            else:
                time_stamp_dt_obj = datetime.strptime(time_stamp['ts'], '%Y%m%d')
                if time_stamp_dt_obj > max_date_dt_obj:
                    max_date = time_stamp
                    max_date_dt_obj = datetime.strptime(time_stamp['ts'], '%Y%m%d')
        final.append(time_stamp['date'])
        return final
    else:
        print('failed to retrieve cmi name for ' + ndc)
    return final


excel_data_fragment = pandas.read_excel('ccp_create_server_list.xlsx', sheet_name='Input')
json_data = json.loads(excel_data_fragment.to_json(orient='records'))

# where env ids and scope were previously placed

hosts = open('hosts.host', "w")
hosts.write('[All]\n')
ret = os.system('terraform init')
envs = ['production', 'dr', 'development', 'qa', 'staging', 'integration', 'pre-prod', 'training', 'mit', 'ci']
for x in json_data:
    if x['Envt'] not in envs:
        print('Invalid environment name: ' + x['Envt'])
        continue
    account_id = x['CCP Account Id']
    account_name = x['CCP Account name']
    account_secret = get_client_secret(account_name)
    body = {'grant_type': 'client_credentials', 'client_id': AZURE_CLIENT_ID, 'client_secret': account_secret, 'scope': SCOPE}
    az = x['AZ'].lower()
    zone_num = az[-1]
    cmi = cmi_name(x['OS'], zone_num, x['DC'], account_id)
    if x['vCPU'] == 1:
        if (x['Memory in GB'] != 1 and x['Memory in GB'] != 2 and x['Memory in GB'] != 2):
            print('Misconguration in CPU or Memory for host: ' + x['Hostname'])
            continue
    if x['vCPU'] == 2:
        if (x['Memory in GB'] != 4 and x['Memory in GB'] != 8 and x['Memory in GB'] != 16):
            print('Misconguration in CPU or Memory for host: ' + x['Hostname'])
            continue
    if x['vCPU'] == 4:
        if (x['Memory in GB'] != 8 and x['Memory in GB'] != 16 and x['Memory in GB'] != 32 and x['Memory in GB'] != 64):
            print('Misconguration in CPU or Memory for host: ' + x['Hostname'])
            continue
    if x['vCPU'] == 8:
        if (x['Memory in GB'] != 16 and x['Memory in GB'] != 32 and x['Memory in GB'] != 64):
            print('Misconguration in CPU or Memory for host: ' + x['Hostname'])
            continue
    if x['vCPU'] == 16:
        if (x['Memory in GB'] != 32 and x['Memory in GB'] != 64 and x['Memory in GB'] != 128):
            print('Misconguration in CPU or Memory for host: ' + x['Hostname'])
            continue
    if x['vCPU'] == 32:
        if (x['Memory in GB'] != 128 and x['Memory in GB'] != 256):
            print('Misconguration in CPU or Memory for host: ' + x['Hostname'])
            continue
    f = open(x['Hostname'] + ".tfvars", "w")
    f.write('access_token = "' + get_token() + '"\n')
    cmi_loc = cmi[0]

    if x['DC'] == 'as':
        f.write(
            'url = "https://api.xcloud.comcast.com/api/terraformassist/v1/vRA/ashburn/' + az + '/' + account_id + '"\n')
    elif x['DC'] == 'ho':
        f.write(
            'url = "https://api.xcloud.comcast.com/api/terraformassist/v1/vRA/hillsboro/' + az + '/' + account_id + '"\n')
    elif x['DC'] == 'ch' or x['DC'] == 'ch2':
        f.write(
            'url = "https://api.xcloud.comcast.com/api/terraformassist/v1/vRA/chicago/' + az + '/' + account_id + '"\n')
    f.write('insecure = "false"\n')
    f.write('project = "' + account_name + '-' + account_id + '"\n')
    now = datetime.now()
    current_time = now.strftime("%Y%m%d%H%M%S")
    f.write('deployment_name = "' + account_name + '-' + current_time + '"\n')
    f.write('catalog_item_name = "Linux with Extra Disk"\n')
    f.write('instance_count = 1\n')
    f.write('vmname = "' + x['Hostname'] + '"\n')
    f.write('flavor = "CC.' + str(x['vCPU']) + 'cpu-' + str(x['Memory in GB']) + 'GB"\n')
    f.write('tenant = "' + x['TSF'] + '"\n')
    f.write('rail = "' + x['Rail'] + '"\n')
    f.write(
        'tags = "itrc_application:' + str(x['itrc_application_id']) + ',itrc_environment:' + x['Envt'] + ',itrc_tier:' +
        x['Tier'] + ', dns:' + 'true' + ',cada_hostgroup:' + 'BSD_CORE_HG_' + str(
            x['itrc_application_id']) + '"\n')
    f.write('cmi = "' + cmi_loc + '"\n')
    f.write('''ipv = "IPv4_IPv6"
deployment_count = 1
''')
    f.write('bootcapacity = ' + str(x['Boot Capacity in GB']) + '\n')
    f.write('extracapacity = ' + str(x['Additional disk  in GB']) + '\n')
    f.write(
        'description = "Deploy new server ' + x['Hostname'] + ' for ' + str(x['itrc_application_id']) + ' in the ' + x[
            'Envt'] + ' environment."\n')
    f.write('''cloud_init = <<-EOF
#cloud-config
runcmd:
''')
    if 'rhel' in x['OS'].lower():
        f.write('- echo bsdcore-xcloud.bsdcore-poc.bsdcorepoc > /etc/ssh/authorized_principals/cloud-user\n')
        f.write('- chage -M -1 cloud-user\n')
        os.environ["ansibleuser"] = "cloud-user"
    elif 'centos' in x['OS'].lower():
        f.write('- echo bsdcore-xcloud.bsdcore-poc.bsdcorepoc > /etc/ssh/authorized_principals/centos\n')
        f.write('- chage -M -1 centos\n')
        os.environ["ansibleuser"] = "centos"
    else:
        f.write('- echo bsdcore-xcloud.bsdcore-poc.bsdcorepoc > /etc/ssh/authorized_principals/rocky\n')
        f.write('- chage -M -1 rockey\n')
        os.environ["ansibleuser"] = "rocky"        
    f.write('''EOF
tocreate = "180m"
todelete = "180m"
''')
    f.close()
    ret = os.system('terraform apply -auto-approve -var-file=' + x['Hostname'] + '.tfvars')
    os.rename('terraform.tfstate', x['Hostname'] + '.tfstate')
    tfstate = open(x['Hostname'] + ".tfstate", "r")
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
    elif 'Rocky' in x['OS']:
        hosts.write(' ansible_user=rocky\n')
    else:
        hosts.write(' ansible_user=centos\n')

print("End of script")
