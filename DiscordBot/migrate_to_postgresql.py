"""
Migration script to transfer data from SQLite to PostgreSQL.
This script will help you migrate your data from SQLite to PostgreSQL without losing any data.
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
            
        except Exception as e:
            print(f"Error querying users: {e}")
            return False
            
        # Close the database session
        db.close()
        return True
        
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return False

def main():
    """Main function to run the migration."""
    print("=== SQLite to PostgreSQL Migration Tool ===")
    print("This script will help you migrate your data from SQLite to PostgreSQL.")
    print("Make sure you have PostgreSQL installed and configured in your .env file.")
    print()
    
    # Check current database configuration
    from models.base import DB_TYPE
    print(f"Current database type: {DB_TYPE}")
    
    if DB_TYPE == "postgresql":
        print("You are already using PostgreSQL.")
        choice = input("Do you want to continue with the migration anyway? (y/n): ")
        if choice.lower() != "y":
            print("Migration cancelled.")
            return
    
    # Check SQLite database
    print("\nChecking SQLite database...")
    original_db_type = DB_TYPE
    
    if original_db_type == "postgresql":
        # Temporarily switch to SQLite
        modify_env_file(use_postgresql=False)
        # Reload modules to apply changes
        import importlib
        import models.base
        importlib.reload(models.base)
    
    sqlite_ok = check_database()
    
    if not sqlite_ok:
        print("SQLite database check failed. Make sure your SQLite database is properly configured.")
        # Switch back to original configuration
        if original_db_type == "postgresql":
            modify_env_file(use_postgresql=True)
        return
    
    # Backup SQLite database
    print("\nBacking up SQLite database...")
    backup_ok = backup_sqlite_db()
    
    if not backup_ok:
        print("SQLite database backup failed. Migration aborted.")
        # Switch back to original configuration
        if original_db_type == "postgresql":
            modify_env_file(use_postgresql=True)
        return
    
    # Switch to PostgreSQL
    print("\nSwitching to PostgreSQL...")
    modify_env_file(use_postgresql=True)
    
    # Reload modules to apply changes
    import importlib
    import models.base
    importlib.reload(models.base)
    
    # Check PostgreSQL database
    print("\nChecking PostgreSQL database...")
    postgresql_ok = check_database()
    
    if not postgresql_ok:
        print("PostgreSQL database check failed. Make sure your PostgreSQL database is properly configured.")
        print("Switching back to SQLite...")
        modify_env_file(use_postgresql=False)
        return
    
    # Migrate data
    print("\nMigrating data to PostgreSQL...")
    migration_ok = migrate_data()
    
    if not migration_ok:
        print("Data migration failed. Switching back to SQLite...")
        modify_env_file(use_postgresql=False)
        return
    
    print("\nMigration completed successfully!")
    print("You are now using PostgreSQL as your database.")
    print("If you encounter any issues, you can switch back to SQLite by editing the .env file.")

if __name__ == "__main__":
    main()