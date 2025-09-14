# neo4j_driver.py
from neo4j import GraphDatabase
from config import settings
from typing import Dict, Any
from datetime import datetime # <-- Make sure datetime is imported

class Neo4jDriver:
    def __init__(self, uri, user, password):
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.driver.verify_connectivity()
            print("Successfully connected to Neo4j.")
        except Exception as e:
            print(f"Error connecting to Neo4j: {e}")
            self.driver = None

    def close(self):
        if self.driver is not None:
            self.driver.close()
            print("Neo4j connection closed.")

    def execute_query(self, query, parameters=None):
        if self.driver is None:
            print("Neo4j driver not initialized.")
            return None
        with self.driver.session() as session:
            result = session.run(query, parameters)
            return [record for record in result]

neo4j_driver = Neo4jDriver(settings.NEO4J_URI, settings.NEO4J_USER, settings.NEO4J_PASSWORD)

def create_user_node(email: str, full_name: str, username: str):
    query = (
        "MERGE (u:User {email: $email}) "
        "ON CREATE SET u.username = $username, u.fullName = $full_name, u.createdAt = timestamp()"
    )
    parameters = {"email": email, "full_name": full_name, "username": username}
    neo4j_driver.execute_query(query, parameters)
    print(f"Created or merged User node for: {email}")

def update_user_node_properties(email: str, properties: Dict[str, Any]):
    if not properties:
        print("No properties to update in Neo4j.")
        return
    query = (
        "MERGE (u:User {email: $email}) "
        "SET u += $props"
    )
    parameters = {"email": email, "props": properties}
    neo4j_driver.execute_query(query, parameters)
    print(f"Updated Neo4j properties for user: {email}")

# --- THIS IS THE NEW FUNCTION THAT WAS MISSING ---
def create_appointment_node_and_link_to_user(
    email: str,
    appointment_id: str,
    doctor_name: str,
    specialization: str,
    appointment_time: datetime
):
    """
    Creates an Appointment node and links it to an existing User node.
    """
    query = (
        "MATCH (u:User {email: $email}) "
        "MERGE (a:Appointment {id: $appointment_id}) "
        "ON CREATE SET "
        "  a.doctor = $doctor_name, "
        "  a.specialization = $specialization, "
        "  a.appointmentTime = $appointment_time, "
        "  a.createdAt = timestamp() "
        "MERGE (u)-[:HAS_APPOINTMENT]->(a)"
    )
    parameters = {
        "email": email,
        "appointment_id": appointment_id,
        "doctor_name": doctor_name,
        "specialization": specialization,
        "appointment_time": appointment_time.isoformat()
    }
    neo4j_driver.execute_query(query, parameters)
    print(f"Created or merged Appointment node for user: {email}")

def close_neo4j_driver():
    neo4j_driver.close()