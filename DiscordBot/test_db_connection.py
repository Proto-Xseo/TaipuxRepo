"""
Test script to verify database connection.
Run this script to check if the database connection is working properly.
"""
import os
import sys
from pathlib import Path

# Add the parent directory to sys.path to import modules
sys.path.append(str(Path(__file__).parent))

try:
    # Import database modules
    from models.base import get_db, engine, DB_TYPE
    from utils.db import migrate_json_to_db, load_db
    
    # Try to get a database session
    db = get_db()
    
    # Print database information
    print(f"Database type: {DB_TYPE}")
    print(f"Database URL: {engine.url}")
    print("Database connection successful!")
    
    # Check if there's data in the database
    try:
        from models.user import User
        user_count = db.query(User).count()
        print(f"Number of users in database: {user_count}")
        
        if user_count == 0 and DB_TYPE == "postgresql":
            # If there are no users and we're using PostgreSQL, suggest migration
            print("\nNo users found in the database. You may need to migrate data from JSON.")
            print("To migrate data, uncomment and run the following line:")
            print("# migrate_json_to_db()")
        
    except Exception as e:
        print(f"Error querying users: {e}")
    
    # Close the database session
    db.close()
    
except Exception as e:
    print(f"Error connecting to database: {e}")
    
    # If using PostgreSQL, provide some troubleshooting tips
    if os.getenv("DB_TYPE") == "postgresql":
        print("\nTroubleshooting tips for PostgreSQL:")
        print("1. Make sure PostgreSQL is installed and running")
        print("2. Check that the PostgreSQL URL in .env is correct")
        print("3. Verify that the PostgreSQL user has the necessary permissions")
        print("4. Ensure that the psycopg2-binary package is installed")
        print("5. If using Supabase, verify that the Supabase URL and key are correct")