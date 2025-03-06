from flask import Flask, request, jsonify, Response
from openai import OpenAI
import psutil
import datetime
import jwt
from supabase import create_client
import random
import os

app = Flask(__name__)


# Supabase connection config
# database already exists
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "dummy_key")
SECRET_KEY = os.environ.get("SECRET_KEY", "dummy_secret")
client = create_client(SUPABASE_URL, SUPABASE_KEY)


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

class ChatBot:
    def __init__(self, client):
        self.client = client
        self.conversation_history = [{"role": "system", "content": "Use English to reply."}]

    # store new message in conversation_history
    def add_message(self, message):
        self.conversation_history.extend(message)

    # return response
    # if stream is False, don't return until deepseek generate whole sentences
    # if stream is True, return while deepseek generate sentences
    # streaming is disabled when underload
    def chat(self, message, model="xdeepseekv3", stream=False):
        self.add_message(message)
        try:
            if stream: # Streaming response
                response = self.client.chat.completions.create(
                    model=model,
                    messages=self.conversation_history,
                    temperature=0.7,
                    max_tokens=16384,
                    extra_headers={"lora_id": "0"},
                    stream=True,
                    stream_options={"include_usage": True}
                )

                for chunk in response:
                    if hasattr(chunk.choices[0].delta, "content") and chunk.choices[0].delta.content:
                        chunk_content = chunk.choices[0].delta.content
                        yield chunk_content

            else: # Normal response
                response = self.client.chat.completions.create(
                    model=model,
                    messages=self.conversation_history,
                    temperature=0.7,
                    max_tokens=16384,
                    extra_headers={"lora_id": "0"}
                )

                assistant_message = response.choices[0].message.content
                self.conversation_history.append({"role": "assistant", "content": assistant_message})
                return assistant_message
        except Exception as e:
            return f"Error: {e}"
        
# Determine whether the server is under high load by evaluating CPU or memory usage
def is_system_under_high_load():
    cpu_usage = psutil.cpu_percent()
    memory_usage = psutil.virtual_memory().percent
    return cpu_usage > 80 or memory_usage > 80


# Reduce token consumption
# by removing unnecessary information (such as timestamps) from the chat history.
def combine_message(message, updated_messages):
    print(updated_messages)
    conversation_history = [{"role": msg["role"], "content": msg["content"]}
                            for msg in updated_messages['messages']]
    conversation_history.append({"role": "user", "content": message})
    return conversation_history

# update datebase
def update_database(updated_messages, message, assistant_message, conversation):
    updated_messages['messages'].append(
        {"role": "user", "content": message, "timestamp": datetime.datetime.now().isoformat()})
    updated_messages['messages'].append(
        {"role": "assistant", "content": assistant_message, "timestamp": datetime.datetime.now().isoformat()})

    client.table('chat_history').update({
        "messages": updated_messages, "updated_at": datetime.datetime.now().isoformat()
    }).eq('id', conversation.data[0]['id']).execute()

    print("database update successfully")

# start chat
@app.route('/start_chat', methods=['POST'])
def start_chat():
    """ Handle the request forwarded by the API Gateway to create a new chat """
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({"message": "Authorization token is missing"}), 401

    try:
        # Decode JWT to obtain user information
        decoded_token = jwt.decode(token.split(" ")[1], SECRET_KEY, algorithms=["HS256"])
        user_id = decoded_token['user_id']

        data = request.get_json()
        if not data or 'chat_name' not in data:
            return jsonify({"message": "Invalid request, 'chat_name' is required"}), 400

        chat_name = data.get('chat_name', 'Untitled Chat')

        # Check if a chat with the same name already exists
        existing_chat = client.table('chat_history') \
            .select('*') \
            .eq('user_id', user_id) \
            .eq('name', chat_name) \
            .execute()

        if existing_chat.data:
            return jsonify({"message": "Chat already exists", "chat_name": chat_name}), 200

        # **Create a new chat with no initial messages**
        client.table('chat_history').insert({
            "user_id": user_id,
            "name": chat_name,
            "messages": {"messages": []},  # Empty chat history
            "created_at": datetime.datetime.now().isoformat(),
            "updated_at": datetime.datetime.now().isoformat(),
        }).execute()

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
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({"message": "Authorization token is missing"}), 401

    try:
        # Decode JWT to obtain user information
        decoded_token = jwt.decode(token.split(" ")[1], SECRET_KEY, algorithms=["HS256"])
        user_id = decoded_token['user_id']

        # Retrieve the chat history list for the user
        response = client.table('chat_history') \
            .select("name") \
            .eq('user_id', user_id) \
            .execute()

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
        # Extract the token from the Authorization header (expected format: "Bearer <token>")
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({"message": "Authorization token is missing"}), 401

        token = auth_header.split(" ")[1]
        chat_name = request.args.get('chat_name', '')  # Get chat_name from query parameters

        # Check if chat_name is provided
        if not chat_name:
            return jsonify({"message": "Chat name is required"}), 400

        # Decode JWT to retrieve user information
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = decoded_token['user_id']

        # Query the database for the user's specific chat history
        conversation = client.table('chat_history') \
            .select('*') \
            .eq('user_id', user_id) \
            .eq('name', chat_name) \
            .execute()

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
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({"message": "Authorization token is missing"}), 401

        token = auth_header.split(" ")[1]
        data = request.get_json()
        message = data['message']
        chat_name = data.get("chat_name", "Default Chat")

        # Decode JWT to retrieve user information
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = decoded_token['user_id']

        # Check if the chat history exists for the user and chat_name
        conversation = client.table('chat_history') \
            .select('*') \
            .eq('user_id', user_id) \
            .eq('name', chat_name) \
            .execute()

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
            update_database(updated_messages, message, assistant_message, conversation)
            return jsonify({"message": assistant_message}), 200
        else:
            # Use a streaming response.
            assistant_message = ""  # Used to accumulate the entire output.

            def generate():
                nonlocal assistant_message
                for chunk in chatbot.chat(conversation_history, stream=True):
                    assistant_message += chunk
                    yield chunk  # Send chunks to the frontend in real time
                update_database(updated_messages, message, assistant_message, conversation)

            return Response(generate(), content_type='text/plain;charset=utf-8')

    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"message": "Invalid token"}), 401


if __name__ == '__main__':
    app.run(debug=True, port=5002)