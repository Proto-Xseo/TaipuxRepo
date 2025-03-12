import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_user, update_user, get_server, update_server
from models.base import get_db
from models.user import User
from models.server import Server
import datetime

class SetupView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=300)  # 5 minute timeout
        self.bot = bot
        
    @discord.ui.button(label="Register Server", style=discord.ButtonStyle.primary, emoji="🏠")
    async def register_server(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if server is already registered
        db = get_db()
        server = db.query(Server).filter(Server.id == str(interaction.guild.id)).first()
        
        if server:
            await interaction.response.send_message(f"✅ Server **{interaction.guild.name}** is already registered!", ephemeral=False)
            return
            
        # Register server
        server = Server(
            id=str(interaction.guild.id),
            name=interaction.guild.name,
            registration_time=datetime.datetime.utcnow()
        )
        db.add(server)
        
        # Add admin (command user)
        user = db.query(User).filter(User.id == str(interaction.user.id)).first()
        if not user:
            user = User(
                id=str(interaction.user.id),
                username=interaction.user.name,
                join_date=datetime.datetime.utcnow()
            )
            db.add(user)
            
        server.add_admin(user)
        db.commit()
        
        # Send confirmation message
        await interaction.response.send_message(f"✅ Server **{interaction.guild.name}** has been registered successfully with admin {interaction.user.mention}!", ephemeral=False)
        
    @discord.ui.button(label="Register User", style=discord.ButtonStyle.success, emoji="👤")
    async def register_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if user is already registered
        db = get_db()
        user = db.query(User).filter(User.id == str(interaction.user.id)).first()
        
        if user:
            # If user exists, just send a confirmation message
            await interaction.response.send_message(f"✅ User **{interaction.user.name}** is already registered! Your data is safe.", ephemeral=False)
            return
            
        # Register user
        user = User(
            id=str(interaction.user.id),
            username=interaction.user.name,
            join_date=datetime.datetime.utcnow()
        )
        db.add(user)
        db.commit()
        
        # Send confirmation message
        await interaction.response.send_message(f"✅ User **{interaction.user.name}** has been registered successfully!", ephemeral=False)
        
    @discord.ui.button(label="Set Spawn Channel", style=discord.ButtonStyle.secondary, emoji="🎮")
    async def set_spawn_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if server is registered
        db = get_db()
        server = db.query(Server).filter(Server.id == str(interaction.guild.id)).first()
        
        if not server:
            await interaction.response.send_message("This server is not registered! Please register the server first.", ephemeral=True)
            return
            
        # Check if user is admin - compare string IDs instead of integer IDs
        if str(interaction.user.id) not in [str(admin.id) for admin in server.admins]:
            await interaction.response.send_message("You don't have permission to set the spawn channel!", ephemeral=True)
            return
            
        # Set spawn channel
        server.spawn_channel_id = str(interaction.channel.id)
        db.commit()
        
        # Send confirmation message
        await interaction.response.send_message(f"✅ Spawn channel has been set to {interaction.channel.mention}!", ephemeral=False)
        
    @discord.ui.button(label="Manage Permissions", style=discord.ButtonStyle.danger, emoji="🔒")
    async def manage_permissions(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if server is registered
        db = get_db()
        server = db.query(Server).filter(Server.id == str(interaction.guild.id)).first()
        
        if not server:
            await interaction.response.send_message("This server is not registered! Please register the server first.", ephemeral=True)
            return
            
        # Check if user is admin - compare string IDs instead of integer IDs
        if str(interaction.user.id) not in [str(admin.id) for admin in server.admins]:
            await interaction.response.send_message("You don't have permission to manage permissions!", ephemeral=True)
            return
            
        # Send permissions management message
        message = (
            "**Command Permissions Management**\n\n"
            "Use the following commands to manage command permissions:\n\n"
            "`!perm allow <command> <channel>` - Allow a command in a channel\n"
            "`!perm deny <command> <channel>` - Deny a command in a channel\n"
            "`!perm allow_role <command> <role>` - Allow a role to use a command\n"
            "`!perm deny_role <command> <role>` - Deny a role from using a command\n"
            "`!perm list` - List all command permissions"
        )
        
        await interaction.response.send_message(message, ephemeral=False)

class Setup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command(name="setup")
    async def setup(self, ctx):
        """Setup command for server and user registration."""
        view = SetupView(self.bot)
        await ctx.send("Welcome to Taipu Bot! Use the buttons below to set up the bot for your server.", view=view)
        
    @commands.command(name="register")
    async def register(self, ctx):
        """Register yourself to start collecting cards."""
        # Check if user is already registered
        db = get_db()
        user = db.query(User).filter(User.id == str(ctx.author.id)).first()
        
        if user:
            await ctx.send(f"✅ User **{ctx.author.name}** is already registered! Your data is safe.")
            return
            
        # Register user
        user = User(
            id=str(ctx.author.id),
            username=ctx.author.name,
            join_date=datetime.datetime.utcnow()
        )
        db.add(user)
        db.commit()
        
        await ctx.send(f"✅ User **{ctx.author.name}** has been registered successfully!")
        
    @commands.command(name="registerserver")
    @commands.has_permissions(administrator=True)
    async def register_server(self, ctx):
        """Register your server to use Taipu Bot."""
        # Check if server is already registered
        db = get_db()
        server = db.query(Server).filter(Server.id == str(ctx.guild.id)).first()
        
        if server:
            await ctx.send(f"✅ Server **{ctx.guild.name}** is already registered!")
            return
            
        # Register server
        server = Server(
            id=str(ctx.guild.id),
            name=ctx.guild.name,
            registration_time=datetime.datetime.utcnow()
        )
        db.add(server)
        
        # Add admin (command user)
        user = db.query(User).filter(User.id == str(ctx.author.id)).first()
        if not user:
            user = User(
                id=str(ctx.author.id),
                username=ctx.author.name,
                join_date=datetime.datetime.utcnow()
            )
            db.add(user)
            
        server.add_admin(user)
        db.commit()
        
        await ctx.send(f"✅ Server **{ctx.guild.name}** has been registered successfully with admin {ctx.author.mention}!")
        
    @commands.command(name="setspawnchannel")
    @commands.has_permissions(administrator=True)
    async def set_spawn_channel(self, ctx):
        """Set the channel where cards will spawn."""
        # Check if server is registered
        db = get_db()
        server = db.query(Server).filter(Server.id == str(ctx.guild.id)).first()
        
        if not server:
            await ctx.send("This server is not registered! Please register the server first.")
            return
            
        # Set spawn channel
        server.spawn_channel_id = str(ctx.channel.id)
        db.commit()
        
        await ctx.send(f"✅ Spawn channel has been set to {ctx.channel.mention}!")
        
    @commands.group(name="perm")
    @commands.has_permissions(administrator=True)
    async def perm(self, ctx):
        """Manage command permissions for your server."""
        if ctx.invoked_subcommand is None:
            await ctx.send("Invalid permission command. Use `!perm list` to see all permissions.")
            
    @perm.command(name="allow")
    async def perm_allow(self, ctx, command: str, channel: discord.TextChannel):
        """Allow a command in a channel."""
        # Check if server is registered
        db = get_db()
        server = db.query(Server).filter(Server.id == str(ctx.guild.id)).first()
        
        if not server:
            await ctx.send("This server is not registered! Please register the server first.")
            return
            
        # Set command permission
        server.set_command_permission(command, "channel", [str(channel.id)], allow=True)
        db.commit()
        
        await ctx.send(f"Command `{command}` is now allowed in {channel.mention}!")
        
    @perm.command(name="deny")
    async def perm_deny(self, ctx, command: str, channel: discord.TextChannel):
        """Deny a command in a channel."""
        # Check if server is registered
        db = get_db()
        server = db.query(Server).filter(Server.id == str(ctx.guild.id)).first()
        
        if not server:
            await ctx.send("This server is not registered! Please register the server first.")
            return
            
        # Set command permission
        server.set_command_permission(command, "channel", [str(channel.id)], allow=False)
        db.commit()
        
        await ctx.send(f"Command `{command}` is now denied in {channel.mention}!")
        
    @perm.command(name="allow_role")
    async def perm_allow_role(self, ctx, command: str, role: discord.Role):
        """Allow a role to use a command."""
        # Check if server is registered
        db = get_db()
        server = db.query(Server).filter(Server.id == str(ctx.guild.id)).first()
        
        if not server:
            await ctx.send("This server is not registered! Please register the server first.")
            return
            
        # Set command permission
        server.set_command_permission(command, "role", [str(role.id)], allow=True)
        db.commit()
        
        await ctx.send(f"Command `{command}` is now allowed for role {role.mention}!")
        
    @perm.command(name="deny_role")
    async def perm_deny_role(self, ctx, command: str, role: discord.Role):
        """Deny a role from using a command."""
        # Check if server is registered
        db = get_db()
        server = db.query(Server).filter(Server.id == str(ctx.guild.id)).first()
        
        if not server:
            await ctx.send("This server is not registered! Please register the server first.")
            return
            
        # Set command permission
        server.set_command_permission(command, "role", [str(role.id)], allow=False)
        db.commit()
        
        await ctx.send(f"Command `{command}` is now denied for role {role.mention}!")
        
    @perm.command(name="list")
    async def perm_list(self, ctx):
        """List all command permissions."""
        # Check if server is registered
        db = get_db()
        server = db.query(Server).filter(Server.id == str(ctx.guild.id)).first()
        
        if not server:
            await ctx.send("This server is not registered! Please register the server first.")
            return
            
        # Get command permissions
        perms = server.command_permissions
        
        if not perms:
            await ctx.send("No command permissions set for this server.")
            return
            
        # Create a channel-centric view of permissions
        channel_perms = {}
        role_perms = {}
        
        for command, perm in perms.items():
            # Process channel permissions
            for channel_id in perm.get("allowed_channels", []):
                if channel_id not in channel_perms:
                    channel_perms[channel_id] = {"allowed": [], "denied": []}
                channel_perms[channel_id]["allowed"].append(command)
                
            for channel_id in perm.get("denied_channels", []):
                if channel_id not in channel_perms:
                    channel_perms[channel_id] = {"allowed": [], "denied": []}
                channel_perms[channel_id]["denied"].append(command)
                
            # Process role permissions
            for role_id in perm.get("allowed_roles", []):
                if role_id not in role_perms:
                    role_perms[role_id] = {"allowed": [], "denied": []}
                role_perms[role_id]["allowed"].append(command)
                
            for role_id in perm.get("denied_roles", []):
                if role_id not in role_perms:
                    role_perms[role_id] = {"allowed": [], "denied": []}
                role_perms[role_id]["denied"].append(command)
        
        # Create embed for channel permissions
        embed = discord.Embed(
            title="Channel Command Permissions",
            description="Shows which commands are allowed or denied in each channel.",
            color=discord.Color.blue()
        )
        
        for channel_id, commands in channel_perms.items():
            channel = ctx.guild.get_channel(int(channel_id))
            channel_name = channel.mention if channel else f"Unknown Channel ({channel_id})"
            
            value = ""
            if commands["allowed"]:
                value += f"**Allowed Commands:** {', '.join(commands['allowed'])}\n"
            if commands["denied"]:
                value += f"**Denied Commands:** {', '.join(commands['denied'])}\n"
                
            embed.add_field(name=channel_name, value=value or "No permissions set", inline=False)
            
        await ctx.send(embed=embed)
        
        # Create embed for role permissions
        if role_perms:
            role_embed = discord.Embed(
                title="Role Command Permissions",
                description="Shows which commands are allowed or denied for each role.",
                color=discord.Color.green()
            )
            
            for role_id, commands in role_perms.items():
                role = ctx.guild.get_role(int(role_id))
                role_name = role.mention if role else f"Unknown Role ({role_id})"
                
                value = ""
                if commands["allowed"]:
                    value += f"**Allowed Commands:** {', '.join(commands['allowed'])}\n"
                if commands["denied"]:
                    value += f"**Denied Commands:** {', '.join(commands['denied'])}\n"
                    
                role_embed.add_field(name=role_name, value=value or "No permissions set", inline=False)
                
            await ctx.send(embed=role_embed)

async def setup(bot):
    await bot.add_cog(Setup(bot))