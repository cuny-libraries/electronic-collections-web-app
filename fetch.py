import httpx
import json
import math
import os
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pprint import pprint

load_dotenv()

apikey1 = os.getenv("NZ_API_KEY")
apikey2 = os.getenv("BIBS_NZ_API_KEY")
url1 = "https://api-na.hosted.exlibrisgroup.com/almaws/v1/electronic/e-collections?limit=100&offset={}&format=json&apikey={}"
url2 = "https://api-na.hosted.exlibrisgroup.com/almaws/v1/electronic/e-collections/{}?apikey={}&format=json"
url3 = "https://api-na.hosted.exlibrisgroup.com/almaws/v1/bibs/{}?apikey={}&format=json"


def sub_fetch(id_number):
    """get e-collection level data"""
    sub_data = httpx.get(url2.format(id_number, apikey1), timeout=500)
    sub_json = sub_data.json()
    return [
        sub_fetch_groups(sub_json),
        sub_fetch_interface(sub_json),
        sub_fetch_vendors(sub_json),
        sub_fetch_cz_ids(sub_json),
    ]


def sub_fetch_cz_ids(sub_json):
    """get cz id"""
    try:
        nz_mms_id = sub_json["resource_metadata"]["mms_id"]["value"]
        bibs_data = httpx.get(url3.format(nz_mms_id, apikey2), timeout=500)
        bibs_json = bibs_data.json()
        pprint(bibs_json)
        for number in bibs_json["network_number"]:
            if "EXLCZ" in number:
                cz_mms_id = number[7:]
                return cz_mms_id
            else:
                return sub_json["id"]
    except KeyError:
        return sub_json["id"]

def sub_fetch_groups(sub_json):
    """get groups data"""
    try:
        group_data = sub_json["group_setting"]
        groups = []
        for group in group_data:
            groups.append(group["group"]["desc"])
        return groups
    except KeyError:
        return False


def sub_fetch_interface(sub_json):
    """get interface data"""
    try:
        return sub_json["interface"]["name"]
    except KeyError:
        return False


def sub_fetch_vendors(sub_json):
    """get vendors data"""
    try:
        return sub_json["interface"]["vendor"]["value"]
    except KeyError:
        return False


def main():
    offset = 0
    data = httpx.get(url1.format(offset, apikey1), timeout=500)
    json_data = data.json()

    # calculate the number of pages of results
    pages = math.ceil(json_data["total_record_count"] / 100)

    names = []

    # paginate
    for page in range(pages):
        offset = page * 100
        page_data = httpx.get(url1.format(offset, apikey1), timeout=500)
        page_json = page_data.json()

        for x in page_json["electronic_collection"]:

            # function to run collection-level api call
            sub_return = sub_fetch(x["id"])
            names.append(
                (x["public_name"], sub_return[0], sub_return[1], sub_return[2], sub_return[3])
            )

    # sort alphabetically, case-insensitive
    sorted_names = sorted(names, key=lambda x: x[0].casefold())

    with open("static/data.json", "w") as f:
        json.dump(sorted_names, f)


if __name__ == "__main__":
    main()
