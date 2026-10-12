import pandas as pd
from flask import Flask, jsonify, render_template

from db import get_engine

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/news")
def get_news():
    try:
        df = pd.read_sql("SELECT * FROM heatmap_data", get_engine())
        df = df.fillna("")
        return jsonify(df.to_dict(orient="records"))
    except Exception as e:
        app.logger.exception("api/news failed")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)