import httpx
import os
from dotenv import load_dotenv
from pprint import pprint

load_dotenv()

ELEC_COLLECTIONS = "https://api-na.hosted.exlibrisgroup.com/almaws/v1/electronic/e-collections?limit=100&offset=0&format=json&apikey="
url = ELEC_COLLECTIONS + os.getenv("NZ_API_KEY")

data = httpx.get(url, timeout=500)
pprint(data)
