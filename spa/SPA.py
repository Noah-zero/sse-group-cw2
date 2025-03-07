from flask import Flask, render_template, request, jsonify, Response
import requests
import os
import random
from dotenv import load_dotenv

app = Flask(__name__)

load_dotenv()
AUTH_SERVICE_URL = os.environ.get("AUTH_SERVICE_URL", "http://127.0.0.1:5000")
# AUTH_SERVICE_URL = "https://gyya-sse2-users-service.impaas.uk/"
# CHAT_SERVICE_URL1 = "http://127.0.0.1:5002"
# CHAT_SERVICE_URL2 = "http://127.0.0.1:5002"
CHAT_SERVICE_URL1 = os.environ.get("CHAT_SERVICE_URL1", "http://127.0.0.1:5002") 
CHAT_SERVICE_URL2 = os.environ.get("CHAT_SERVICE_URL2", "http://127.0.0.1:5002") 
lt = [CHAT_SERVICE_URL1, CHAT_SERVICE_URL2]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def health():
    CHAT_SERVICE_URL = random.choice(lt)
    try:
        response = requests.get(f"{CHAT_SERVICE_URL}/health")
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        return (
            jsonify({"error": "Authentication service unreachable", "details": str(e)}),
            500,
        )
    except requests.exceptions.JSONDecodeError:
        return (
            jsonify({"error": "Invalid JSON response from authentication service"}),
            500,
        )
    except Exception as e:
        return jsonify({"error": "Unexpected error", "details": str(e)}), 500


@app.route("/api/login", methods=["POST"])
def login():
    """Proxy user login request to the authentication service"""
    try:
        data = request.json
        response = requests.post(f"{AUTH_SERVICE_URL}/login", json=data)
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        return (
            jsonify({"error": "Authentication service unreachable", "details": str(e)}),
            500,
        )
    except requests.exceptions.JSONDecodeError:
        return (
            jsonify({"error": "Invalid JSON response from authentication service"}),
            500,
        )
    except Exception as e:
        return jsonify({"error": "Unexpected error", "details": str(e)}), 500


@app.route("/api/register", methods=["POST"])
def register():
    """Proxy user registration request to the authentication service"""
    try:
        data = request.json
        response = requests.post(f"{AUTH_SERVICE_URL}/register", json=data)
        return jsonify(response.json()), response.status_code
    except requests.exceptions.RequestException as e:
        return (
            jsonify({"error": "Authentication service unreachable", "details": str(e)}),
            500,
        )
    except Exception as e:
        if "JSONDecodeError" in str(e):
            return jsonify({"error": "Invalid JSON format"}), 400
        return jsonify({"error": "Unexpected error", "details": str(e)}), 500


@app.route("/api/start_chat", methods=["POST"])
def start_chat():
    """Proxy chat initiation request to the chat service"""
    CHAT_SERVICE_URL = random.choice(lt)
    try:
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"error": "Authorization token is missing"}), 401
        data = request.json  # Get JSON data from the request
        headers = {
            "Authorization": token,  # Forward authentication token
            "Content-Type": "application/json",
        }
        response = requests.post(
            f"{CHAT_SERVICE_URL}/start_chat", json=data, headers=headers
        )  # Forward request to chat service
        return jsonify(response.json()), response.status_code

    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Chat service unreachable", "details": str(e)}), 500
    except requests.exceptions.JSONDecodeError:
        return jsonify({"error": "Invalid JSON response from chat service"}), 500


# get chat list
@app.route("/api/chat_list", methods=["GET"])
def chat_list():
    """Proxy chat list request to the chat service"""
    CHAT_SERVICE_URL = random.choice(lt)
    try:
        token = request.headers.get("Authorization")

        if not token:
            return jsonify({"error": "Authorization token is missing"}), 401

        headers = {
            "Authorization": token,  # Forward authentication token
            "Content-Type": "application/json",
        }

        response = requests.get(
            f"{CHAT_SERVICE_URL}/chat_list", headers=headers
        )  # Forward request to chat service
        
        return jsonify(response.json()), response.status_code

    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Chat service unreachable", "details": str(e)}), 500
    except requests.exceptions.JSONDecodeError:
        return jsonify({"error": "Invalid JSON response from chat service"}), 500


# get chat history
@app.route("/api/chat_history", methods=["GET"])
def chat_history():
    """Forward the /api/chat_history request to the backend service."""
    CHAT_SERVICE_URL = random.choice(lt)
    try:
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"error": "Authorization token is missing"}), 401

        # Get the chat_name from query parameters
        chat_name = request.args.get("chat_name", "")
        params = {"chat_name": chat_name}
        headers = {
            "Authorization": token,  # Forward the authentication token
            "Content-Type": "application/json",
        }

        # Forward the request to the backend service's /chat_history endpoint
        response = requests.get(
            f"{CHAT_SERVICE_URL}/chat_history", headers=headers, params=params
        )
        return jsonify(response.json()), response.status_code

    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Chat service unreachable", "details": str(e)}), 500


@app.route("/api/send_message", methods=["POST"])
def send_message():
    """Forward the /send_message request to the backend service."""
    CHAT_SERVICE_URL = random.choice(lt)
    try:
        token = request.headers.get("Authorization")
        if not token:
            return jsonify({"error": "Authorization token is missing"}), 401

        data = request.get_json()
        headers = {
            "Authorization": token,  # Forward the authentication token
            "Content-Type": "application/json",
        }
        # Forward the request to the backend service's /send_message endpoint
        response = requests.post(
            f"{CHAT_SERVICE_URL}/send_message", headers=headers, json=data
        )
        return Response(
            response.content,
            status=response.status_code,
            content_type=response.headers.get("Content-Type"),
        )

    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Chat service unreachable", "details": str(e)}), 500


if __name__ == "__main__":
    app.run(port=5001, debug=True)
