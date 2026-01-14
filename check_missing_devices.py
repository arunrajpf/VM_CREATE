import json, os
import requests
import subprocess

cada_pass = os.environ['cada_pass']
itrc_pass = os.environ['itrc_pass']


def device_missing_from_itrc(fqdns):
    url = 'https://api.itrc.comcast.net/api/v3/'
    headers = {'Content-Type': 'application/json', 'Accept': 'application/vnd.api+json'}
    resp = requests.post(
        "https://websec.cable.comcast.com/as/token.oauth2?grant_type=client_credentials&client_id=" + "itrc_bsd_data_fetcher" + "&client_secret=" +
        itrc_pass + "&scope=itrc:user")
    json_data = json.loads(resp.text)
    token = "bearer " + json_data['access_token']
    headers['authorization'] = token

    final_data = []
    for fqdn in fqdns:
        resp = requests.get(url + 'devices?filter[fqdn]=' + fqdn, headers=headers)
        if resp.status_code == 403:
            while resp.status_code == 403:
                sleep(60)
                resp = requests.get(url + 'devices?filter[fqdn]=' + fqdn, headers=headers)
        if json.loads(resp.text)['meta']['record-count'] == 0:
            final_data.append(fqdn)
    return final_data


def device_missing_from_cada(fqdns):
    headers = {'Content-Type': 'application/json', 'Accept': 'application/vnd.api+json'}
    resp = requests.post(
        "https://websec.cable.comcast.com/as/token.oauth2?grant_type=client_credentials&client_id=" + "bsd_cada_api" + "&client_secret=" +
        cada_pass + "&scope=cada:viewhost")
    json_data = json.loads(resp.text)
    token = "bearer " + json_data['access_token']
    headers['authorization'] = token

    final_data = []
    for fqdn in fqdns:
        resp = requests.get('https://cada.comcast.net/api/v2/host/' + fqdn,
                            headers=headers)
        if 'Successfully queried CADA host' not in resp.text:
            final_data.append(fqdn)
    return final_data


def device_missing_from_dns(fqdns):
    final_data = []
    for x in fqdns:
        process = subprocess.Popen(["nslookup", x], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False)
        output = str(process.communicate()[0]).split('\\r\\n')
        for data in output:
            if 'can\'t find' in str(data):
                final_data.append(x)
                break

    return final_data


fqdns = []
file = open("hosts.host", "r")
lines = file.readlines()
for line in lines:
    if 'ccp_hostname=' in line:
        fqdns.append(line.split('ccp_hostname=')[1].rstrip())
file.close()
success = fqdns
fail = []
itrc = device_missing_from_itrc(fqdns)
if itrc:
    print("devices missing from itrc:")
    for x in itrc:
        if x in success:
            success.remove(x)
            fail.append(x)
        print(x)

cada = device_missing_from_cada(fqdns)
if cada:
    print("devices missing from cada:")
    for x in cada:
        if x in success:
            success.remove(x)
            fail.append(x)
        print(x)

dns = device_missing_from_dns(fqdns)
if dns:
    print("devices missing from dns:")
    for x in dns:
        if x in success:
            success.remove(x)
            fail.append(x)
        print(x)
        
f=open('validated', 'w')
f.writelines("%s\n" % i for i in success)
f.close()

f=open('failed', 'w')
f.writelines("%s\n" % i for i in fail)
f.close()
