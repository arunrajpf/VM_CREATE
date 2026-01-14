import pandas
import json
import requests
import os
from datetime import datetime



excel_data_fragment = pandas.read_excel('ccp_create_server_list.xlsx', sheet_name='Input')
json_data = json.loads(excel_data_fragment.to_json(orient='records'))

AZURE_CLIENT_ID = os.environ['client_id']
AZURE_CLIENT_SECRET = os.environ['client_secret']
AZURE_TENANT_ID = os.environ['tenant_id']

SCOPE = "api://xcloud/.default"
# ccp_acount_id = os.environ['ccp_account_id']


body = {'grant_type': 'client_credentials', 'client_id': AZURE_CLIENT_ID, 'client_secret': AZURE_CLIENT_SECRET,
        'scope': SCOPE}
resp = requests.post("https://login.microsoftonline.com/" + AZURE_TENANT_ID + "/oauth2/v2.0/token", data=body)
ACCESS_TOKEN = json.loads(resp.text)['access_token']

hosts = open('hosts.host', "w")
hosts.write('[All]\n')

for x in json_data:
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
    f.write('access_token = "' + ACCESS_TOKEN + '"\n')
    cmi_loc = ''
    if x['DC'] == 'as':
         f.write(
            'url = "https://api.xcloud.comcast.com/api/terraformassist/v1/vRA/ashburn/az2/e1b5ee09-dce1-4b7f-96fc-733350102960"\n')
    elif x['DC'] == 'ho':
        f.write(
            'url = "https://api.xcloud.comcast.com/api/terraformassist/v1/vRA/hillsboro/az2/e1b5ee09-dce1-4b7f-96fc-733350102960"\n')
    elif x['DC'] == 'ch' or x['DC'] == 'ch2':
        f.write(
            'url = "https://api.xcloud.comcast.com/api/terraformassist/v1/vRA/chicago/az2/e1b5ee09-dce1-4b7f-96fc-733350102960"\n')
    f.write('''insecure = "false"
project = "BSD-Ops-non-prod-e1b5ee09-dce1-4b7f-96fc-733350102960"\n''')
    now = datetime.now()
    current_time = now.strftime("%Y%m%d%H%M%S")
    f.write('deployment_name = "BSD-Ops-non-prod-' + current_time + '"\n')
    f.write('catalog_item_name = "R1 Machine with Extra disk Standard Image"\n')
    f.write('instance_count = 1\n')
    f.write('vmname = "' + x['Hostname'] + '"\n')
    f.write('flavor = "CC.' + str(x['vCPU']) + 'cpu-' + str(x['Memory in GB']) + 'GB"\n')
    f.write('tenant = "' + x['TSF'] + '"\n')
    f.write('rail = "' + x['Rail'] + '"\n')
    f.write('tags = "itrc_application:' + str(x['itrc_application_id']) + ',itrc_environment:' + x['Envt'] + ',itrc_tier:' + x['Tier'] + ',comcastapplicationenvironment:' + x['Envt'] + ',comcastiopapplicationid:' + str(x['IOP App ID']) + ',dns:' + 'true' + ',cada_hostgroup:' + 'BSD_CORE_HG_' + str(x['itrc_application_id']) + '"\n')
    f.write('''cmi = "Comcast-CentOS-7-20210910"
ipv = "IPv4_IPv6"
deployment_count = 1
bootcapacity = 1000
''')
    f.write('extracapacity = ' + str(x['Space in GB']) + '\n')
    f.write('description = "Deploy new server ' + x['Hostname'] + ' for ' + str(x['itrc_application_id']) + ' in the ' + x['Envt'] + ' environment."\n')
    f.write('''cloud_init = <<-EOF
#cloud-config
runcmd:
''')
    if 'RHEL' in x['OS']:
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
    print(x['Hostname'])
    ret = os.system('/usr/bin/terraform init')
    ret = os.system('/usr/bin/terraform apply -auto-approve -var-file=' + x['Hostname'] + '.tfvars')
    print(ret)
    os.rename('terraform.tfstate', x['Hostname'] + '.tfstate')
    tfstate = open(x['Hostname'] + ".tfstate", "r")
    content = tfstate.read()
    y = json.loads(content)
    host_ip = y['outputs']['vm_name_with_ip']['value'][str(y['outputs']['vm_name_with_ip']['value']).split("'")[1]]
    if 'g' in str(x['swap']):
        swap = str(x['swap'])
    else:
        swap = str(x['swap']) + 'g'
    if x['Tier'] == 'app' or x['Tier'] == 'web':
        hosts.write(host_ip + ' swap_size=' + swap + ' filesystem_name=app hostname=' + x['Hostname'] + '.sys.comcast.net')
    if x['Tier'] == 'db':
        hosts.write(host_ip + ' swap_size=' + swap + ' filesystem_name=db hostname=' + x['Hostname'] + '.sys.comcast.net')
    if x['nas_path'] != 'NA' and x['nas_path'] != '' and x['nas_path'] is not None:
        hosts.write(' ' + x['nas_path'])
    if 'RHEL' in x['OS']:
        hosts.write(' ansible_user=cloud-user\n')
    else:
        hosts.write(' ansible_user=centos\n')
