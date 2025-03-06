# utils/db_utils.py

import datetime

def check_chat_exists(supabase_client, user_id, chat_name):
    """
    Check if a chat with the same name already exists for a user.
    """
    return supabase_client.table('chat_history') \
        .select('*') \
        .eq('user_id', user_id) \
        .eq('name', chat_name) \
        .execute()

def create_chat(supabase_client, user_id, chat_name):
    """
    Create a new chat with no initial messages for the user.
    """
    now = datetime.datetime.now().isoformat()
    return supabase_client.table('chat_history').insert({
        "user_id": user_id,
        "name": chat_name,
        "messages": {"messages": []},  # Empty chat history
        "created_at": now,
        "updated_at": now,
    }).execute()

def get_chat_history_list(supabase_client, user_id):
    """
    Retrieve the list of chat names for a given user.
    """
    return supabase_client.table('chat_history') \
        .select("name") \
        .eq('user_id', user_id) \
        .execute()

def get_conversation(supabase_client, user_id, chat_name):
    """
    Query the database for the specific conversation of a user by chat name.
    """
    return supabase_client.table('chat_history') \
        .select('*') \
        .eq('user_id', user_id) \
        .eq('name', chat_name) \
        .execute()


def update_database(client, updated_messages, message, assistant_message, conversation):
    """
    Update the database with new chat messages and update the conversation timestamp.
    """
    # Append the user message with a timestamp.
    updated_messages['messages'].append({
        "role": "user",
        "content": message,
        "timestamp": datetime.datetime.now().isoformat()
    })
    # Append the assistant message with a timestamp.
    updated_messages['messages'].append({
        "role": "assistant",
        "content": assistant_message,
        "timestamp": datetime.datetime.now().isoformat()
    })

    # Update the 'chat_history' table with the new messages and updated timestamp.
    client.table('chat_history').update({
        "messages": updated_messages,
        "updated_at": datetime.datetime.now().isoformat()
    }).eq('id', conversation.data[0]['id']).execute()

    print("Database updated successfully")
