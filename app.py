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

    # create time to be displayed
    ctime = os.path.getctime(PATH)
    utc_time = datetime.fromtimestamp(ctime).replace(tzinfo=pytz.utc)
    tz = pytz.timezone("America/New_York")
    dt = utc_time.astimezone(tz)
    output_time = dt.strftime("%-I:%M%p (%Z)")

    # swap in new library names
    for record in data:
        try:
            newschools = []
            for school in record[2]:
                if school == "Manhattan Community College":
                    newschools.append("Borough of Manhattan Community College")
                elif school == "Fiorello H LaGuardia Community College Library":
                    newschools.append("LaGuardia Community College")
                else:
                    newschools.append(school)
            record[2] = newschools
        except TypeError:
            pass

    count = len(data)  # the number of collections
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
