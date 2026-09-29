import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY was not found in the .env file")

client = genai.Client(api_key=api_key)

# No tools are used, so turn off automatic function calling (also silences its warning)
config = types.GenerateContentConfig(
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
)


def ask_llm(question):
    response = client.models.generate_content(
       model="gemini-3.5-flash-lite",
        contents=question,
        config=config
    )

    return response.text


MAX_HISTORY_MESSAGES = 20


def ask_llm_stream(messages):
    # messages: chat history as [{"role": "user" | "assistant", "content": str}, ...]
    contents = [
        {
            "role": "model" if message["role"] == "assistant" else "user",
            "parts": [{"text": message["content"]}]
        }
        for message in messages[-MAX_HISTORY_MESSAGES:]
    ]

    stream = client.models.generate_content_stream(
        model="gemini-3.5-flash-lite",
        contents=contents,
        config=config
    )

    for chunk in stream:
        if chunk.text:
            yield chunk.text


if __name__ == "__main__":
    answer = ask_llm("What is machine learning?")
    print("\nGemini Response:")
    print(answer)