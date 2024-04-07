import httpx
import json
import math
import os
from dotenv import load_dotenv
from pprint import pprint

load_dotenv()

apikey = os.getenv("NZ_API_KEY")
url1 = "https://api-na.hosted.exlibrisgroup.com/almaws/v1/electronic/e-collections?limit=100&offset={}&format=json&apikey={}"
url2 = "https://api-na.hosted.exlibrisgroup.com/almaws/v1/electronic/e-collections/{}?apikey={}&format=json"

def sub_fetch(id_number):
    sub_data = httpx.get(url2.format(id_number, apikey), timeout=500)
    sub_json = sub_data.json()
    try:
        return sub_json["activation_date"]
    except KeyError:
        print(sub_json["public_name"])
        return False

offset = 0
data = httpx.get(url1.format(offset, apikey), timeout=500)
json_data = data.json()
pages = math.ceil(json_data["total_record_count"] / 100)

names = []

for page in range(pages):
    offset = page * 100
    page_data = httpx.get(url1.format(offset, apikey), timeout=500)
    page_json = page_data.json()

    for x in page_json["electronic_collection"]:
        sub_return = sub_fetch(x["id"])
        if sub_return:
            names.append((x["public_name"], x["id"]))

sorted_names = sorted(names, key=lambda x: x[0].casefold())



with open("data.json", "w") as f:
    json.dump(sorted_names, f)
