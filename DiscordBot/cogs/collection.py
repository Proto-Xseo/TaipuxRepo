import discord
import os
import json
import random
import asyncio
from discord.ext import commands
from utils.db import get_user, update_user

def load_characters():
    characters = {}
    base_dir = "DiscordBot/assets/characters/"
    print(f"Loading characters from {base_dir}")
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".json"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r") as f:
                        data = json.load(f)
                        characters.update(data)
                        print(f"Loaded: {file_path}")
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
    print(f"Total characters loaded: {len(characters)}")
    return characters

ALL_CHARACTERS = load_characters()

def format_card_line(card, position=None):
    # Optionally add emoji for rarity (customize these as you wish)
    rarity_emojis = {
        "UR": "🌟",
        "SSR": "💎",
        "SR": "🔥",
        "R": "✨",
        "N": "🔰"
    }
    rarity = card.get("rarity", "N")
    emoji = rarity_emojis.get(rarity.upper(), "")
    # If the card is marked as favorite, show a star
    fav = "⭐ " if card.get("favorite", False) else ""
    # Use position if provided, otherwise fall back to original order
    display_number = position if position is not None else card.get('order', '?')
    return f"`{display_number}` {emoji} {fav}{card.get('name', 'Unknown')} • [ID: {card.get('global_id','N/A')}]"

# Updated rarity order: highest to lowest (UR highest)
RARITY_ORDER = {"N": 1, "R": 2, "SR": 3, "SSR": 4, "UR": 5}

def sort_cards(cards, criteria):
    # Note: Make sure the criteria string matches the labels in the select
    if criteria == "🔢 Default":
        return sorted(cards, key=lambda c: c.get("order", 0))
    elif criteria == "💖 Wishlist":
        return sorted(cards, key=lambda c: (not c.get("wishlist", False), c.get("order", 0)))
    elif criteria == "🔥 Rarity":
        # Highest rarity first
        return sorted(cards, key=lambda c: RARITY_ORDER.get(c.get("rarity", "N"), 0), reverse=True)
    elif criteria == "🔤 Alphabetical":
        return sorted(cards, key=lambda c: c.get("name", "").lower())
    elif criteria == "❤️ Affection":
        return sorted(cards, key=lambda c: c.get("affection", 0), reverse=True)
    elif criteria == "✨ Ascension":
        return sorted(cards, key=lambda c: c.get("ascension", RARITY_ORDER.get(c.get("rarity", "N"), 0)))
    elif criteria == "🎉 Event":
        return sorted(cards, key=lambda c: (not c.get("event", False), c.get("order", 0)))
    return cards

class CollectionSortSelect(discord.ui.Select):
    def __init__(self, parent_view):
        options = [
            discord.SelectOption(label="🔢 Default", description="Sort by claim order"),
            discord.SelectOption(label="💖 Wishlist", description="Sort by wishlist status"),
            discord.SelectOption(label="🔥 Rarity", description="Sort by rarity (highest to lowest)"),
            discord.SelectOption(label="🔤 Alphabetical", description="Sort by card name"),
            discord.SelectOption(label="❤️ Affection", description="Sort by affection (desc)"),
            discord.SelectOption(label="✨ Ascension", description="Sort by ascension"),
            discord.SelectOption(label="🎉 Event", description="Sort by event cards")
        ]
        super().__init__(placeholder="Sort by...", min_values=1, max_values=1, options=options)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.sort_option = self.values[0]
        sorted_cards = sort_cards(self.parent_view.original_cards, self.parent_view.sort_option)
        self.parent_view.pages = [sorted_cards[i:i + self.parent_view.items_per_page]
                                  for i in range(0, len(sorted_cards), self.parent_view.items_per_page)]
        self.parent_view.current_page = 0
        await self.parent_view.update_message(interaction)

class CollectionButton(discord.ui.Button):
    def __init__(self, emoji, parent_view, action):
        super().__init__(emoji=emoji, style=discord.ButtonStyle.primary)
        self.parent_view = parent_view
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.parent_view.author:
            await interaction.response.send_message("This isn't your collection!", ephemeral=True)
            return
        if self.action == "first":
            self.parent_view.current_page = 0
        elif self.action == "prev" and self.parent_view.current_page > 0:
            self.parent_view.current_page -= 1
        elif self.action == "next" and self.parent_view.current_page < len(self.parent_view.pages) - 1:
            self.parent_view.current_page += 1
        elif self.action == "last":
            self.parent_view.current_page = len(self.parent_view.pages) - 1
        await self.parent_view.update_message(interaction)

class CollectionView(discord.ui.View):
    def __init__(self, cards, author: discord.Member):
        super().__init__(timeout=120)
        self.author = author
        # Default sort by claim order
        self.sort_option = "🔢 Default"
        self.original_cards = cards
        self.sorted_cards = sort_cards(cards, self.sort_option)
        self.items_per_page = 10  # Adjust per your design
        self.pages = [self.sorted_cards[i:i + self.items_per_page]
                      for i in range(0, len(self.sorted_cards), self.items_per_page)]
        self.current_page = 0
        # Add the sort select dropdown
        self.add_item(CollectionSortSelect(self))
        if len(self.pages) > 1:
            self.add_item(CollectionButton("<:first:1347598533653430443>", self, "first"))
            self.add_item(CollectionButton("<:prev:1347598835295453346>", self, "prev"))
            self.add_item(CollectionButton("<:next:1347642109359816895>", self, "next"))
            self.add_item(CollectionButton("<:last:1347596578751250565>", self, "last"))


    def get_embed(self):
        if not self.pages:
            desc = "Your collection is empty!"
        else:
            # Calculate the starting position for the current page
            start_position = self.current_page * self.items_per_page + 1
            # Format each card line with its position and join them with line breaks
            desc = "\n".join(format_card_line(card, start_position + i) 
                            for i, card in enumerate(self.pages[self.current_page]))
        embed = discord.Embed(
            title=f"{self.author.display_name}'s Collection",
            description=desc,
            color=discord.Color.from_rgb(88, 101, 242)  # Modern blurple color
        )
        embed.set_footer(text=f"Page {self.current_page + 1}/{len(self.pages)} • Sorted by: {self.sort_option} • Total Cards: {len(self.original_cards)}")
        return embed

    async def update_message(self, interaction: discord.Interaction):
        embed = self.get_embed()
        await interaction.response.edit_message(embed=embed, view=self)

class Collection(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="collection")
    async def collection(self, ctx):
        user_data = get_user(ctx.author.id)
        if "cards" not in user_data and "characters" in user_data:
            user_data["cards"] = user_data["characters"]
            update_user(ctx.author.id, "cards", user_data["cards"])
        if not user_data or "cards" not in user_data or not user_data["cards"]:
            await ctx.send("Your collection is empty!")
            return
        cards = user_data["cards"]
        view = CollectionView(cards, ctx.author)
        embed = view.get_embed()
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Collection(bot))
