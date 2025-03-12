from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, ForeignKey, Table
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

# Association table for user-badge many-to-many relationship
user_badges = Table(
    'user_badges',
    Base.metadata,
    Column('user_id', String, ForeignKey('users.id')),
    Column('badge_id', Integer, ForeignKey('badges.id'))
)

# Association table for user favorite series
user_favorite_series = Table(
    'user_favorite_series',
    Base.metadata,
    Column('user_id', String, ForeignKey('users.id')),
    Column('series_id', Integer, ForeignKey('series.id'))
)

# Association table for user favorite characters
user_favorite_characters = Table(
    'user_favorite_characters',
    Base.metadata,
    Column('user_id', String, ForeignKey('users.id')),
    Column('character_id', Integer, ForeignKey('characters.id'))
)

class User(Base):
    """User model for storing user-related data."""
    __tablename__ = 'users'

    # Basic user information
    id = Column(String, primary_key=True)  # Discord user ID
    username = Column(String)
    join_date = Column(DateTime, default=datetime.utcnow)
    
    # Statistics
    total_claims = Column(Integer, default=0)
    total_cards = Column(Integer, default=0)
    
    # Relationships
    cards = relationship("Card", back_populates="owner")
    badges = relationship("Badge", secondary=user_badges, back_populates="users")
    favorite_series = relationship("Series", secondary=user_favorite_series)
    favorite_characters = relationship("Character", secondary=user_favorite_characters)
    
    # Inventory and resources
    inventory = Column(JSON, default=dict)  # Store inventory items as JSON
    currency = Column(Integer, default=0)  # Main currency
    premium_currency = Column(Integer, default=0)  # Premium currency
    
    # Profile customization
    profile_color = Column(String, default="#3498db")
    profile_background = Column(String, nullable=True)
    profile_description = Column(String, nullable=True)
    
    # Settings and preferences
    settings = Column(JSON, default=dict)  # Store user settings as JSON
    
    # Leaderboard and ranking
    leaderboard_rank = Column(Integer, nullable=True)
    experience = Column(Integer, default=0)
    level = Column(Integer, default=1)
    
    # Card tags for sorting (user-defined tags)
    card_tags = Column(JSON, default=dict)  # Store tags as JSON: {"tag_emoji": [card_ids]}
    
    # Timestamps for various activities
    last_claim_time = Column(DateTime, nullable=True)
    last_daily_reward = Column(DateTime, nullable=True)
    last_login = Column(DateTime, default=datetime.utcnow)
    
    # Flags and status
    is_premium = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>"
    
    @property
    def rarest_cards(self):
        """Get the user's rarest cards."""
        if not self.cards:
            return []
        
        # Define rarity order (highest to lowest)
        rarity_order = {"ER": 7, "LR": 6, "UR": 5, "SSR": 4, "SR": 3, "R": 2, "N": 1}
        
        # Sort cards by rarity
        sorted_cards = sorted(
            self.cards, 
            key=lambda card: rarity_order.get(card.rarity, 0), 
            reverse=True
        )
        
        return sorted_cards[:5]  # Return top 5 rarest cards
    
    @property
    def favorite_card(self):
        """Get the user's favorite card."""
        if not self.cards:
            return None
        
        for card in self.cards:
            if card.is_favorite:
                return card
        
        # If no favorite is set, return the rarest card
        return self.rarest_cards[0] if self.rarest_cards else None
    
    def add_card(self, card):
        """Add a card to the user's collection."""
        self.cards.append(card)
        self.total_cards += 1
        self.total_claims += 1
        
    def add_badge(self, badge):
        """Add a badge to the user."""
        if badge not in self.badges:
            self.badges.append(badge)
            
    def add_tag(self, tag_emoji, card_id):
        """Add a tag to a card."""
        if not self.card_tags:
            self.card_tags = {}
            
        if tag_emoji not in self.card_tags:
            self.card_tags[tag_emoji] = []
            
        if card_id not in self.card_tags[tag_emoji]:
            self.card_tags[tag_emoji].append(card_id)
            
    def remove_tag(self, tag_emoji, card_id):
        """Remove a tag from a card."""
        if not self.card_tags or tag_emoji not in self.card_tags:
            return
            
        if card_id in self.card_tags[tag_emoji]:
            self.card_tags[tag_emoji].remove(card_id)
            
            # Remove the tag if it's empty
            if not self.card_tags[tag_emoji]:
                del self.card_tags[tag_emoji]

class Badge(Base):
    """Badge model for storing badge information."""
    __tablename__ = 'badges'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    icon_url = Column(String, nullable=True)
    
    # Relationships
    users = relationship("User", secondary=user_badges, back_populates="badges")
    
    def __repr__(self):
        return f"<Badge(id={self.id}, name={self.name})>"