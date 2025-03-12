import discord
import os
import random
import asyncio
from discord.ext import commands, tasks
from models.base import get_db
from models.server import Server
from models.character import Character
from models.card import Card
from utils.db import get_all_characters, add_card, get_user, update_user

POSSIBLE_RARITIES = ["N", "R", "SR", "SSR", "UR", "LR", "ER"]
RARITY_WEIGHTS = [40, 25, 20, 10, 5, 3, 1]

RARITY_COLORS = {
    "N": 0x8B4513,
    "R": 0x800080,
    "SR": 0xFFA500,
    "SSR": 0xFF6347,
    "UR": 0xFFD700,
    "LR": 0xEE82EE,
    "ER": 0xC0C0C0
}

RARITY_THUMBNAIL_URLS = {
    "N": "https://i.postimg.cc/FKfL95jh/N-rarity.png",
    "R": "https://i.postimg.cc/C50BHR9K/r-rarity.webp",
    "SR": "https://i.postimg.cc/GpZst7QG/EL4-M2u-IXs-AAkx-f.png",
    "SSR": "https://i.postimg.cc/T1cykRXJ/ssr-rarity-1.png",
    "UR": "https://i.postimg.cc/kMNtMytR/UR-Rarity-1.png",
    "LR": "https://i.postimg.cc/PxYvwW3c/EL4-M2a4-Ws-AAd-YIa.png",
    "ER": "https://i.postimg.cc/159V8NpC/ER-icon.png"
}

class Spawn(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.default_spawn_channel_id = int(os.getenv("SPAWN_CHANNEL_ID", 0))
        self.server_spawn_channels = {}  # Guild ID -> Channel ID
        self.currently_spawned = {}  # Guild ID -> Character name
        self.current_rarity = {}  # Guild ID -> Rarity
        self.current_image = {}  # Guild ID -> Image URL
        self.spawn_message = {}  # Guild ID -> Message
        self.load_spawn_channels()
        self.spawn_task.start()
        
    def load_spawn_channels(self):
        """Load spawn channels from the database."""
        db = get_db()
        servers = db.query(Server).all()
        
        for server in servers:
            if server.spawn_channel_id:
                self.server_spawn_channels[int(server.id)] = int(server.spawn_channel_id)
                
        print(f"Loaded {len(self.server_spawn_channels)} spawn channels from database.")

    @tasks.loop(minutes=5)
    async def spawn_task(self):
        """Spawn cards in all registered servers."""
        # Use default spawn channel if no servers are registered
        if not self.server_spawn_channels and self.default_spawn_channel_id:
            channel = self.bot.get_channel(self.default_spawn_channel_id)
            if channel:
                await self.spawn_in_channel(channel)
            return
            
        # Spawn in all registered servers
        for guild_id, channel_id in self.server_spawn_channels.items():
            guild = self.bot.get_guild(guild_id)
            if not guild:
                continue
                
            channel = guild.get_channel(channel_id)
            if not channel:
                try:
                    channel = await self.bot.fetch_channel(channel_id)
                except Exception as e:
                    print(f"[ERROR] Spawn channel not found for guild {guild_id}: {e}")
                    continue
                    
            await self.spawn_in_channel(channel)
            
            # Add a small delay between spawns to avoid rate limits
            await asyncio.sleep(1)
            
    async def spawn_in_channel(self, channel):
        """Spawn a card in a specific channel."""
        guild_id = channel.guild.id
        
        # Random timing variability may occur if errors happen.
        chance = random.random()
        if chance < 0.1:
            await channel.send("🌵 Tumbleweed... nothing here!")
            return
        elif chance > 0.95:
            await channel.send("⚡ Surge Storm activated! Rare waifus are spiking!")
            for _ in range(3):
                rarity_code = random.choice(["SSR", "UR", "LR", "ER"])
                await self.send_spawn(channel, forced_rarity=rarity_code)
            return
            
        teaser = discord.Embed(
            title="Something's coming...",
            description="A mysterious waifu is about to appear...",
            color=0x2F3136
        )
        teaser_msg = await channel.send(embed=teaser)
        await asyncio.sleep(5)
        await teaser_msg.delete()
        await self.send_spawn(channel)

    async def send_spawn(self, channel, forced_rarity=None):
        """Send a spawn message in a channel."""
        guild_id = channel.guild.id
        
        # Get all characters from database
        all_characters = get_all_characters()
        if not all_characters:
            await channel.send("❌ Error: No characters found in database!")
            return
            
        # Select a random character
        character_name = random.choice(list(all_characters.keys()))
        character = all_characters[character_name]
        
        # Select rarity and image
        rarity_code = forced_rarity if forced_rarity else random.choices(POSSIBLE_RARITIES, weights=RARITY_WEIGHTS, k=1)[0]
        embed_color = RARITY_COLORS.get(rarity_code, 0x000000)
        thumbnail_url = RARITY_THUMBNAIL_URLS.get(rarity_code)
        
        # Get free images (no affection required)
        free_images = []
        primary = character.get("primary_image", {}).get("url")
        if primary:
            free_images.append(primary)
        for img in character.get("extra_images", []):
            if img.get("affection_required", 0) == 0:
                free_images.append(img.get("url"))
                
        image_url = random.choice(free_images) if free_images else "https://via.placeholder.com/800"
        
        # Store current spawn info
        self.current_rarity[guild_id] = rarity_code
        self.current_image[guild_id] = image_url
        self.currently_spawned[guild_id] = character_name
        
        # Create embed
        flavor_titles = {
            "N": "A Humble Appearance!",
            "R": "A Regular but Cute Waifu!",
            "SR": "A Stunning Surprise!",
            "SSR": "A Supreme Vision!",
            "UR": "An Ultra Rare Beauty!",
            "LR": "A Legendary Diva!",
            "ER": "An Extremely Rare Goddess!"
        }
        
        embed = discord.Embed(
            title=flavor_titles.get(rarity_code, "A new waifu appears!"),
            description="Claim with `tclaim <name>` for rare cards. For common waifus, react with ✅.",
            color=embed_color
        )
        
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)
        embed.set_image(url=image_url)
        embed.set_footer(text=f"Rarity: {rarity_code}")
        
        try:
            msg = await channel.send(embed=embed)
            self.spawn_message[guild_id] = msg
            
            if rarity_code in ("N", "R"):
                await msg.add_reaction("✅")
                
            # Update server statistics
            db = get_db()
            server = db.query(Server).filter(Server.id == str(guild_id)).first()
            if server:
                server.total_spawns += 1
                db.commit()
                
        except Exception as e:
            print(f"[ERROR] Failed to send spawn message: {e}")
            self.currently_spawned[guild_id] = None

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Handle reaction-based claims for common cards."""
        if user.bot:
            return
            
        guild_id = reaction.message.guild.id
        
        # Check if this is a spawn message
        if guild_id not in self.spawn_message or reaction.message.id != self.spawn_message[guild_id].id:
            return
            
        # Check if the reaction is the claim reaction
        if str(reaction.emoji) != "✅":
            return
            
        # Check if the card is claimable by reaction
        if guild_id not in self.current_rarity or self.current_rarity[guild_id] not in ("N", "R"):
            return
            
        # Get character info
        spawned_name = self.currently_spawned[guild_id]
        if not spawned_name:
            await reaction.message.channel.send("❌ Error: No character is currently spawned!")
            return
            
        # Get all characters
        all_characters = get_all_characters()
        if spawned_name not in all_characters:
            await reaction.message.channel.send("❌ Error: Spawned character not found!")
            return
            
        character_info = all_characters[spawned_name]
        
        # Add card to user's collection
        db = get_db()
        
        # Get character from database
        character = db.query(Character).filter(Character.name == spawned_name).first()
        if not character:
            await reaction.message.channel.send("❌ Error: Character not found in database!")
            return
            
        # Create card
        card = add_card(
            user_id=str(user.id),
            character_id=character.id,
            rarity=self.current_rarity[guild_id],
            claimed_artwork=self.current_image[guild_id],
            claim_method="spawn"
        )
        
        if not card:
            await reaction.message.channel.send("❌ Error: Failed to create card!")
            return
            
        # Update server statistics
        server = db.query(Server).filter(Server.id == str(guild_id)).first()
        if server:
            server.total_claims += 1
            db.commit()
            
        # Send success message
        await reaction.message.channel.send(
            f"🌟 {user.mention}, you claimed **[{self.current_rarity[guild_id]}] {spawned_name}**! (Global ID: {card.global_id})"
        )
        
        # Update spawn message
        try:
            embed = self.spawn_message[guild_id].embeds[0]
            embed.add_field(name="Status", value=f"Claimed by {user.mention}", inline=False)
            await self.spawn_message[guild_id].edit(embed=embed)
        except Exception as e:
            print(f"[ERROR] Failed to update spawn embed: {e}")
            
        # Reset spawn info
        self.currently_spawned[guild_id] = None
        self.current_rarity[guild_id] = None
        self.current_image[guild_id] = None
        
    @commands.command(name="spawnhere")
    @commands.has_permissions(administrator=True)
    async def spawn_here(self, ctx):
        """Set the current channel as the spawn channel for this server."""
        guild_id = ctx.guild.id
        channel_id = ctx.channel.id
        
        # Update database
        db = get_db()
        server = db.query(Server).filter(Server.id == str(guild_id)).first()
        
        if not server:
            # Create server if it doesn't exist
            server = Server(
                id=str(guild_id),
                name=ctx.guild.name,
                spawn_channel_id=str(channel_id)
            )
            db.add(server)
        else:
            server.spawn_channel_id = str(channel_id)
            
        db.commit()
        
        # Update local cache
        self.server_spawn_channels[guild_id] = channel_id
        
        await ctx.send(f"✅ Spawn channel set to {ctx.channel.mention}!")

async def setup(bot):
    await bot.add_cog(Spawn(bot))
