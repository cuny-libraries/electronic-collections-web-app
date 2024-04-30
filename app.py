import json
from flask import Flask, render_template, url_for

app = Flask(__name__)

with open("/home/b7jl/electronic-collections-web-app/static/data.json", "r") as f:
    data = json.load(f)


@app.route("/")
def index():
    count = len(data)
    return render_template("index.html", count=count, data=data)


@app.after_request
def add_security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    resp.headers["Content-Security-Policy"] = (
        "script-src 'self'; style-src 'self'; frame-ancestors https://cuny-ols.libanswers.com; default-src 'none'"
    )
    return resp


if __name__ == "__main__":
    app.run(debug=True)
