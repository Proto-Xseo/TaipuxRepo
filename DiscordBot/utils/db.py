import json
import os
import datetime
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
import random
import string

from models.base import Base, engine, init_db, get_db
from models.user import User, Badge
from models.server import Server
from models.character import Character, CharacterImage
from models.card import Card
from models.series import Series
from models.event import Event

# Path to the old JSON database
import os.path
OLD_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users.json")
print(f"Using JSON database path: {OLD_DB_PATH}")

def initialize_database():
    """Initialize the database by creating all tables."""
    try:
        init_db()
        print("Database initialized successfully.")
        return True
    except SQLAlchemyError as e:
        print(f"Error initializing database: {e}")
        return False

def migrate_json_to_db():
    """Migrate data from JSON to the database."""
    if not os.path.exists(OLD_DB_PATH):
        print(f"JSON database not found at {OLD_DB_PATH}")
        return False
        
    try:
        # Load JSON data
        with open(OLD_DB_PATH, "r") as f:
            data = json.load(f)
            
        db = get_db()
        
        # Migrate users and their cards
        for user_id, user_data in data.items():
            # Create user if not exists
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                user = User(
                    id=user_id,
                    username=user_data.get("username", f"User_{user_id}"),
                    join_date=datetime.datetime.utcnow(),
                    total_claims=len(user_data.get("cards", [])),
                    total_cards=len(user_data.get("cards", [])),
                    profile_color=user_data.get("profile_color", "#3498db"),
                    leaderboard_rank=user_data.get("leaderboard_rank", None)
                )
                db.add(user)
                
            # Migrate cards
            for card_data in user_data.get("cards", []):
                # Find or create character
                character_name = card_data.get("name", "Unknown")
                character = db.query(Character).filter(Character.name == character_name).first()
                
                if not character:
                    # Find or create series
                    series_name = card_data.get("series", "Unknown")
                    series = db.query(Series).filter(Series.name == series_name).first()
                    
                    if not series:
                        series = Series(name=series_name)
                        db.add(series)
                        db.flush()  # Get series ID
                        
                    character = Character(
                        name=character_name,
                        series_id=series.id
                    )
                    db.add(character)
                    db.flush()  # Get character ID
                    
                    # Add character image
                    artwork = card_data.get("claimed_artwork", "https://via.placeholder.com/800")
                    character.add_image(url=artwork, is_primary=True)
                
                # Create card
                card = Card(
                    global_id=card_data.get("global_id", generate_global_id()),
                    character_id=character.id,
                    owner_id=user_id,
                    rarity=card_data.get("rarity", "N"),
                    claimed_artwork=card_data.get("claimed_artwork", "https://via.placeholder.com/800"),
                    claim_method=card_data.get("claim_method", "spawn"),
                    order=card_data.get("order", 0),
                    affection=card_data.get("affection", 0),
                    is_favorite=card_data.get("favorite", False),
                    claimed_at=datetime.datetime.utcnow()
                )
                db.add(card)
                
        db.commit()
        print("Data migration completed successfully.")
        return True
    except Exception as e:
        print(f"Error migrating data: {e}")
        db.rollback()
        return False

def generate_global_id():
    """Generate a unique global ID for a card."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=7))

# User functions

def load_db():
    """Load all users from the database for backward compatibility."""
    # For backward compatibility, try to load from JSON file first
    try:
        if os.path.exists(OLD_DB_PATH):
            with open(OLD_DB_PATH, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading JSON database: {e}")
        
    # If JSON file doesn't exist or can't be loaded, return empty dict
    return {}

def get_user(user_id):
    """Get a user from the database."""
    # For backward compatibility, try to load from JSON file first
    try:
        if os.path.exists(OLD_DB_PATH):
            with open(OLD_DB_PATH, "r") as f:
                data = json.load(f)
                if str(user_id) in data:
                    return data[str(user_id)]
    except Exception as e:
        print(f"Error loading user from JSON: {e}")
    
    # If we get here, either the JSON file doesn't exist, the user isn't in it,
    # or there was an error loading it. Try the database.
    db = get_db()
    user = db.query(User).filter(User.id == str(user_id)).first()
    
    if not user:
        # For backward compatibility, return empty dict
        return {}
        
    # Convert to dict for backward compatibility
    user_dict = {
        "id": user.id,
        "username": user.username,
        "join_date": user.join_date.strftime("%Y-%m-%d"),
        "total_claims": user.total_claims,
        "total_cards": user.total_cards,
        "cards": [],
        "profile_color": user.profile_color,
        "leaderboard_rank": user.leaderboard_rank,
        "badges": [badge.name for badge in user.badges]
    }
    
    # Add cards
    for card in user.cards:
        character = card.character
        card_dict = {
            "order": card.order,
            "global_id": card.global_id,
            "character_id": character.id,
            "name": character.name,
            "series": character.series.name if character.series else "Unknown",
            "affection": card.affection,
            "claimed_artwork": card.claimed_artwork,
            "rarity": card.rarity,
            "claimed_by": f"<@{user.id}>",
            "favorite": card.is_favorite,
            "wishlist": card.is_wishlist,
            "tags": card.tags
        }
        user_dict["cards"].append(card_dict)
        
    # Add favorite card
    if user.favorite_card:
        user_dict["favourite_card"] = {
            "name": user.favorite_card.character.name,
            "claimed_artwork": user.favorite_card.claimed_artwork,
            "rarity": user.favorite_card.rarity,
            "global_id": user.favorite_card.global_id
        }
        
    return user_dict

def update_user(user_id, key, value):
    """Update a user in the database."""
    db = get_db()
    user = db.query(User).filter(User.id == str(user_id)).first()
    
    if not user:
        # Create new user
        user = User(id=str(user_id))
        db.add(user)
        
    # Handle special keys
    if key == "cards":
        # Clear existing cards and add new ones
        db.query(Card).filter(Card.owner_id == str(user_id)).delete()
        
        for card_data in value:
            # Find or create character
            character_name = card_data.get("name", "Unknown")
            character = db.query(Character).filter(Character.name == character_name).first()
            
            if not character:
                # Find or create series
                series_name = card_data.get("series", "Unknown")
                series = db.query(Series).filter(Series.name == series_name).first()
                
                if not series:
                    series = Series(name=series_name)
                    db.add(series)
                    db.flush()  # Get series ID
                    
                character = Character(
                    name=character_name,
                    series_id=series.id
                )
                db.add(character)
                db.flush()  # Get character ID
                
                # Add character image
                artwork = card_data.get("claimed_artwork", "https://via.placeholder.com/800")
                character.add_image(url=artwork, is_primary=True)
            
            # Create card
            card = Card(
                global_id=card_data.get("global_id", generate_global_id()),
                character_id=character.id,
                owner_id=str(user_id),
                rarity=card_data.get("rarity", "N"),
                claimed_artwork=card_data.get("claimed_artwork", "https://via.placeholder.com/800"),
                claim_method=card_data.get("claim_method", "spawn"),
                order=card_data.get("order", 0),
                affection=card_data.get("affection", 0),
                is_favorite=card_data.get("favorite", False),
                claimed_at=datetime.datetime.utcnow()
            )
            db.add(card)
            
        user.total_cards = len(value)
        user.total_claims = len(value)
    elif key == "favourite_card":
        # Find the card and set it as favorite
        global_id = value.get("global_id")
        if global_id:
            card = db.query(Card).filter(Card.global_id == global_id).first()
            if card:
                # Reset all favorites
                for c in user.cards:
                    c.is_favorite = False
                # Set new favorite
                card.is_favorite = True
    elif key == "profile_color":
        user.profile_color = value
    elif key == "username":
        user.username = value
    elif key == "leaderboard_rank":
        user.leaderboard_rank = value
    elif key == "badges":
        # Clear existing badges and add new ones
        user.badges = []
        for badge_name in value:
            badge = db.query(Badge).filter(Badge.name == badge_name).first()
            if not badge:
                badge = Badge(name=badge_name)
                db.add(badge)
            user.badges.append(badge)
    
    db.commit()
    return True

# Server functions

def get_server(server_id):
    """Get a server from the database."""
    db = get_db()
    server = db.query(Server).filter(Server.id == str(server_id)).first()
    
    if not server:
        return None
        
    return server

def update_server(server_id, name, key, value):
    """Update a server in the database."""
    db = get_db()
    server = db.query(Server).filter(Server.id == str(server_id)).first()
    
    if not server:
        # Create new server
        server = Server(id=str(server_id), name=name)
        db.add(server)
        
    # Handle special keys
    if key == "spawn_channel_id":
        server.spawn_channel_id = value
    elif key == "log_channel_id":
        server.log_channel_id = value
    elif key == "welcome_channel_id":
        server.welcome_channel_id = value
    elif key == "admins":
        # Clear existing admins and add new ones
        server.admins = []
        for admin_id in value:
            user = db.query(User).filter(User.id == str(admin_id)).first()
            if not user:
                user = User(id=str(admin_id))
                db.add(user)
            server.admins.append(user)
    elif key == "command_permissions":
        server.command_permissions = value
    elif key == "settings":
        server.settings = value
        
    db.commit()
    return True

# Character functions

def get_all_characters():
    """Get all characters from the database."""
    db = get_db()
    characters = db.query(Character).all()
    
    # Convert to dict for backward compatibility
    characters_dict = {}
    for character in characters:
        primary_image = character.primary_image
        extra_images = []
        
        for image in character.images:
            if not image.is_primary:
                extra_images.append({
                    "url": image.url,
                    "affection_required": image.affection_required,
                    "is_event": image.is_event
                })
                
        characters_dict[character.name] = {
            "id": character.id,
            "name": character.name,
            "series": character.series.name if character.series else "Unknown",
            "primary_image": {
                "url": primary_image.url if primary_image else "https://via.placeholder.com/800"
            },
            "extra_images": extra_images
        }
        
    return characters_dict

def get_character(character_id=None, name=None):
    """Get a character from the database by ID or name."""
    db = get_db()
    
    if character_id:
        character = db.query(Character).filter(Character.id == character_id).first()
    elif name:
        character = db.query(Character).filter(Character.name == name).first()
    else:
        return None
        
    if not character:
        return None
        
    return character

def add_character(name, series_name, primary_image_url, description=None):
    """Add a character to the database."""
    db = get_db()
    
    # Check if character already exists
    character = db.query(Character).filter(Character.name == name).first()
    if character:
        return character
        
    # Find or create series
    series = db.query(Series).filter(Series.name == series_name).first()
    if not series:
        series = Series(name=series_name)
        db.add(series)
        db.flush()  # Get series ID
        
    # Create character
    character = Character(
        name=name,
        series_id=series.id,
        description=description
    )
    db.add(character)
    db.flush()  # Get character ID
    
    # Add primary image
    character.add_image(url=primary_image_url, is_primary=True)
    
    db.commit()
    return character

# Card functions

def get_card(global_id):
    """Get a card from the database by global ID."""
    db = get_db()
    card = db.query(Card).filter(Card.global_id == global_id).first()
    
    if not card:
        return None
        
    return card

def add_card(user_id, character_id, rarity, claimed_artwork, claim_method="spawn"):
    """Add a card to the database."""
    db = get_db()
    
    # Get user
    user = db.query(User).filter(User.id == str(user_id)).first()
    if not user:
        user = User(id=str(user_id))
        db.add(user)
        
    # Get character
    character = db.query(Character).filter(Character.id == character_id).first()
    if not character:
        return None
        
    # Create card
    order = len(user.cards) + 1
    global_id = generate_global_id()
    
    card = Card(
        global_id=global_id,
        character_id=character.id,
        owner_id=str(user_id),
        rarity=rarity,
        claimed_artwork=claimed_artwork,
        claim_method=claim_method,
        order=order,
        claimed_at=datetime.datetime.utcnow()
    )
    db.add(card)
    
    # Update user stats
    user.total_cards += 1
    user.total_claims += 1
    
    db.commit()
    return card

# Load all characters from JSON files
def load_characters_from_json():
    """Load characters from JSON files and add them to the database."""
    characters = {}
    base_dir = "DiscordBot/assets/characters/"
    
    if not os.path.exists(base_dir):
        print(f"Characters directory not found at {base_dir}")
        return {}
        
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".json"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r") as f:
                        data = json.load(f)
                        characters.update(data)
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
                    
    # Add characters to database
    db = get_db()
    
    for name, character_data in characters.items():
        # Find or create series
        series_name = character_data.get("series", "Unknown")
        series = db.query(Series).filter(Series.name == series_name).first()
        
        if not series:
            series = Series(name=series_name)
            db.add(series)
            db.flush()  # Get series ID
            
        # Find or create character
        character = db.query(Character).filter(Character.name == name).first()
        
        if not character:
            character = Character(
                name=name,
                series_id=series.id,
                description=character_data.get("description")
            )
            db.add(character)
            db.flush()  # Get character ID
            
            # Add primary image
            primary_image = character_data.get("primary_image", {}).get("url")
            if primary_image:
                character.add_image(url=primary_image, is_primary=True)
                
            # Add extra images
            for image_data in character_data.get("extra_images", []):
                character.add_image(
                    url=image_data.get("url"),
                    is_primary=False,
                    affection_required=image_data.get("affection_required", 0),
                    is_event=image_data.get("is_event", False)
                )
                
    db.commit()
    return characters

# Initialize database on module import
from models.base import DB_TYPE

# Only create directories for SQLite
if DB_TYPE == "sqlite":
    if not os.path.exists(os.path.dirname(engine.url.database)):
        os.makedirs(os.path.dirname(engine.url.database), exist_ok=True)
    
initialize_database()