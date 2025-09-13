from neo4j import GraphDatabase
from config import settings
from typing import Dict, Any

class Neo4jDriver:
    # ... (class definition is unchanged)
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

# --- NEW FUNCTION ---
def update_user_node_properties(email: str, properties: Dict[str, Any]):
    """
    Updates a User node with a dictionary of new properties.
    This is efficient as it only sends one query.
    """
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

def close_neo4j_driver():
    neo4j_driver.close()