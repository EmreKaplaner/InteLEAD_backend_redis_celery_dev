import psycopg2
from psycopg2 import OperationalError

# Database credentials
db_name = "test-database-intelead"
db_user = "postgreintelead"
db_password = "x1KVmwxkixHGJc16"
db_host = "test-database-intelead.cbsuoyka0fzt.eu-north-1.rds.amazonaws.com"
db_port = "5432"

# Function to test connection to the database
def test_db_connection():
    try:
        # Attempt to connect to the database
        connection = psycopg2.connect(
            database=db_name,
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port
        )
        # Check if the connection is valid
        if connection:
            print("Connection successful")
    except OperationalError as e:
        print(f"Connection failed: {e}")
    finally:
        # Close the connection if it's open
        if 'connection' in locals() and connection:
            connection.close()

# Test the connection
test_db_connection()
