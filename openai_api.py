import os
import openai
from dotenv import load_dotenv
from datetime import datetime
from fetch_availability import (
    get_available_slots,
    book_appointment,
    get_doctors_by_department,
    is_valid_future_date_for_doctor,
    is_valid_time_for_doctor,
    get_departments,
    suggest_department_based_on_symptom,
    fuzzy_match_doctor,
)

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Global state to track conversation
stored_department = None
stored_doctor = None
stored_date = None
stored_time = None

messages = [
    {"role": "system", "content": "You are a helpful medical appointment assistant for Super Clinic."}
]

def chat_with_openai(user_message):
    global stored_department, stored_doctor, stored_date, stored_time

    messages.append({"role": "user", "content": user_message})

    # Step 0: Handle common phrases like "I want to see a doctor"
    if user_message.lower() in [
        "i want to see a doctor",
        "i need to see a doctor",
        "book a doctor",
        "doctor appointment",
        "appointment booking",
        "see doctor",
        "consult a doctor"
    ]:
        return "Sure, I can help you with that. Could you please tell me about your symptoms or the department you'd like to visit?"

    # Step 1: Department-based keyword detection
    departments = get_departments()
    for dept in departments:
        if dept.lower() in user_message.lower():
            stored_department = dept
            doctors = get_doctors_by_department(dept)
            if not doctors:
                return f"No doctors available in the {dept} department at the moment."
            doctor_list = "\n".join([f"- {doc['doctor_name']} ({doc['specialization']})" for doc in doctors])
            return f"Here are the available doctors in {dept}:\n{doctor_list}\nWho would you like to book an appointment with?"

    # Step 2: If no department stored, suggest based on symptoms
    if not stored_department:
        suggested = suggest_department_based_on_symptom(user_message)
        if suggested:
            stored_department = suggested
            return f"Based on your symptoms, I suggest visiting the {suggested} department. Would you like to see available doctors in this department? Please type 'yes'."

    # Step 3: User agrees to proceed
    if stored_department and not stored_doctor and user_message.lower() in ["yes", "yes please"]:
        doctors = get_doctors_by_department(stored_department)
        if not doctors:
            return f"No doctors available in the {stored_department} department at the moment."
        doctor_list = "\n".join([f"- {doc['doctor_name']} ({doc['specialization']})" for doc in doctors])
        return f"Here are the available doctors in {stored_department}:\n{doctor_list}\nWho would you like to book an appointment with?"

    # Step 4: Doctor selection
    if stored_department and not stored_doctor:
        matched_doc = fuzzy_match_doctor(user_message, stored_department)
        if matched_doc:
            stored_doctor = matched_doc["doctor_name"]
            return get_available_slots(stored_doctor) + "\nPlease select a date (e.g., 9 April)."
        else:
            return "Sorry, I couldn't match the doctor name. Please try again with a valid doctor name from the list."

    # Step 5: Capture preferred date
    if stored_doctor and not stored_date:
        date_value, error = is_valid_future_date_for_doctor(stored_doctor, user_message)
        if error:
            return error
        stored_date = date_value
        return "Valid date selected. Please provide a preferred time (e.g., 10 AM)."

    # Step 6: Capture time
    if stored_doctor and stored_date and not stored_time:
        time_value, error = is_valid_time_for_doctor(stored_doctor, stored_date, user_message)
        if error:
            return error
        stored_time = time_value
        return f"Confirming appointment for Dr. {stored_doctor} on {stored_date} at {stored_time}. Type 'yes' to confirm."

    # Step 7: Final confirmation
    if stored_doctor and stored_date and stored_time:
        if user_message.lower() in ["yes", "confirm"]:
            result = book_appointment(stored_doctor, stored_date, stored_time)
            # Reset conversation
            stored_department = stored_doctor = stored_date = stored_time = None
            return result
        else:
            return "Okay, appointment not confirmed. You can choose a different date or time if you'd like."

    # Fallback
    return "I'm here to help you book an appointment. Please share your symptoms or department you'd like to visit."

if __name__ == "__main__":
    print("Chatbot: Hello! Welcome to the Super Clinic.")
    while True:
        user = input("You: ")
        reply = chat_with_openai(user)
        print("Chatbot:", reply)
