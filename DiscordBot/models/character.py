from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, ForeignKey, Table
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class CharacterImage(Base):
    """Model for storing character images."""
    __tablename__ = 'character_images'
    
    id = Column(Integer, primary_key=True)
    character_id = Column(Integer, ForeignKey('characters.id'))
    url = Column(String, nullable=False)
    is_primary = Column(Boolean, default=False)
    affection_required = Column(Integer, default=0)  # Affection level required to unlock
    is_event = Column(Boolean, default=False)  # Whether this is an event image
    event_id = Column(Integer, ForeignKey('events.id'), nullable=True)
    
    # Relationships
    character = relationship("Character", back_populates="images")
    event = relationship("Event", back_populates="character_images")
    
    def __repr__(self):
        return f"<CharacterImage(id={self.id}, character_id={self.character_id})>"

class Character(Base):
    """Character model for storing character data."""
    __tablename__ = 'characters'

    # Basic character information
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    series_id = Column(Integer, ForeignKey('series.id'))
    description = Column(String, nullable=True)
    
    # Relationships
    series = relationship("Series", back_populates="characters")
    images = relationship("CharacterImage", back_populates="character", cascade="all, delete-orphan")
    cards = relationship("Card", back_populates="character")
    
    # Character statistics
    total_cards = Column(Integer, default=0)
    normal_cards = Column(Integer, default=0)
    event_cards = Column(Integer, default=0)
    wishlist_count = Column(Integer, default=0)
    affection_leaderboard = Column(JSON, default=dict)  # Store top users by affection as JSON
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Additional data
    character_metadata = Column(JSON, nullable=True)  # Store additional metadata as JSON
    
    def __repr__(self):
        return f"<Character(id={self.id}, name={self.name})>"
    
    @property
    def primary_image(self):
        """Get the primary image for the character."""
        for image in self.images:
            if image.is_primary:
                return image
        return self.images[0] if self.images else None
    
    @property
    def free_images(self):
        """Get images that don't require affection."""
        return [image for image in self.images if image.affection_required == 0]
    
    @property
    def event_images(self):
        """Get event images for the character."""
        return [image for image in self.images if image.is_event]
    
    @property
    def owners(self):
        """Get users who own cards of this character."""
        return list(set(card.owner for card in self.cards if card.owner))
    
    @property
    def owner_count(self):
        """Get the number of users who own cards of this character."""
        return len(self.owners)
    
    def add_image(self, url, is_primary=False, affection_required=0, is_event=False, event_id=None):
        """Add an image to the character."""
        image = CharacterImage(
            character_id=self.id,
            url=url,
            is_primary=is_primary,
            affection_required=affection_required,
            is_event=is_event,
            event_id=event_id
        )
        self.images.append(image)
        
        if is_event:
            self.event_cards += 1
        else:
            self.normal_cards += 1
            
        self.total_cards = self.normal_cards + self.event_cards
        
        return image
    
    def update_affection_leaderboard(self, user_id, affection):
        """Update the affection leaderboard for the character."""
        if not self.affection_leaderboard:
            self.affection_leaderboard = {}
            
        self.affection_leaderboard[str(user_id)] = affection
        
        # Keep only top 10 users
        sorted_users = sorted(
            self.affection_leaderboard.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        self.affection_leaderboard = dict(sorted_users[:10])
        
    def increment_wishlist_count(self):
        """Increment the wishlist count for the character."""
        self.wishlist_count += 1
        
    def decrement_wishlist_count(self):
        """Decrement the wishlist count for the character."""
        if self.wishlist_count > 0:
            self.wishlist_count -= 1