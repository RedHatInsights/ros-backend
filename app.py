from flask import Flask
from flask_cors import CORS
app = Flask(__name__)
CORS(app)


@app.route('/ping')
def ping():
  """Ping API to check application status."""
  return 'Application is running! Ping worked!'

if __name__ == "__main__":
    app.run(debug=True)
