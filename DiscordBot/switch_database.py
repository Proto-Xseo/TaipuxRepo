"""
Database Switcher Script

This script allows you to easily switch between SQLite and PostgreSQL databases
without losing any data. It will:

1. Check your current database configuration
2. Backup your current database
3. Switch to the other database type
4. Migrate your data if needed

Usage:
    python switch_database.py

"""
import os
import sys
import shutil
import datetime
from pathlib import Path

# Add the parent directory to sys.path to import modules
sys.path.append(str(Path(__file__).parent))

def backup_sqlite_db():
    """Create a backup of the SQLite database."""
    from models.base import SQLITE_DB_PATH
    
    if not os.path.exists(SQLITE_DB_PATH):
        print(f"SQLite database not found at {SQLITE_DB_PATH}")
        return False
        
    # Create backup directory if it doesn't exist
    backup_dir = os.path.join(os.path.dirname(SQLITE_DB_PATH), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    
    # Create backup filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"taipu_{timestamp}.db")
    
    # Copy the database file
    shutil.copy2(SQLITE_DB_PATH, backup_path)
    print(f"SQLite database backed up to {backup_path}")
    return True

def modify_env_file(use_postgresql=True):
    """Modify the .env file to use PostgreSQL or SQLite."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    
    if not os.path.exists(env_path):
        print(f".env file not found at {env_path}")
        return False
        
    with open(env_path, "r") as f:
        lines = f.readlines()
        
    with open(env_path, "w") as f:
        for line in lines:
            if line.startswith("DB_TYPE="):
                if use_postgresql:
                    f.write("DB_TYPE=postgresql\n")
                else:
                    f.write("DB_TYPE=sqlite\n")
            elif line.startswith("# POSTGRESQL_URL=") and use_postgresql:
                f.write(line[2:])  # Remove the comment
            elif line.startswith("POSTGRESQL_URL=") and not use_postgresql:
                f.write("# " + line)  # Add a comment
            elif line.startswith("# SUPABASE_URL=") and use_postgresql:
                f.write(line[2:])  # Remove the comment
            elif line.startswith("SUPABASE_URL=") and not use_postgresql:
                f.write("# " + line)  # Add a comment
            elif line.startswith("# SUPABASE_KEY=") and use_postgresql:
                f.write(line[2:])  # Remove the comment
            elif line.startswith("SUPABASE_KEY=") and not use_postgresql:
                f.write("# " + line)  # Add a comment
            else:
                f.write(line)
                
    print(f".env file modified to use {'PostgreSQL' if use_postgresql else 'SQLite'}")
    return True

def check_database():
    """Check the database connection and print information."""
    try:
        from models.base import get_db, engine, DB_TYPE
        
        print(f"Database type: {DB_TYPE}")
        print(f"Database URL: {engine.url}")
        
        # Try to get a database session
        db = get_db()
        print("Database connection successful!")
        
        # Check if there's data in the database
        try:
            from models.user import User
            user_count = db.query(User).count()
            print(f"Number of users in database: {user_count}")
            
            from models.character import Character
            character_count = db.query(Character).count()
            print(f"Number of characters in database: {character_count}")
            
            from models.card import Card
            card_count = db.query(Card).count()
            print(f"Number of cards in database: {card_count}")
            
        except Exception as e:
            print(f"Error querying database: {e}")
            return False
            
        # Close the database session
        db.close()
        return True
        
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return False

def migrate_data():
    """Migrate data from JSON to the database."""
    from utils.db import migrate_json_to_db
    
    print("Migrating data from JSON to the database...")
    success = migrate_json_to_db()
    
    if success:
        print("Data migration completed successfully.")
    else:
        print("Data migration failed.")
        
    return success

def main():
    """Main function to run the database switcher."""
    print("=== Database Switcher ===")
    print("This script allows you to switch between SQLite and PostgreSQL databases.")
    print()
    
    # Check current database configuration
    from models.base import DB_TYPE
    print(f"Current database type: {DB_TYPE}")
    
    # Ask user which database to use
    if DB_TYPE == "sqlite":
        print("\nYou are currently using SQLite.")
        choice = input("Do you want to switch to PostgreSQL? (y/n): ")
        use_postgresql = choice.lower() == "y"
    else:
        print("\nYou are currently using PostgreSQL.")
        choice = input("Do you want to switch to SQLite? (y/n): ")
        use_postgresql = choice.lower() != "y"
        
    if (DB_TYPE == "sqlite" and not use_postgresql) or (DB_TYPE == "postgresql" and use_postgresql):
        print("\nNo changes needed. Exiting.")
        return
        
    # Check current database
    print("\nChecking current database...")
    current_db_ok = check_database()
    
    if not current_db_ok:
        print("Current database check failed. Make sure your database is properly configured.")
        return
        
    # Backup SQLite database if needed
    if DB_TYPE == "sqlite" and use_postgresql:
        print("\nBacking up SQLite database...")
        backup_ok = backup_sqlite_db()
        
        if not backup_ok:
            print("SQLite database backup failed. Switch aborted.")
            return
            
    # Switch database type
    print(f"\nSwitching to {'PostgreSQL' if use_postgresql else 'SQLite'}...")
    modify_env_file(use_postgresql=use_postgresql)
    
    # Reload modules to apply changes
    import importlib
    import models.base
    importlib.reload(models.base)
    
    # Check new database
    print("\nChecking new database...")
    new_db_ok = check_database()
    
    if not new_db_ok:
        print(f"New database check failed. Make sure your {'PostgreSQL' if use_postgresql else 'SQLite'} database is properly configured.")
        print(f"Switching back to {DB_TYPE}...")
        modify_env_file(use_postgresql=(DB_TYPE == "postgresql"))
        return
        
    # Migrate data if needed
    print("\nChecking if data migration is needed...")
    try:
        from models.user import User
        from models.base import get_db
        
        db = get_db()
        user_count = db.query(User).count()
        
        if user_count == 0:
            print("No users found in the new database. Migrating data...")
            migration_ok = migrate_data()
            
            if not migration_ok:
                print("Data migration failed. Switch aborted.")
                print(f"Switching back to {DB_TYPE}...")
                modify_env_file(use_postgresql=(DB_TYPE == "postgresql"))
                return
        else:
            print(f"Found {user_count} users in the new database. No migration needed.")
            
    except Exception as e:
        print(f"Error checking for data migration: {e}")
        print(f"Switching back to {DB_TYPE}...")
        modify_env_file(use_postgresql=(DB_TYPE == "postgresql"))
        return
        
    print(f"\nSwitch to {'PostgreSQL' if use_postgresql else 'SQLite'} completed successfully!")
    print("You can now run the bot with the new database configuration.")

if __name__ == "__main__":
    main()