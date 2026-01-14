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
AZURE_TENANT_ID = os.environ['tenant_id']
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
    baseUrl = "https://api.xcloud.comcast.com/api/account/v1/account/projectid?accountId="
    fullUrl = baseUrl + "{0}&az=az{1}&region={2}".format(acct, zone, region)
    result = requests.get(url=fullUrl, headers=headers)
    project = json.loads(result.text)
    project = project['projectId']
    print("Project Id for acctID {0} zone: {1} region: {2} is : {3}".format(acct, zone, region, project))
    return project


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
            if 'RHEL' in os_name:
                if 'Comcast-RHEL-7-' in z:
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

# ccp_acount_id = os.environ['ccp_account_id']
# body used to be here
# resp = requests.post("https://login.microsoftonline.com/" + AZURE_TENANT_ID + "/oauth2/v2.0/token", data=body)
# ACCESS_TOKEN = json.loads(resp.text)['access_token']
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
        x['Tier'] + ',comcastapplicationenvironment:' + x['Envt'] + ',comcastiopapplicationid:' + str(
            x['IOP App ID']) + ',dns:' + 'true' + ',cada_hostgroup:' + 'BSD_CORE_HG_' + str(
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
        os.environ["ansibleuser"] = "cloud-user"
    else:
        f.write('- echo bsdcore-xcloud.bsdcore-poc.bsdcorepoc > /etc/ssh/authorized_principals/centos\n')
        f.write('- chage -M -1 centos\n')
        os.environ["ansibleuser"] = "centos"
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
    else:
        hosts.write(' ansible_user=centos\n')

print("End of script")