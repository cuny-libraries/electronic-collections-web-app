import json
import os
import pytz
from datetime import datetime
from flask import Flask, render_template, url_for

app = Flask(__name__)
PATH = "/home/b7jl/electronic-collections-web-app/static/data.json"


@app.route("/")
def index():
    with open(PATH, "r") as f:
        data = json.load(f)

    ctime = os.path.getctime(PATH)
    utc_time = datetime.fromtimestamp(ctime).replace(tzinfo=pytz.utc)
    tz = pytz.timezone("America/New_York")
    dt = utc_time.astimezone(tz)
    output_time = dt.strftime("%-I:%M%p (%Z)")

    count = len(data)
    return render_template("index.html", count=count, data=data, time=output_time)


@app.after_request
def add_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    resp.headers["Content-Security-Policy"] = (
        "script-src 'self'; style-src 'self'; frame-ancestors https://cuny-ols.libanswers.com; default-src 'none'"
    )
    resp.headers["Cache-Control"] = "max-age=0"
    return resp


if __name__ == "__main__":
    app.run(debug=True)
