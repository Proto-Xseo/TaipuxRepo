import discord
from discord.ext import commands
import os
import json
import random

def load_characters():
    characters = {}
    base_dir = "assets/characters/"
    import os
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
    return characters

ALL_CHARACTERS = load_characters()

class Archive(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="card")
    async def view_archive_card(self, ctx, identifier: str):
        card_found = None
        try:
            global_id = int(identifier)
            for card in ALL_CHARACTERS.values():
                if card.get("id") == global_id:
                    card_found = card
                    break
        except ValueError:
            for key, card in ALL_CHARACTERS.items():
                if key.lower() == identifier.lower():
                    card_found = card
                    break
        if not card_found:
            return await ctx.send("Read properly, blind man! That card doesn't exist.")
        image_url = card_found.get("primary_image", {}).get("url") or card_found.get("image", "https://via.placeholder.com/300")
        images = [image_url]
        for img in card_found.get("extra_images", []):
            url = img.get("url")
            if url:
                images.append(url)
        if not images:
            images.append("https://via.placeholder.com/300")
        description = (
            f"**Card Name:** {card_found.get('name', 'Unknown')}\n"
            f"**Archive ID:** {card_found.get('id', 'N/A')}\n"
            f"**Rarity:** {card_found.get('rarity', 'N/A')}\n"
            f"**Series:** {card_found.get('series', 'Unknown Series')}\n"
            "(Other details can be added here)"
        )
        embed = discord.Embed(title=f"{card_found.get('name', 'Card')} Archive Details", description=description, color=discord.Color.gold())
        embed.set_image(url=images[0])
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Archive(bot))