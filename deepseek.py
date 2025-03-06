from dotenv import load_dotenv
from utils.chatbot_utils import ChatBot, is_system_under_high_load, combine_message
from utils.db_utils import check_chat_exists, create_chat, get_chat_history_list, get_conversation, update_database
from utils.auth_utils import get_user_id_from_token, get_decoded_token
from flask import Flask, request, jsonify, Response
from openai import OpenAI
import jwt
from supabase import create_client
import random
import os

app = Flask(__name__)

load_dotenv()

# Supabase connection config
# database already exists
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "dummy_key")
SECRET_KEY = os.environ.get("SECRET_KEY", "dummy_secret")

supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)


CLIENT_XUNFEI1_API_KEY = os.environ.get("CLIENT_XUNFEI1_API_KEY", "dummy_xunfei_key")
CLIENT_XUNFEI_BASE_URL = os.environ.get("CLIENT_XUNFEI_BASE_URL")

CLIENT_XUNFEI2_API_KEY = os.environ.get("CLIENT_XUNFEI2_API_KEY", "dummy_xunfei_key1")
CLIENT_XUNFEI_BASE_URL = os.environ.get("CLIENT_XUNFEI_BASE_URL")


# create DeepSeek clients
client_xunfei = OpenAI(
   api_key=CLIENT_XUNFEI1_API_KEY,
   base_url=CLIENT_XUNFEI_BASE_URL
)

client_xunfei1 = OpenAI(
    api_key=CLIENT_XUNFEI2_API_KEY,
    base_url=CLIENT_XUNFEI_BASE_URL
)

lt = [client_xunfei, client_xunfei1]


# start chat
@app.route('/start_chat', methods=['POST'])
def start_chat():
    """ Handle the request forwarded by the API Gateway to create a new chat """
    try:
        user_id = get_user_id_from_token(SECRET_KEY)
        data = request.get_json()
        if not data or 'chat_name' not in data:
            return jsonify({"message": "Invalid request, 'chat_name' is required"}), 400

        chat_name = data.get('chat_name', 'Untitled Chat')

        # Check if a chat with the same name already exists
        existing_chat = check_chat_exists(supabase_client, user_id, chat_name)

        if existing_chat.data:
            return jsonify({"message": "Chat already exists", "chat_name": chat_name}), 200

        # **Create a new chat with no initial messages**
        create_chat(supabase_client, user_id, chat_name)

        return jsonify({"message": "Chat started", "chat_name": chat_name}), 200

    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"message": "Invalid token"}), 401
    except Exception as e:
        return jsonify({"message": "Internal server error", "error": str(e)}), 500


# get chat list
@app.route('/chat_list', methods=['GET'])
def chat_list():
    """ Handle the request forwarded by the API Gateway to retrieve the chat history list """
    try:
        user_id = get_user_id_from_token(SECRET_KEY)
        # Retrieve the chat history list for the user
        response = get_chat_history_list(supabase_client, user_id)

        return jsonify({"chats": [conv["name"] for conv in response.data]}), 200

    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"message": "Invalid token"}), 401
    except Exception as e:
        return jsonify({"message": "Internal server error", "error": str(e)}), 500


# get chat history
@app.route('/chat_history', methods=['GET'])
def chat_history():
    """Handle the /chat_history request forwarded by the API Gateway to fetch a specific chat history."""
    try:        
        decoded_token = get_decoded_token(SECRET_KEY)
        user_id = decoded_token['user_id']
        chat_name = request.args.get('chat_name', '')  # Get chat_name from query parameters

        # Check if chat_name is provided
        if not chat_name:
            return jsonify({"message": "Chat name is required"}), 400

        # Query the database for the user's specific chat history
        conversation = get_chat_history_list(supabase_client, user_id, chat_name)

        if conversation.data:
            messages = conversation.data[0].get('messages', {}).get('messages', [])
            return jsonify({"messages": messages}), 200  # Ensure that the returned value is a list
        else:
            return jsonify({"messages": []}), 200

    except Exception as e:
        print(f"Error in chat_history: {e}")  # Log the error
        return jsonify({"message": "Internal Server Error"}), 500
    

# send message
@app.route('/send_message', methods=['POST'])
def send_message():
    """Handle the /send_message request to send a message to deepseek."""
    try:
        decoded_token = get_decoded_token(SECRET_KEY)
        user_id = decoded_token['user_id']

        data = request.get_json()
        message = data['message']
        chat_name = data.get("chat_name", "Default Chat")

        # Check if the chat history exists for the user and chat_name
        conversation = get_conversation(supabase_client, user_id, chat_name)

        if not conversation.data:
            return jsonify({"message": "Chat not found"}), 404

        updated_messages = conversation.data[0]['messages']
        conversation_history = combine_message(message, updated_messages)

        client1 = random.choice(lt)
        chatbot = ChatBot(client1)

        # Determine whether to use a streaming response based on system load.
        if is_system_under_high_load():
            # Use a normal (non-streaming) response under high load.
            assistant_message = chatbot.chat(conversation_history, stream=False)
            update_database(supabase_client, updated_messages, message, assistant_message, conversation)
            return jsonify({"message": assistant_message}), 200
        else:
            # Use a streaming response.
            assistant_message = ""  # Used to accumulate the entire output.
            def generate():
                nonlocal assistant_message
                for chunk in chatbot.chat(conversation_history, stream=True):
                    assistant_message += chunk
                    yield chunk  # Send chunks to the frontend in real time
                update_database(supabase_client, updated_messages, message, assistant_message, conversation)

            return Response(generate(), content_type='text/plain;charset=utf-8')

    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"message": "Invalid token"}), 401


if __name__ == '__main__':
    app.run(debug=True, port=5002)