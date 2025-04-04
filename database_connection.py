import mysql.connector
import os
from dotenv import load_dotenv

# Load database credentials from .env file
load_dotenv()

# Database connection settings
db_config = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "user": os.getenv("MYSQL_USER"),  
    "password": os.getenv("MYSQL_PASSWORD"),  
    "database": os.getenv("MYSQL_DATABASE")
}

def connect_to_database():
    try:
        connection = mysql.connector.connect(**db_config)
        if connection.is_connected():
            print("Connected to MySQL database successfully!")
        return connection
    except mysql.connector.Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

# Test the connection
if __name__ == "__main__":
    conn = connect_to_database()
    if conn:
        conn.close()
