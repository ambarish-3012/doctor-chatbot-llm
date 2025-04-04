from database_connection import connect_to_database
from fuzzywuzzy import process
from datetime import datetime, time
from dateutil import parser

def get_corrected_doctor_name(user_input):
    connection = connect_to_database()
    if not connection:
        return user_input

    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT doctor_name FROM doctors")
    doctors = [row["doctor_name"] for row in cursor.fetchall()]
    cursor.close()
    connection.close()

    best_match, score = process.extractOne(user_input, doctors)
    return best_match if score > 75 else user_input

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

def get_doctors_by_department(department_name):
    connection = connect_to_database()
    if not connection:
        return "Database connection failed!"

    cursor = connection.cursor(dictionary=True)
    query = "SELECT doctor_name, specialization FROM doctors WHERE department LIKE CONCAT('%', %s, '%')"
    cursor.execute(query, (department_name,))
    result = cursor.fetchall()
    cursor.close()
    connection.close()

    if not result:
        return f"No doctors available in the {department_name} department at the moment."

    formatted = "\n".join([f"- {doc['doctor_name']} ({doc['specialization']})" for doc in result])
    return f"Here are the available doctors in {department_name}:\n{formatted}\nWho would you like to book an appointment with?"

def get_available_slots(doctor_name):
    doctor_name = get_corrected_doctor_name(doctor_name)
    connection = connect_to_database()
    if not connection:
        return "Database connection failed!"

    cursor = connection.cursor(dictionary=True)
    query = """
    SELECT available_date, available_time 
    FROM availability 
    JOIN doctors ON availability.doctor_id = doctors.doctor_id
    WHERE doctors.doctor_name = %s AND availability.is_booked = FALSE
    ORDER BY available_date ASC, available_time ASC
    """
    cursor.execute(query, (doctor_name,))
    results = cursor.fetchall()
    cursor.close()
    connection.close()

    future_slots = []
    now = datetime.now()

    for slot in results:
        slot_date = slot["available_date"]
        slot_time = slot["available_time"]

        if isinstance(slot_time, datetime):
            slot_time = slot_time.time()
        elif isinstance(slot_time, str):
            slot_time = parser.parse(slot_time).time()
        elif isinstance(slot_time, int):
            slot_time = time(hour=slot_time // 3600, minute=(slot_time % 3600) // 60)
        elif not isinstance(slot_time, time):
            continue

        slot_dt = datetime.combine(slot_date, slot_time)
        if slot_dt > now:
            future_slots.append(f"{slot_date} at {slot_time}")

    if not future_slots:
        return f"No upcoming slots available for {doctor_name}."

    return f"Available slots for {doctor_name}: {future_slots}"

def is_valid_future_date_for_doctor(doctor_name, user_date_str):
    doctor_name = get_corrected_doctor_name(doctor_name)

    try:
        cleaned = user_date_str.lower().replace("st", "").replace("nd", "").replace("rd", "").replace("th", "")
        parsed = parser.parse(cleaned)
        date_only = parsed.date()
    except Exception:
        return None, "Couldn't understand the date format. Please try again like '26 March'."

    if date_only < datetime.today().date():
        return None, "That date has already passed. Please provide a future date."

    connection = connect_to_database()
    if not connection:
        return None, "Failed to connect to database."

    cursor = connection.cursor(dictionary=True)
    query = """
    SELECT available_time 
    FROM availability 
    JOIN doctors ON availability.doctor_id = doctors.doctor_id
    WHERE doctors.doctor_name = %s AND available_date = %s AND availability.is_booked = FALSE
    ORDER BY available_time ASC
    """
    cursor.execute(query, (doctor_name, date_only))
    result = cursor.fetchall()
    cursor.close()
    connection.close()

    if result:
        times = [row['available_time'].strftime('%H:%M:%S') for row in result]
        return date_only.strftime("%Y-%m-%d"), f"Available times on {date_only} for {doctor_name}: {times}. Please choose one."
    else:
        return None, f"No available slots for {doctor_name} on {date_only}. Please choose a different date."

def book_appointment(doctor_name, appointment_date, appointment_time, patient_name="Guest"):
    doctor_name = get_corrected_doctor_name(doctor_name)
    connection = connect_to_database()
    if not connection:
        return "Database connection failed!"

    cursor = connection.cursor()
    cursor.execute("SELECT doctor_id FROM doctors WHERE doctor_name = %s LIMIT 1", (doctor_name,))
    result = cursor.fetchone()
    if not result:
        cursor.close()
        connection.close()
        return f"Doctor {doctor_name} not found."

    doctor_id = result[0]
    query = """
    UPDATE availability 
    SET is_booked = TRUE 
    WHERE doctor_id = %s AND available_date = %s AND available_time = %s AND is_booked = FALSE
    """
    cursor.execute(query, (doctor_id, appointment_date, appointment_time))
    connection.commit()

    if cursor.rowcount == 0:
        cursor.close()
        connection.close()
        return f"Sorry, the slot for {doctor_name} at {appointment_time} on {appointment_date} is no longer available."

    cursor.close()
    connection.close()
    return f"Appointment confirmed with {doctor_name} on {appointment_date} at {appointment_time}."
