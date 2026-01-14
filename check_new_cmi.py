import pandas
import json
import requests
import os
from datetime import datetime


def cmi_name(os_name):
    final = []
    for ndc in ['chicago', 'ashburn', 'hillsboro']:
        project_id = '2cc74b51-2328-4d68-b1a3-eb1b051ff5f1'
        headers = {'Content-Type': 'application/json', 'x-xca-xcloudaccount': project_id, 'Authorization': ACCESS_TOKEN}
        d = '{\"uri\":\"com.vmware.xcloud.common/getCMINamesByProject\",\"dataSource\":\"scriptAction\",\"parameters\":[{\"name\":\"showCustom\",\"value\":\"false\",\"useResultFromRequestId\":-1},{\"name\":\"projectId\",\"value\":\"' + project_id + '\",\"useResultFromRequestId\":-1}],\"requestId\":0}'
        httpresp = requests.post(
            'https://api.xcloud.comcast.com/api/catalog/v2/catalogItems/forms/render?az=az2&region=' + ndc + '&projectId=' + project_id,
            data=d, headers=headers)

        if httpresp.status_code == 200:
            cmi = json.loads(httpresp.text)
            dates = []
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
            continue
    return final


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


for x in json_data:
    cmi = cmi_name(x['OS'])
    cmi_loc = cmi[0]
    file_name = ''
    if 'Centos' in x['OS']:
        file_name = 'centos_cmi_name_latest'
    elif 'RHEL' in x['OS']:
        file_name = 'rhel_cm_name_latest'
    else:
        continue
    with open(file_name, "r+") as f:
        content = f.read()
        if content != cmi_loc:
            print('new CMI for ' + x['OS'] + ':' + cmi_loc)
            f.seek(0)
            f.write(cmi_loc)
            f.close()
        else:
            f.close()
            continue
