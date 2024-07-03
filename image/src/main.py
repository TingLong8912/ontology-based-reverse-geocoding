from flask import Flask, request, jsonify
from flask_cors import CORS
from flask import send_from_directory

app = Flask(__name__)
CORS(app)

@app.route('/api', methods=['GET'])
def api():
    return "Hello, world"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
    pass

if __name__ == '__main__':
    app.run(debug=True)
