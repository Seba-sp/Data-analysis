import functions_framework
from flask import Request, jsonify

@functions_framework.http
def webhook_handler(request: Request):
    return jsonify({"message": "Hello World"}), 200
