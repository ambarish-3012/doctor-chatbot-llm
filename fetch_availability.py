import mysql.connector
from datetime import datetime, time, timedelta
from dateutil import parser
from fuzzywuzzy import process
from database_connection import connect_to_database


def get_departments():
    conn = connect_to_database()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT DISTINCT department FROM doctors")
    departments = [row["department"] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return departments

def suggest_department_based_on_symptom(symptom):
    symptom_to_department = {
        "chest pain": "Cardiology",
        "heart": "Cardiology",
        "knee": "Orthopedics",
        "bone": "Orthopedics",
        "fracture": "Orthopedics",
        "stomach": "Gastroenterology",
        "skin": "Dermatology",
        "rash": "Dermatology",
        "eye": "Ophthalmology",
        "ear": "ENT",
        "cold": "General Medicine",
        "fever": "General Medicine",
    }

    for keyword, department in symptom_to_department.items():
        if keyword in symptom.lower():
            return department

    return "General Medicine"
    
def get_doctors_by_department(department):
    conn = connect_to_database()
    cursor = conn.cursor(dictionary=True)
    query = """
        SELECT doctor_name, specialization
        FROM doctors
        WHERE department = %s
    """
    cursor.execute(query, (department,))
    doctors = cursor.fetchall()
    cursor.close()
    conn.close()
    return doctors


def fuzzy_match_doctor(user_input, department):
    doctors = get_doctors_by_department(department)
    doctor_names = [doc["doctor_name"] for doc in doctors]
    best_match, score = process.extractOne(user_input, doctor_names)
    if score > 70:
        for doc in doctors:
            if doc["doctor_name"] == best_match:
                return doc
    return None


def get_available_slots(doctor_name):
    conn = connect_to_database()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT d.doctor_id, d.doctor_name, a.available_date, a.available_time
        FROM doctors d
        JOIN availability a ON d.doctor_id = a.doctor_id
        WHERE d.doctor_name = %s AND a.is_booked = 0
        ORDER BY a.available_date, a.available_time
    """
    cursor.execute(query, (doctor_name,))
    results = cursor.fetchall()
    cursor.close()
    conn.close()

    future_slots = []
    now = datetime.now()

    for slot in results:
        slot_date = slot["available_date"]
        slot_time = slot["available_time"]

        # Fix: Convert timedelta (MySQL TIME) to time object
        if isinstance(slot_time, timedelta):
            total_seconds = int(slot_time.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            slot_time = time(hour=hours, minute=minutes)
        elif isinstance(slot_time, datetime):
            slot_time = slot_time.time()
        elif isinstance(slot_time, str):
            slot_time = parser.parse(slot_time).time()
        elif isinstance(slot_time, int):
            slot_time = time(hour=slot_time // 3600, minute=(slot_time % 3600) // 60)
        elif not isinstance(slot_time, time):
            continue

        slot_dt = datetime.combine(slot_date, slot_time)
        if slot_dt > now:
            future_slots.append(f"{slot_date} at {slot_time.strftime('%H:%M:%S')}")

    if future_slots:
        return f"Available slots for Dr. {doctor_name}: {future_slots}"
    else:
        return f"No upcoming slots available for Dr. {doctor_name}."


def is_valid_future_date_for_doctor(doctor_name, user_input):
    try:
        requested_date = parser.parse(user_input, fuzzy=True).date()
        now = datetime.now().date()
        if requested_date < now:
            return None, "The selected date is in the past. Please choose a future date."

        conn = connect_to_database()
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT a.available_date, a.available_time
            FROM doctors d
            JOIN availability a ON d.doctor_id = a.doctor_id
            WHERE d.doctor_name = %s AND a.is_booked = 0 AND a.available_date = %s
        """
        cursor.execute(query, (doctor_name, requested_date))
        slots = cursor.fetchall()
        cursor.close()
        conn.close()

        if slots:
            return requested_date, None
        else:
            return None, f"No available slots for Dr. {doctor_name} on {requested_date}. Please choose a different date."

    except Exception as e:
        return None, f"Error: {str(e)}"


def is_valid_time_for_doctor(doctor_name, date_value, user_input):
    try:
        requested_time = parser.parse(user_input, fuzzy=True).time()
        conn = connect_to_database()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT a.id
            FROM doctors d
            JOIN availability a ON d.doctor_id = a.doctor_id
            WHERE d.doctor_name = %s AND a.available_date = %s
              AND a.available_time = %s AND a.is_booked = 0
        """
        cursor.execute(query, (doctor_name, date_value, requested_time))
        slot = cursor.fetchone()
        cursor.close()
        conn.close()

        if slot:
            return requested_time, None
        else:
            return None, "Selected time is not available. Please choose a different time."

    except Exception as e:
        return None, f"Error: {str(e)}"


def book_appointment(doctor_name, date_value, time_value):
    conn = connect_to_database()
    cursor = conn.cursor(dictionary=True)

    # Find doctor_id
    cursor.execute("SELECT doctor_id FROM doctors WHERE doctor_name = %s", (doctor_name,))
    result = cursor.fetchone()
    if not result:
        cursor.close()
        conn.close()
        return f"Doctor {doctor_name} not found."

    doctor_id = result["doctor_id"]

    # Update slot to booked
    update_query = """
        UPDATE availability
        SET is_booked = 1
        WHERE doctor_id = %s AND available_date = %s AND available_time = %s AND is_booked = 0
    """
    cursor.execute(update_query, (doctor_id, date_value, time_value))
    conn.commit()
    affected_rows = cursor.rowcount
    cursor.close()
    conn.close()

    if affected_rows:
        return f"Appointment confirmed with Dr. {doctor_name} on {date_value} at {time_value}."
    else:
        return f"Sorry, the slot for Dr. {doctor_name} at {time_value} on {date_value} is no longer available."
