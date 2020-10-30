from flask import Flask

app = Flask(__name__)


@app.route("/ping")
def ping():
    return "Application is running! Ping worked!"


if __name__ == "__main__":
    app.run(debug=True)
