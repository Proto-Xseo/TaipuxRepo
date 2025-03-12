import os
import json
import math
import random
import requests
import asyncio
import functools
from io import BytesIO
from PIL import Image, ImageOps
from discord.ext import commands
from concurrent.futures import ThreadPoolExecutor
import discord
# Set to 8 threads for optimal performance
executor = ThreadPoolExecutor(max_workers=8)

def load_characters():
    characters = {}
    base_dir = "DiscordBot/assets/characters/"
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith(".json"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        # Allow both dicts (with "id" and "name") and nested dicts
                        if isinstance(data, dict) and "id" in data and "name" in data:
                            key = data["name"].strip().lower()
                            characters[key] = data
                        else:
                            for key, value in data.items():
                                characters[key.strip().lower()] = value
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
    return characters

def initialize_wishlist_counts():
    """Initialize wishlist counts for all characters"""
    from utils.db import load_db 
    user_data = load_db()
    wishlist_counts = {}
    for user_id, data in user_data.items():
        wishlist = data.get("wishlist", [])
        for character in wishlist:
            char_key = character.strip().lower()
            wishlist_counts[char_key] = wishlist_counts.get(char_key, 0) + 1
    for char_key, count in wishlist_counts.items():
        if char_key in ALL_CHARACTERS:
            ALL_CHARACTERS[char_key]["wishlists"] = count
    for char_data in ALL_CHARACTERS.values():
        if "wishlists" not in char_data or char_data["wishlists"] == "N/A":
            char_data["wishlists"] = 0
    print(f"Initialized wishlist counts for {len(wishlist_counts)} characters")

# Load characters and initialize wishlist counts
ALL_CHARACTERS = load_characters()
try:
    initialize_wishlist_counts()
except Exception as e:
    print(f"Error initializing wishlist counts: {e}")

# Asynchronous image fetching with thread pool
async def fetch_image(url, session=None):
    """Fetch an image from a URL and return it as a PIL Image in RGBA mode"""
    try:
        if session:
            async with session.get(url, timeout=15) as response:
                if response.status != 200:
                    return None
                image_data = await response.read()
        else:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                executor,
                functools.partial(requests.get, url, timeout=10)
            )
            if response.status_code != 200:
                return None
            image_data = response.content
        # Open image using PIL in a thread so as not to block the loop
        image = await asyncio.get_running_loop().run_in_executor(
            executor,
            functools.partial(Image.open, BytesIO(image_data))
        )
        return image.convert("RGBA")
    except Exception as e:
        print(f"Error loading image {url}: {e}")
        return None

async def create_collage(image_urls, grid_cols=4, spacing=5, target_width=2400):
    """Create a high-resolution collage for given image URLs"""
    image_tasks = [fetch_image(url) for url in image_urls if url]
    loaded_images = await asyncio.gather(*image_tasks)
    images = [img for img in loaded_images if img]
    if not images:
        blank = Image.new("RGBA", (1200, 800), (0, 0, 0, 0))
        buffer = BytesIO()
        blank.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer.getvalue()
    cols = grid_cols  
    rows = max(math.ceil(len(images) / cols), 1)
    available_width = target_width - (spacing * (cols - 1))
    thumbnail_width = available_width // cols
    aspect_ratio = 2400 / 1440  # ~1.67
    thumbnail_height = int(thumbnail_width * aspect_ratio)
    max_height_per_thumb = 800
    if thumbnail_height > max_height_per_thumb:
        thumbnail_height = max_height_per_thumb
        thumbnail_width = int(thumbnail_height / aspect_ratio)
    total_width = cols * thumbnail_width + (cols - 1) * spacing
    total_height = rows * thumbnail_height + (rows - 1) * spacing
    collage = Image.new("RGBA", (total_width, total_height), (0, 0, 0, 0))
    for idx, img in enumerate(images):
        if idx >= cols * rows:
            break
        row = idx // cols
        col = idx % cols
        x_position = col * (thumbnail_width + spacing)
        y_position = row * (thumbnail_height + spacing)
        thumb = img.resize((thumbnail_width, thumbnail_height), Image.Resampling.LANCZOS)
        collage.paste(thumb, (x_position, y_position), thumb)
    buffer = BytesIO()
    collage.save(buffer, format="PNG", quality=95, optimize=True)
    buffer.seek(0)
    return buffer.getvalue()

async def create_collage_with_images(images, grid_cols=4, rows=2, spacing=5, target_width=2400):
    """Create a collage directly from PIL images"""
    if not images:
        blank = Image.new("RGBA", (1200, 800), (0, 0, 0, 0))
        buffer = BytesIO()
        blank.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer.getvalue()
    cols = grid_cols
    available_width = target_width - (spacing * (cols - 1))
    thumbnail_width = available_width // cols
    aspect_ratio = 2400 / 1440  # ~1.67
    thumbnail_height = int(thumbnail_width * aspect_ratio)
    max_height_per_thumb = 800
    if thumbnail_height > max_height_per_thumb:
        thumbnail_height = max_height_per_thumb
        thumbnail_width = int(thumbnail_height / aspect_ratio)
    total_width = cols * thumbnail_width + (cols - 1) * spacing
    total_height = rows * thumbnail_height + (rows - 1) * spacing
    collage = Image.new("RGBA", (total_width, total_height), (0, 0, 0, 0))
    for idx, img in enumerate(images):
        if idx >= cols * rows:
            break
        row = idx // cols
        col = idx % cols
        x_position = col * (thumbnail_width + spacing)
        y_position = row * (thumbnail_height + spacing)
        thumb = img.resize((thumbnail_width, thumbnail_height), Image.Resampling.LANCZOS)
        collage.paste(thumb, (x_position, y_position), thumb)
    buffer = BytesIO()
    collage.save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    return buffer.getvalue()

async def create_collage_pages(image_urls, images_per_page=8, grid_cols=4):
    """Create pages of collages from image URLs"""
    image_tasks = [fetch_image(url) for url in image_urls if url]
    loaded_images = await asyncio.gather(*image_tasks)
    all_images = [img for img in loaded_images if img]
    pages = []
    num_images = len(all_images)
    for i in range(0, num_images, images_per_page):
        page_images = all_images[i:i+images_per_page]
        fixed_rows = 2  # Always 2 rows for consistency
        while len(page_images) < grid_cols * fixed_rows:
            blank_img = Image.new("RGBA", (1440, 2400), (0, 0, 0, 0))
            page_images.append(blank_img)
        collage_data = await create_collage_with_images(page_images, grid_cols, fixed_rows)
        pages.append(collage_data)
    return pages

# ------------------
# UI Components
# ------------------
class LookupNavButton(discord.ui.Button):
    def __init__(self, parent_view, action: str):
        # Map actions to custom emoji icons
        emoji_map = {
            "first": "<:first:1347598533653430443>",
            "prev": "<:prev:1347598835295453346>",
            "next": "<:next:1347642109359816895>",
            "last": "<:last:1347596578751250565>"
        }
        # Use primary style for navigation buttons
        super().__init__(label="", emoji=emoji_map.get(action), style=discord.ButtonStyle.primary, custom_id=action)
        self.parent_view = parent_view
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.parent_view.author:
            return await interaction.response.send_message("Not your session!", ephemeral=True)
        if self.action == "first":
            self.parent_view.current_page = 0
        elif self.action == "prev" and self.parent_view.current_page > 0:
            self.parent_view.current_page -= 1
        elif self.action == "next" and self.parent_view.current_page < len(self.parent_view.page_data) - 1:
            self.parent_view.current_page += 1
        elif self.action == "last":
            self.parent_view.current_page = len(self.parent_view.page_data) - 1
        await self.parent_view.update_message(interaction.message)

class LookupVersionButton(discord.ui.Button):
    def __init__(self, parent_view):
        super().__init__(label="Full Size", style=discord.ButtonStyle.primary)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.parent_view.author:
            return await interaction.response.send_message("Not your session!", ephemeral=True)
        await interaction.response.defer(thinking=False)
        view = LookupFullSizeView(
            self.parent_view.full_images,
            self.parent_view.author,
            self.parent_view.page_data,
            self.parent_view.current_page,
            self.parent_view.char_data
        )
        embed = view.get_embed()
        await interaction.message.edit(embed=embed, attachments=[], view=view)

class LookupCollageView(discord.ui.View):
    def __init__(self, page_data, author, full_images, char_data):
        super().__init__(timeout=180)
        self.page_data = page_data  # List of collage image byte arrays
        self.author = author
        self.current_page = 0
        self.full_images = full_images
        self.char_data = char_data
        # Add navigation buttons in order: First, Prev, Next, Last
        if len(self.page_data) > 1:
            self.add_item(LookupNavButton(self, "first"))
            self.add_item(LookupNavButton(self, "prev"))
            self.add_item(LookupNavButton(self, "next"))
            self.add_item(LookupNavButton(self, "last"))
        self.add_item(LookupVersionButton(self))
    
    def get_embed(self):
        embed = discord.Embed(
            title=f"{self.char_data.get('name', 'Unknown')}",
            description=f"Series: {self.char_data.get('series', 'Unknown')}",
            color=0x7289DA
        )
        embed.add_field(name="Wishlists", value=str(self.char_data.get('wishlists', 0)), inline=True)
        embed.add_field(name="Biggest Simp", value=self.char_data.get('biggest_simp', 'N/A'), inline=True)
        embed.add_field(name="Events", value=self.char_data.get('events', 'N/A'), inline=True)
        primary_url = self.char_data.get("primary_image", {}).get("url")
        if primary_url:
            embed.set_thumbnail(url=primary_url)
        return embed
    
    async def update_message(self, message):
        try:
            file = discord.File(BytesIO(self.page_data[self.current_page]), filename=f"collage_{self.current_page}.png")
            embed = self.get_embed()
            embed.set_image(url=f"attachment://{file.filename}")
            await message.edit(attachments=[file], embed=embed, view=self)
        except Exception as e:
            print(f"Error updating message: {e}")

class VersionNavButton(discord.ui.Button):
    def __init__(self, parent_view, action: str):
        emoji_map = {
            "first": "<:first:1347598533653430443>",
            "prev": "<:prev:1347598835295453346>",
            "next": "<:next:1347642109359816895>",
            "last": "<:last:1347596578751250565>",
            "back": "🔙"
        }
        style = discord.ButtonStyle.danger if action == "back" else discord.ButtonStyle.primary
        super().__init__(label="", emoji=emoji_map.get(action), style=style, custom_id=action)
        self.parent_view = parent_view
        self.action = action

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.parent_view.author:
            return await interaction.response.send_message("Not your session!", ephemeral=True)
        await interaction.response.defer(thinking=False)
        changed = False
        if self.action == "first":
            self.parent_view.current_index = 0
            changed = True
        elif self.action == "prev" and self.parent_view.current_index > 0:
            self.parent_view.current_index -= 1
            changed = True
        elif self.action == "next" and self.parent_view.current_index < len(self.parent_view.images) - 1:
            self.parent_view.current_index += 1
            changed = True
        elif self.action == "last":
            self.parent_view.current_index = len(self.parent_view.images) - 1
            changed = True
        elif self.action == "back":
            view = LookupCollageView(
                self.parent_view.page_data,
                self.parent_view.author,
                self.parent_view.full_images,
                self.parent_view.char_data
            )
            view.current_page = self.parent_view.return_page
            file = discord.File(BytesIO(view.page_data[view.current_page]), filename=f"collage_{view.current_page}.png")
            embed = view.get_embed()
            embed.set_image(url=f"attachment://{file.filename}")
            await interaction.message.edit(attachments=[file], embed=embed, view=view)
            return
        if changed:
            embed = self.parent_view.get_embed()
            await interaction.message.edit(embed=embed)

class LookupFullSizeView(discord.ui.View):
    def __init__(self, images, author, page_data, return_page=0, char_data=None):
        super().__init__(timeout=180)
        self.images = [img for img in images if img]
        self.full_images = images
        self.author = author
        self.page_data = page_data
        self.return_page = return_page
        self.current_index = 0
        self.char_data = char_data
        if self.images:
            self.add_item(VersionNavButton(self, "first"))
            self.add_item(VersionNavButton(self, "prev"))
            self.add_item(VersionNavButton(self, "next"))
            self.add_item(VersionNavButton(self, "last"))
        self.add_item(VersionNavButton(self, "back"))
    
    def get_embed(self):
        if not self.images:
            embed = discord.Embed(
                title=f"{self.char_data.get('name', 'Unknown')}",
                description="No images available",
                color=0x7289DA
            )
            return embed
        embed = discord.Embed(
            title=f"{self.char_data.get('name', 'Unknown')} - Full Size Image",
            description=f"Image {self.current_index+1}/{len(self.images)}",
            color=0x7289DA
        )
        embed.set_image(url=self.images[self.current_index])
        if self.char_data and 'series' in self.char_data:
            embed.set_footer(text=f"Series: {self.char_data.get('series', 'Unknown')}")
        return embed

# Import database modules
from models.base import get_db
from models.series import Series
from models.character import Character, CharacterImage
from utils.db import add_character

# Sample Genshin Impact character data
GENSHIN_CHARACTERS = [
    {
        "name": "Raiden Shogun",
        "description": "The Electro Archon and ruler of Inazuma.",
        "primary_image": {
            "url": "https://static.wikia.nocookie.net/gensin-impact/images/2/24/Character_Raiden_Shogun_Portrait.png"
        },
        "extra_images": [
            {"url": "https://static.wikia.nocookie.net/gensin-impact/images/5/52/Character_Raiden_Shogun_Full_Wish.png"},
            {"url": "https://static.wikia.nocookie.net/gensin-impact/images/c/c6/Character_Raiden_Shogun_Game.png"}
        ]
    },
    {
        "name": "Hu Tao",
        "description": "The 77th Director of the Wangsheng Funeral Parlor.",
        "primary_image": {
            "url": "https://static.wikia.nocookie.net/gensin-impact/images/a/a4/Character_Hu_Tao_Portrait.png"
        },
        "extra_images": [
            {"url": "https://static.wikia.nocookie.net/gensin-impact/images/a/a9/Character_Hu_Tao_Full_Wish.png"},
            {"url": "https://static.wikia.nocookie.net/gensin-impact/images/e/e9/Character_Hu_Tao_Game.png"}
        ]
    },
    {
        "name": "Zhongli",
        "description": "A consultant for the Wangsheng Funeral Parlor and the Geo Archon.",
        "primary_image": {
            "url": "https://static.wikia.nocookie.net/gensin-impact/images/a/a6/Character_Zhongli_Portrait.png"
        },
        "extra_images": [
            {"url": "https://static.wikia.nocookie.net/gensin-impact/images/a/a6/Character_Zhongli_Full_Wish.png"},
            {"url": "https://static.wikia.nocookie.net/gensin-impact/images/7/79/Character_Zhongli_Game.png"}
        ]
    }
]

def add_genshin_impact_series():
    """Add a sample Genshin Impact series to the database."""
    db = get_db()
    
    # Check if series already exists
    series = db.query(Series).filter(Series.name == "Genshin Impact").first()
    if series:
        print("Genshin Impact series already exists.")
        return series
    
    # Create series
    series = Series(
        name="Genshin Impact",
        description="An open-world action RPG developed by miHoYo.",
        image_url="https://static.wikia.nocookie.net/gensin-impact/images/5/53/Genshin_Impact.png",
        release_year=2020,
        genre="Action RPG",
        studio="miHoYo",
        external_links={"official": "https://genshin.hoyoverse.com/", "wiki": "https://genshin-impact.fandom.com/"},
        tags=["rpg", "gacha", "open-world"]
    )
    db.add(series)
    db.flush()  # Get series ID
    
    # Add characters
    for char_data in GENSHIN_CHARACTERS:
        character = Character(
            name=char_data["name"],
            series_id=series.id,
            description=char_data.get("description")
        )
        db.add(character)
        db.flush()  # Get character ID
        
        # Add primary image
        primary_url = char_data.get("primary_image", {}).get("url")
        if primary_url:
            character.add_image(url=primary_url, is_primary=True)
            
        # Add extra images
        for img_data in char_data.get("extra_images", []):
            character.add_image(
                url=img_data.get("url"),
                is_primary=False,
                affection_required=img_data.get("affection_required", 0),
                is_event=img_data.get("is_event", False)
            )
    
    db.commit()
    print(f"Added Genshin Impact series with {len(GENSHIN_CHARACTERS)} characters.")
    return series

class Lookup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Add Genshin Impact series when the cog is loaded
        self.bot.loop.create_task(self.add_genshin_impact())
    
    async def add_genshin_impact(self):
        """Add Genshin Impact series in a non-blocking way."""
        await self.bot.wait_until_ready()
        # Run in executor to avoid blocking the event loop
        await asyncio.get_event_loop().run_in_executor(executor, add_genshin_impact_series)

    @commands.command(name="lookup")
    async def lookup(self, ctx, *, identifier: str):
        initial_message = await ctx.reply("🔍 Searching for character...", mention_author=False)
        key = identifier.strip().lower()
        char_data = None
        if key.isdigit():
            num_key = int(key)
            for data in ALL_CHARACTERS.values():
                if data.get("id") == num_key:
                    char_data = data
                    break
        else:
            char_data = ALL_CHARACTERS.get(key)
        if not char_data:
            await initial_message.edit(content="❌ Character not found, please check the spelling!")
            return
        await initial_message.edit(content=f"✅ Found **{char_data.get('name', 'Unknown')}**!\n⏳ Loading images (1/3)...")
        image_urls = []
        full_images = []
        primary_url = char_data.get("primary_image", {}).get("url")
        if primary_url:
            image_urls.append(primary_url)
            full_images.append(primary_url)
        for img in char_data.get("extra_images", []):
            url = img.get("url")
            if url:
                image_urls.append(url)
                full_images.append(url)
        if not image_urls:
            placeholder = "https://via.placeholder.com/1440x2400"
            image_urls = [placeholder]
            full_images = [placeholder]
        await initial_message.edit(content=f"✅ Found **{char_data.get('name', 'Unknown')}**!\n✅ Found {len(image_urls)} images\n⏳ Creating gallery (2/3)...")
        page_data = await create_collage_pages(image_urls, images_per_page=8, grid_cols=4)
        await initial_message.edit(content=f"✅ Found **{char_data.get('name', 'Unknown')}**!\n✅ Found {len(image_urls)} images\n✅ Created gallery\n⏳ Finalizing (3/3)...")
        file = discord.File(BytesIO(page_data[0]), filename="collage_0.png")
        embed = discord.Embed(
            title=f"{char_data.get('name', 'Unknown')}",
            description=f"Series: {char_data.get('series', 'Unknown')}",
            color=0x7289DA
        )
        wishlist_count = char_data.get('wishlists', 0)
        if isinstance(wishlist_count, str) and wishlist_count == 'N/A':
            wishlist_count = 0
        embed.add_field(name="Wishlists", value=str(wishlist_count), inline=True)
        embed.add_field(name="Biggest Simp", value=char_data.get('biggest_simp', 'N/A'), inline=True)
        embed.add_field(name="Events", value=char_data.get('events', 'N/A'), inline=True)
        if primary_url:
            embed.set_thumbnail(url=primary_url)
        embed.set_image(url=f"attachment://{file.filename}")
        embed.set_footer(text=f"Page 1/{len(page_data)} • {len(full_images)} images")
        view = LookupCollageView(page_data, ctx.author, full_images, char_data)
        await initial_message.edit(content=None, embed=embed, attachments=[file], view=view)

    @commands.command(name="series")
    async def series_lookup(self, ctx, *, series_name: str):
        """Look up information about a series and its characters."""
        initial_message = await ctx.reply("🔍 Searching for series...", mention_author=False)
        
        # Search for series in database
        db = get_db()
        series = db.query(Series).filter(Series.name.ilike(f"%{series_name}%")).first()
        
        if not series:
            await initial_message.edit(content="❌ Series not found, please check the spelling!")
            return
        
        # Get characters in series
        characters = series.characters
        
        if not characters:
            await initial_message.edit(content=f"✅ Found series **{series.name}**, but it has no characters yet.")
            return
        
        # Create embed with series information
        embed = discord.Embed(
            title=f"{series.name}",
            description=series.description or "No description available.",
            color=0x7289DA
        )
        
        # Add series metadata
        if series.release_year:
            embed.add_field(name="Release Year", value=str(series.release_year), inline=True)
        if series.genre:
            embed.add_field(name="Genre", value=series.genre, inline=True)
        if series.studio:
            embed.add_field(name="Studio", value=series.studio, inline=True)
        
        # Add character list
        character_list = "\n".join([f"• {character.name}" for character in characters[:10]])
        if len(characters) > 10:
            character_list += f"\n... and {len(characters) - 10} more"
        embed.add_field(name=f"Characters ({len(characters)})", value=character_list, inline=False)
        
        # Add series image if available
        if series.image_url:
            embed.set_thumbnail(url=series.image_url)
        
        # Add external links if available
        if series.external_links:
            links = []
            for name, url in series.external_links.items():
                links.append(f"[{name.capitalize()}]({url})")
            if links:
                embed.add_field(name="Links", value=" | ".join(links), inline=False)
        
        # Add footer with tags if available
        if series.tags:
            embed.set_footer(text=f"Tags: {', '.join(series.tags)}")
        
        await initial_message.edit(content=None, embed=embed)
        
        # If there are characters, create a collage of their images
        if characters:
            await initial_message.edit(content=f"✅ Found series **{series.name}**\n⏳ Creating character collage...")
            
            # Collect character images
            image_urls = []
            for character in characters[:8]:  # Limit to 8 characters for the collage
                primary_image = character.primary_image
                if primary_image:
                    image_urls.append(primary_image.url)
            
            if image_urls:
                # Create collage
                collage_data = await create_collage(image_urls, grid_cols=4)
                file = discord.File(BytesIO(collage_data), filename="series_collage.png")
                
                # Create new embed with collage
                collage_embed = discord.Embed(
                    title=f"{series.name} Characters",
                    description=f"Here are some characters from {series.name}:",
                    color=0x7289DA
                )
                collage_embed.set_image(url=f"attachment://{file.filename}")
                
                await ctx.send(embed=collage_embed, file=file)

async def setup(bot):
    await bot.add_cog(Lookup(bot))