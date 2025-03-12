from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, ForeignKey, Table
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class Series(Base):
    """Series model for storing anime series data."""
    __tablename__ = 'series'

    # Basic series information
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    image_url = Column(String, nullable=True)  # Thumbnail image
    
    # Series metadata
    release_year = Column(Integer, nullable=True)
    genre = Column(String, nullable=True)
    studio = Column(String, nullable=True)
    
    # Relationships
    characters = relationship("Character", back_populates="series")
    
    # Series statistics
    total_characters = Column(Integer, default=0)
    total_cards = Column(Integer, default=0)
    popularity_rank = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Additional data
    external_links = Column(JSON, nullable=True)  # Store external links as JSON
    tags = Column(JSON, nullable=True)  # Store tags as JSON
    
    def __repr__(self):
        return f"<Series(id={self.id}, name={self.name})>"
    
    @property
    def character_count(self):
        """Get the number of characters in the series."""
        return len(self.characters)
    
    @property
    def character_names(self):
        """Get a list of character names in the series."""
        return [character.name for character in self.characters]
    
    def add_character(self, character):
        """Add a character to the series."""
        if character not in self.characters:
            self.characters.append(character)
            self.total_characters = len(self.characters)
            
    def update_statistics(self):
        """Update series statistics."""
        self.total_characters = len(self.characters)
        self.total_cards = sum(character.total_cards for character in self.characters)