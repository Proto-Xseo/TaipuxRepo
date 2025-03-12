from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, ForeignKey, Table
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class Event(Base):
    """Event model for storing event data."""
    __tablename__ = 'events'

    # Basic event information
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    banner_image = Column(String, nullable=True)
    
    # Event dates
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    
    # Event status
    is_active = Column(Boolean, default=False)
    
    # Relationships
    character_images = relationship("CharacterImage", back_populates="event")
    
    # Event settings
    settings = Column(JSON, default=dict)  # Store event settings as JSON
    
    # Event statistics
    total_participants = Column(Integer, default=0)
    total_claims = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Event(id={self.id}, name={self.name})>"
    
    @property
    def is_ongoing(self):
        """Check if the event is currently ongoing."""
        now = datetime.utcnow()
        return self.start_date <= now <= self.end_date
    
    @property
    def days_remaining(self):
        """Get the number of days remaining in the event."""
        if not self.is_ongoing:
            return 0
            
        now = datetime.utcnow()
        return (self.end_date - now).days
    
    @property
    def character_count(self):
        """Get the number of characters in the event."""
        character_ids = set(image.character_id for image in self.character_images)
        return len(character_ids)
    
    @property
    def image_count(self):
        """Get the number of images in the event."""
        return len(self.character_images)
    
    def activate(self):
        """Activate the event."""
        self.is_active = True
        
    def deactivate(self):
        """Deactivate the event."""
        self.is_active = False
        
    def add_participant(self):
        """Add a participant to the event."""
        self.total_participants += 1
        
    def add_claim(self):
        """Add a claim to the event."""
        self.total_claims += 1