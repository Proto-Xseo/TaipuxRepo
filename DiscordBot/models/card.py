from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, ForeignKey, Table, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class Card(Base):
    """Card model for storing card data."""
    __tablename__ = 'cards'

    # Basic card information
    id = Column(Integer, primary_key=True)
    global_id = Column(String, unique=True, nullable=False)  # Unique identifier for the card
    character_id = Column(Integer, ForeignKey('characters.id'))
    owner_id = Column(String, ForeignKey('users.id'))
    
    # Card details
    rarity = Column(String, nullable=False)  # N, R, SR, SSR, UR, LR, ER
    claimed_artwork = Column(String, nullable=False)  # URL of the artwork
    claim_method = Column(String, default="spawn")  # spawn, trade, gift, auction, gacha
    order = Column(Integer, nullable=False)  # Order in user's collection
    
    # Relationships
    character = relationship("Character", back_populates="cards")
    owner = relationship("User", back_populates="cards")
    
    # Card statistics
    affection = Column(Integer, default=0)
    ascension = Column(Integer, default=0)
    
    # Card stats (placeholders for now)
    stat_1 = Column(Float, default=0.0)
    stat_2 = Column(Float, default=0.0)
    stat_3 = Column(Float, default=0.0)
    stat_4 = Column(Float, default=0.0)
    stat_5 = Column(Float, default=0.0)
    
    # Timestamps
    claimed_at = Column(DateTime, default=datetime.utcnow)
    last_interaction = Column(DateTime, default=datetime.utcnow)
    
    # Flags
    is_favorite = Column(Boolean, default=False)
    is_wishlist = Column(Boolean, default=False)
    is_event = Column(Boolean, default=False)
    is_locked = Column(Boolean, default=False)  # Prevent trading/gifting
    
    # Additional data
    tags = Column(JSON, default=list)  # User-defined tags (emojis)
    custom_name = Column(String, nullable=True)  # User-defined name
    notes = Column(String, nullable=True)  # User-defined notes
    
    def __repr__(self):
        return f"<Card(id={self.id}, global_id={self.global_id}, character_id={self.character_id})>"
    
    def increase_affection(self, amount=1):
        """Increase the affection level of the card."""
        self.affection += amount
        self.last_interaction = datetime.utcnow()
        
        # Update character's affection leaderboard
        if self.character and self.owner:
            self.character.update_affection_leaderboard(self.owner.id, self.affection)
            
        return self.affection
    
    def add_tag(self, tag_emoji):
        """Add a tag to the card."""
        if not self.tags:
            self.tags = []
            
        if tag_emoji not in self.tags:
            self.tags.append(tag_emoji)
            
    def remove_tag(self, tag_emoji):
        """Remove a tag from the card."""
        if not self.tags:
            return
            
        if tag_emoji in self.tags:
            self.tags.remove(tag_emoji)
            
    def toggle_favorite(self):
        """Toggle the favorite status of the card."""
        self.is_favorite = not self.is_favorite
        return self.is_favorite
    
    def toggle_wishlist(self):
        """Toggle the wishlist status of the card."""
        old_status = self.is_wishlist
        self.is_wishlist = not self.is_wishlist
        
        # Update character's wishlist count
        if self.character:
            if self.is_wishlist and not old_status:
                self.character.increment_wishlist_count()
            elif not self.is_wishlist and old_status:
                self.character.decrement_wishlist_count()
                
        return self.is_wishlist
    
    def toggle_lock(self):
        """Toggle the lock status of the card."""
        self.is_locked = not self.is_locked
        return self.is_locked
    
    def transfer_ownership(self, new_owner_id, method="trade"):
        """Transfer ownership of the card to a new user."""
        old_owner_id = self.owner_id
        self.owner_id = new_owner_id
        self.claim_method = method
        self.claimed_at = datetime.utcnow()
        
        # Reset certain attributes
        self.is_favorite = False
        self.is_wishlist = False
        self.tags = []
        self.custom_name = None
        self.notes = None
        
        return old_owner_id