import json
from quart import Quart, render_template

app = Quart(__name__)

with open("data.json", "r") as f:
   data = json.load(f)

@app.route("/")
async def index():
    count = len(data)
    return await render_template("index.html", value=count)

if __name__ == "__main__":
    app.run(debug=True)
