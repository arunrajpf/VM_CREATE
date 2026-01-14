import json, os
import pymysql
import requests


def get_device_id(fqdns):
    connection = pymysql.connect(host='10.124.133.36',
                                 user='automation',
                                 password=os.environ['sqlPasswd'],
                                 db='itrc',
                                 charset='utf8mb4',
                                 port=3306,
                                 cursorclass=pymysql.cursors.DictCursor)
    try:
        final_data = []
        for fqdn in fqdns:
            with connection.cursor() as cursor:
                sql = str("SELECT id from itrc.devices where fqdn = '" + fqdn + "';")
                cursor.execute(sql)
            data = cursor.fetchall()

            if str(data) != '()':
                final_data.append(data[0])
            else:
                print('Device "' + fqdn + '" does not exist!')
            connection.commit()
    finally:
        connection.close()
    return final_data



def get_device_tags(id):
    resp = requests.get(url + 'devices/' + str(id) + '/assignments', headers=headers)
    if resp.status_code != 200:
        print('(ERROR: ' + str(resp.status_code) + ')' + ' Failed to retrieve devices from app: ' + str(id) + '!')

    resp = resp.json()
    final = []
    for x in resp['data']:
        final.append(x['id'])
    return final



url = 'https://api.itrc.comcast.net/api/v3/'
headers = {'Content-Type': 'application/vnd.api+json', 'Accept': 'application/vnd.api+json'}
file = open("fqdn.txt","r")
fqdns = file.readlines()
file.close()
dev_ids = get_device_id(fqdns)

resp = requests.post(
    "https://websec.cable.comcast.com/as/token.oauth2?grant_type=client_credentials&client_id=" + "itrc_bsd_data_fetcher" + "&client_secret=" +
    os.environ['authToken1'] + "&scope=itrc:user")
json_data = json.loads(resp.text)
token = "bearer " + json_data['access_token']
headers['Authorization'] = token

for dev_id in dev_ids:
    tags = get_device_tags(dev_id)
    for tag in tags:
        httpresp = requests.delete(url + 'device-assignments/' + str(id), headers=headers)
        if httpresp.status_code != 200:
            print(str(httpresp.status_code) + ": " + httpresp.text)
        else:
            print("Assignment removed from device: " + str(dev_id))
