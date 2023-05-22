import requests
import pprint
import json

DOMAIN = 'https://api.hh.ru/'

url = f'{DOMAIN}areas/'

result = requests.get(url).json()

pprint.pprint(type(result[0]))

print(result[0]['id'])
print(result[0]['parent_id'])
print(result[0]['name'])
rus_len = len(result[0]['areas'])
for i in range(rus_len):
    print(result[0]['areas'][i]['id'] + ' : ' + result[0]['areas'][i]['name'] + ' : ' + str(len(result[0]['areas'][i]['areas'])))





