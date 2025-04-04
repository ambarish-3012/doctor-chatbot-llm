import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load API Key from .env file
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Set up Google Gemini API
genai.configure(api_key="AIzaSyClxWjJaODjNYIJEIxe4Hwf0SuHMpzsm-E")

def get_ai_response(prompt):
    """Send a prompt to Google Gemini and return the response."""
    try:
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

# Test the Gemini API
if __name__ == "__main__":
    user_message = "Hello, how can I book a doctor's appointment?"
    response = get_ai_response(user_message)
    print(f"Chatbot: {response}")