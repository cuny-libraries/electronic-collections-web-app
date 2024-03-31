import json
from flask import Flask, render_template

app = Flask(__name__)

with open("data.json", "r") as f:
    data = json.load(f)


@app.route("/")
def index():
    count = len(data)
    return render_template("index.html", count=count, data=data)


if __name__ == "__main__":
    app.run(debug=True)
