import discord
import random
import string
from discord.ext import commands
from models.base import get_db
from models.character import Character
from models.server import Server
from utils.db import get_all_characters, add_card, get_user

def generate_global_id():
    """Generate a unique global ID for a card."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=7))

class Claim(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="claim")
    async def claim_character(self, ctx, *, card_name: str):
        """Claim a spawned character by name."""
        # Get spawn cog
        spawn_cog = self.bot.get_cog("Spawn")
        if not spawn_cog:
            await ctx.send("❌ Spawn system is not available!")
            return
            
        # Check if a character is spawned in this guild
        guild_id = ctx.guild.id
        if guild_id not in spawn_cog.currently_spawned or not spawn_cog.currently_spawned[guild_id]:
            await ctx.send("❌ No character is currently spawned!")
            return
            
        # Check if the name matches
        user_input = card_name.strip().lower()
        spawned_name = spawn_cog.currently_spawned[guild_id].strip().lower()
        if user_input != spawned_name:
            await ctx.send("❌ That's not the spawned character!")
            return
            
        # Check if the rarity is claimable by command
        if guild_id in spawn_cog.current_rarity and spawn_cog.current_rarity[guild_id] in ("N", "R"):
            await ctx.send("❌ For common waifus, please claim by reacting!")
            return
            
        # Get character info
        all_characters = get_all_characters()
        matched_key = None
        for key in all_characters:
            if key.strip().lower() == spawned_name:
                matched_key = key
                break
                
        if not matched_key:
            await ctx.send("❌ Error: Spawned character not found!")
            return
            
        character_info = all_characters[matched_key]
        
        # Get character from database
        db = get_db()
        character = db.query(Character).filter(Character.name == matched_key).first()
        
        if not character:
            await ctx.send("❌ Error: Character not found in database!")
            return
            
        # Create card
        claimed_image = spawn_cog.current_image[guild_id] if guild_id in spawn_cog.current_image else character_info.get("primary_image", {}).get("url", "https://via.placeholder.com/300")
        
        card = add_card(
            user_id=str(ctx.author.id),
            character_id=character.id,
            rarity=spawn_cog.current_rarity[guild_id],
            claimed_artwork=claimed_image,
            claim_method="spawn"
        )
        
        if not card:
            await ctx.send("❌ Error: Failed to create card!")
            return
            
        # Update server statistics
        server = db.query(Server).filter(Server.id == str(guild_id)).first()
        if server:
            server.total_claims += 1
            db.commit()
            
        # Send success message
        await ctx.send(f"🌟 {ctx.author.mention}, you claimed **[{spawn_cog.current_rarity[guild_id]}] {matched_key}**! (Global ID: {card.global_id})")
        
        # Update spawn message
        try:
            if guild_id in spawn_cog.spawn_message:
                embed = spawn_cog.spawn_message[guild_id].embeds[0]
                embed.add_field(name="Status", value=f"Claimed by {ctx.author.mention}", inline=False)
                await spawn_cog.spawn_message[guild_id].edit(embed=embed)
                
                # Reset spawn info
                spawn_cog.currently_spawned[guild_id] = None
                spawn_cog.current_rarity[guild_id] = None
                spawn_cog.current_image[guild_id] = None
        except Exception as e:
            print(f"[ERROR] Updating spawn embed: {e}")

async def setup(bot):
    await bot.add_cog(Claim(bot))