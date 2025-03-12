from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, ForeignKey, Table
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

# Association table for server-admin many-to-many relationship
server_admins = Table(
    'server_admins',
    Base.metadata,
    Column('server_id', String, ForeignKey('servers.id')),
    Column('user_id', String, ForeignKey('users.id'))
)

class Server(Base):
    """Server model for storing server-related data."""
    __tablename__ = 'servers'

    # Basic server information
    id = Column(String, primary_key=True)  # Discord server ID
    name = Column(String, nullable=False)
    registration_time = Column(DateTime, default=datetime.utcnow)
    
    # Channel IDs for specific commands
    spawn_channel_id = Column(String, nullable=True)
    log_channel_id = Column(String, nullable=True)
    welcome_channel_id = Column(String, nullable=True)
    
    # Relationships
    admins = relationship("User", secondary=server_admins)
    
    # Command permissions
    command_permissions = Column(JSON, default=dict)  # Store command permissions as JSON
    # Format: {"command_name": {"allowed_channels": [], "denied_channels": [], "allowed_roles": [], "denied_roles": []}}
    
    # Server settings
    settings = Column(JSON, default=dict)  # Store server settings as JSON
    
    # Server statistics
    total_spawns = Column(Integer, default=0)
    total_claims = Column(Integer, default=0)
    
    # Flags and status
    is_premium = Column(Boolean, default=False)
    is_banned = Column(Boolean, default=False)
    
    def __repr__(self):
        return f"<Server(id={self.id}, name={self.name})>"
    
    def add_admin(self, user):
        """Add an admin to the server."""
        if user not in self.admins:
            self.admins.append(user)
            
    def remove_admin(self, user):
        """Remove an admin from the server."""
        if user in self.admins:
            self.admins.remove(user)
            
    def set_spawn_channel(self, channel_id):
        """Set the spawn channel for the server."""
        self.spawn_channel_id = channel_id
        
    def set_log_channel(self, channel_id):
        """Set the log channel for the server."""
        self.log_channel_id = channel_id
        
    def set_welcome_channel(self, channel_id):
        """Set the welcome channel for the server."""
        self.welcome_channel_id = channel_id
        
    def set_command_permission(self, command_name, permission_type, id_list, allow=True):
        """Set command permissions for the server.
        
        Args:
            command_name (str): The name of the command.
            permission_type (str): The type of permission (channel or role).
            id_list (list): List of channel or role IDs.
            allow (bool): Whether to allow or deny the command.
        """
        if not self.command_permissions:
            self.command_permissions = {}
            
        if command_name not in self.command_permissions:
            self.command_permissions[command_name] = {
                "allowed_channels": [],
                "denied_channels": [],
                "allowed_roles": [],
                "denied_roles": []
            }
            
        if permission_type == "channel":
            key = "allowed_channels" if allow else "denied_channels"
        elif permission_type == "role":
            key = "allowed_roles" if allow else "denied_roles"
        else:
            raise ValueError(f"Invalid permission type: {permission_type}")
            
        self.command_permissions[command_name][key] = id_list
        
    def check_command_permission(self, command_name, channel_id, role_ids):
        """Check if a command is allowed in a channel for roles.
        
        Args:
            command_name (str): The name of the command.
            channel_id (str): The channel ID.
            role_ids (list): List of role IDs.
            
        Returns:
            bool: Whether the command is allowed.
        """
        if not self.command_permissions or command_name not in self.command_permissions:
            return True  # Allow by default
            
        perms = self.command_permissions[command_name]
        
        # Check if channel is explicitly denied
        if channel_id in perms["denied_channels"]:
            return False
            
        # Check if any role is explicitly denied
        if any(role_id in perms["denied_roles"] for role_id in role_ids):
            return False
            
        # Check if channel is explicitly allowed
        if perms["allowed_channels"] and channel_id not in perms["allowed_channels"]:
            return False
            
        # Check if roles are explicitly allowed
        if perms["allowed_roles"] and not any(role_id in perms["allowed_roles"] for role_id in role_ids):
            return False
            
        return True  # Allow if no restrictions apply