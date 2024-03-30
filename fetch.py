import httpx
import json
import math
import os
from dotenv import load_dotenv
from pprint import pprint

load_dotenv()

apikey = os.getenv("NZ_API_KEY")
url = "https://api-na.hosted.exlibrisgroup.com/almaws/v1/electronic/e-collections?limit=100&offset={}&format=json&apikey={}"

offset = 0
data = httpx.get(url.format(offset, apikey), timeout=500)
json_data = data.json()
pages = math.ceil(json_data["total_record_count"] / 100)

names = []

for page in range(pages):
    offset = page * 100
    page_data = httpx.get(url.format(offset, apikey), timeout=500)
    page_json = page_data.json()

    for x in page_json["electronic_collection"]:
        names.append(x["public_name"])

sorted_names = sorted(names, key=str.casefold)

with open('data.json', 'w') as f:
    json.dump(sorted_names, f)
