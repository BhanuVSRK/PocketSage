#!/usr/bin/env python3
"""
Startup script for SageAI Medical Advisor
"""

import subprocess
import sys
import os
import time
from pathlib import Path

def check_env_file():
    """Check if .env file exists and create from template if needed"""
    if not os.path.exists('.env'):
        if os.path.exists('.env.example'):
            print("No .env file found. Please copy .env.example to .env and configure:")
            print("  cp .env.example .env")
            print("  # Edit .env with your API keys and database settings")
            return False
        else:
            print("Neither .env nor .env.example found. Creating basic template...")
            with open('.env', 'w') as f:
                f.write("""# SageAI Medical Advisor Configuration
MONGO_URI=mongodb://localhost:27017
DB_NAME=sageai_medical
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=change_me
SECRET_KEY=change-this-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=1440
GEMINI_API_KEY=your_gemini_api_key_here
ASSEMBLYAI_API_KEY=your_assemblyai_api_key_here
AUDIO_FILES_DIR=audio_records
""")
            print("Created basic .env file. Please edit it with your settings.")
            return False
    return True

def install_dependencies():
    """Install required dependencies"""
    print("Installing dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True, capture_output=True)
        print("Dependencies installed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install dependencies: {e}")
        return False

def check_databases():
    """Check if databases are running"""
    print("Checking database connections...")
    
    # Check MongoDB
    try:
        import pymongo
        client = pymongo.MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=2000)
        client.admin.command('ping')
        print("MongoDB: Connected")
        mongo_ok = True
    except Exception:
        print("MongoDB: Not accessible (make sure MongoDB is running)")
        mongo_ok = False
    
    # Check Neo4j
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "neo4j"))
        with driver.session() as session:
            session.run("RETURN 1")
        print("Neo4j: Connected")
        neo4j_ok = True
        driver.close()
    except Exception:
        print("Neo4j: Not accessible (make sure Neo4j is running)")
        neo4j_ok = False
    
    if not (mongo_ok or neo4j_ok):
        print("\nWarning: Neither database is accessible.")
        print("The application may not function properly.")
        print("Please ensure MongoDB and Neo4j are installed and running.")
    
    return mongo_ok, neo4j_ok

def start_backend():
    """Start the FastAPI backend"""
    print("Starting FastAPI backend...")
    try:
        # Run in background
        backend_process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", 
            "main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000",
            "--reload"
        ])
        
        # Wait a moment for startup
        time.sleep(3)
        
        # Check if process is still running
        if backend_process.poll() is None:
            print("Backend started successfully on http://localhost:8000")
            return backend_process
        else:
            print("Backend failed to start")
            return None
            
    except Exception as e:
        print(f"Failed to start backend: {e}")
        return None

def start_frontend():
    """Start the Streamlit frontend"""
    print("Starting Streamlit frontend...")
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "app.py",
            "--server.port", "8501",
            "--server.address", "0.0.0.0"
        ])
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Failed to start frontend: {e}")

def main():
    """Main startup function"""
    print("SageAI Medical Advisor - Startup Script")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists("main.py") or not os.path.exists("app.py"):
        print("Error: main.py or app.py not found!")
        print("Please run this script from the project root directory.")
        return
    
    # Check environment configuration
    if not check_env_file():
        return
    
    # Install dependencies
    if not install_dependencies():
        return
    
    # Check databases
    check_databases()
    
    print("\nStarting application components...")
    print("Press Ctrl+C to stop")
    
    # Start backend
    backend_process = start_backend()
    
    if backend_process:
        try:
            # Start frontend (this blocks)
            start_frontend()
        finally:
            # Cleanup
            if backend_process and backend_process.poll() is None:
                print("Stopping backend...")
                backend_process.terminate()
                backend_process.wait()
    else:
        print("Cannot start frontend without backend.")

if __name__ == "__main__":
    main()