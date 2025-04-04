import os
import re
import json
from dotenv import load_dotenv
import openai
from dateutil import parser
from fetch_availability import (
    get_available_slots,
    book_appointment,
    get_doctors_by_department,
    suggest_department_based_on_symptom,
    is_valid_future_date_for_doctor
)

# Load API key
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key=OPENAI_API_KEY)

conversation_history = []
stored_department = None
stored_doctor = None
stored_date = None
stored_time = None

def parse_natural_language_date(date_str):
    try:
        date_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)
        dt = parser.parse(date_str)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None

def chat_with_openai(user_message):
    global stored_department, stored_doctor, stored_date, stored_time, conversation_history

    conversation_history.append({"role": "user", "content": user_message})

    try:
        # 1. Date selection step
        if stored_doctor and not stored_date:
            date_value, error = is_valid_future_date_for_doctor(stored_doctor, user_message)
            if error:
                return error
            stored_date = date_value
            return f"Valid date selected. Please provide a preferred time for your appointment with Dr. {stored_doctor} (e.g., 10 AM)."

        # 2. Time selection step
        if stored_doctor and stored_date and not stored_time:
            time_str = parse_natural_language_date(user_message)
            if not time_str:
                return "Sorry, I couldn't understand the time format. Please enter something like '10 AM'."
            stored_time = time_str[-8:]
            return f"Confirming appointment for Dr. {stored_doctor} on {stored_date} at {stored_time}. Please type 'yes' to confirm."

        # 3. Booking confirmation
        if stored_doctor and stored_date and stored_time and user_message.lower() in ["yes", "confirm"]:
            result = book_appointment(stored_doctor, stored_date, stored_time)
            # Reset all stored context
            stored_department = stored_doctor = stored_date = stored_time = None
            conversation_history.clear()
            return result

        # 4. User says a doctor's name (no date given yet)
        if stored_doctor is None and any(dr in user_message.lower() for dr in ["dr", "john", "smith", "brown"]):
            stored_doctor = user_message
            return get_available_slots(stored_doctor) + " You can now select a date (e.g., 26 March)."

        # 5. User says 'yes' after department suggestion
        if stored_department and user_message.lower() in ["yes", "yes please"]:
            department = stored_department
            stored_department = None
            return get_doctors_by_department(department)

        # 6. Let OpenAI model determine the right function
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content":
                 "You are a helpful assistant at a doctor's clinic. "
                 "You ask patients their symptoms, suggest departments, list available doctors, show future slots, and book confirmed appointments. "
                 "Only suggest dates/times that are in the future and available."},
                *conversation_history,
            ],
            functions=[
                {
                    "name": "suggest_department_based_on_symptom",
                    "description": "Suggest department based on symptom",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symptom": {"type": "string"}
                        },
                        "required": ["symptom"]
                    }
                },
                {
                    "name": "get_doctors_by_department",
                    "description": "Fetch doctors by department",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "department_name": {"type": "string"}
                        },
                        "required": ["department_name"]
                    }
                },
                {
                    "name": "get_available_slots",
                    "description": "Fetch available slots for a doctor",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "doctor_name": {"type": "string"}
                        },
                        "required": ["doctor_name"]
                    }
                },
            ],
            function_call="auto"
        )

        msg = response.choices[0].message

        if msg.function_call:
            fn = msg.function_call.name
            args = json.loads(msg.function_call.arguments)

            if fn == "suggest_department_based_on_symptom":
                department = suggest_department_based_on_symptom(args.get("symptom"))
                stored_department = department
                return f"Based on your symptoms, I suggest visiting the {department} department. Would you like to see available doctors in this department? Please type 'yes'."

            elif fn == "get_doctors_by_department":
                return get_doctors_by_department(args.get("department_name"))

            elif fn == "get_available_slots":
                stored_doctor = args.get("doctor_name")
                return get_available_slots(stored_doctor) + " You can now select a date (e.g., 26 March)."

        return msg.content

    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    print("Chatbot: Hello! Welcome to the Super Clinic.")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Chatbot: Goodbye!")
            break
        reply = chat_with_openai(user_input)
        print("Chatbot:", reply)
