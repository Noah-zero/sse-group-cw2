# utils/chatbot_utils.py
import psutil


class ChatBot:
    def __init__(self, client):
        self.client = client
        self.conversation_history = [
            {"role": "system", "content": "Use English to reply."}
        ]

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
            if stream:  # Streaming response
                response = self.client.chat.completions.create(
                    model=model,
                    messages=self.conversation_history,
                    temperature=0.7,
                    max_tokens=16384,
                    extra_headers={"lora_id": "0"},
                    stream=True,
                    stream_options={"include_usage": True},
                )
                for chunk in response:
                    if (
                        hasattr(chunk.choices[0].delta, "content")
                        and chunk.choices[0].delta.content
                    ):
                        chunk_content = chunk.choices[0].delta.content
                        yield chunk_content

            else:  # Normal response
                response = self.client.chat.completions.create(
                    model=model,
                    messages=self.conversation_history,
                    temperature=0.7,
                    max_tokens=16384,
                    extra_headers={"lora_id": "0"},
                )

                assistant_message = response.choices[0].message.content
                self.conversation_history.append(
                    {"role": "assistant", "content": assistant_message}
                )
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
    conversation_history = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in updated_messages["messages"]
    ]
    conversation_history.append({"role": "user", "content": message})
    return conversation_history
