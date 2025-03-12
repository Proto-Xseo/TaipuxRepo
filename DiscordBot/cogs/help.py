import discord
import random
import io
import colorsys
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
from utils.db import get_user, update_user

# Define rarity mapping (lowest to highest)
RARITY_ORDER = {"N": 1, "R": 2, "SR": 3, "SSR": 4, "UR": 5, "LR": 6, "ER": 7}

def get_profile_rank(card_count: int) -> tuple:
    """
    Determine the user's rank based on the number of cards.
    Returns a tuple: (rank_name, threshold_for_this_rank)
    """
    if card_count < 19:
        return ("Beginner", 19)
    elif card_count < 100:
        return ("Mediocre", 100)
    elif card_count < 500:
        return ("Simp", 500)
    elif card_count < 800:
        return ("Ultra Simper", 800)
    else:
        return ("Legendary", 800)

def generate_rainbow_text_image(text: str, font_path="arial.ttf", font_size=48) -> discord.File:
    """
    Generate an image of the given text with each letter in a different rainbow color.
    Returns a discord.File object containing the PNG image.
    """
    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception:
        font = ImageFont.load_default()
    # Calculate width for each letter and overall image size.
    widths = [font.getsize(letter)[0] for letter in text]
    total_width = sum(widths)
    height = font.getsize(text)[1]
    image = Image.new("RGBA", (total_width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    x = 0
    for i, letter in enumerate(text):
        # Cycle hue across letters for a rainbow effect.
        hue = i / max(len(text) - 1, 1)
        r, g, b = [int(c * 255) for c in colorsys.hls_to_rgb(hue, 0.5, 1)]
        draw.text((x, 0), letter, font=font, fill=(r, g, b, 255))
        x += widths[i]
    image_binary = io.BytesIO()
    image.save(image_binary, format="PNG")
    image_binary.seek(0)
    return discord.File(fp=image_binary, filename="rank.png")

class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="profile")
    async def profile(self, ctx):
        user_data = get_user(ctx.author.id)
        if not user_data:
            await ctx.send("No profile data found, please claim some cards first!")
            return

        # Retrieve card collection from user data.
        cards = user_data.get("cards", [])
        card_count = len(cards)
        rank, threshold = get_profile_rank(card_count)
        join_date = user_data.get("join_date", "2023-01-01")
        leaderboard_rank = user_data.get("leaderboard_rank", "Unranked")
        badges = ", ".join(user_data.get("badges", ["No badges"]))

        # Determine biggest simp (card with highest affection)
        if cards:
            biggest_simp = max(cards, key=lambda c: c.get("affection", 0))
            biggest_simp_name = biggest_simp.get("name", "N/A")
        else:
            biggest_simp_name = "N/A"

        # Determine the showcase card: use user's favourite if set; otherwise, pick highest rarity.
        favourite_card = user_data.get("favourite_card")
        if not favourite_card and cards:
            favourite_card = max(cards, key=lambda c: RARITY_ORDER.get(c.get("rarity", "N"), 0))
        favourite_image = (
            favourite_card.get("claimed_artwork")
            if favourite_card and favourite_card.get("claimed_artwork")
            else "https://via.placeholder.com/300"
        )
        favourite_name = favourite_card.get("name") if favourite_card else "None"

        # Use custom profile color if set; else random.
        custom_color = user_data.get("profile_color")
        if custom_color:
            try:
                color_value = int(custom_color.strip("#"), 16)
                embed_color = discord.Color(color_value)
            except Exception:
                embed_color = discord.Color.random()
        else:
            embed_color = discord.Color.random()

        # Check if the user is a developer; if so, use custom rainbow text.
        developer_ids = {816735778339291186, 984783866072039435}
        if ctx.author.id in developer_ids:
            rank_text = "Developer"
        else:
            rank_text = rank

        # Generate the rainbow rank text image.
        rank_file = generate_rainbow_text_image(rank_text)

        # Build the profile embed.
        embed = discord.Embed(
            title=f"{ctx.author.display_name}'s PROFILE",
            description=(
                f"**Username:** {ctx.author.name}\n"
                f"**Joined:** {join_date}\n"
                f"**Total Cards:** {card_count}\n"
                f"**Leaderboard Rank:** {leaderboard_rank}\n"
                f"**Badges:** {badges}\n"
                f"**Biggest Simp:** {biggest_simp_name}\n"
                f"**Showcase Card:** {favourite_name}\n"
                f"**Rank:** {rank} (Level: {threshold} cards)"
            ),
            color=embed_color
        )
        # Attach the rainbow rank image as the main image.
        embed.set_image(url="attachment://rank.png")
        # Set the user's favourite card image as the thumbnail (right-hand side).
        embed.set_thumbnail(url=favourite_image)
        embed.set_footer(text="Keep collecting to level up your profile!")

        await ctx.send(file=rank_file, embed=embed)

    @commands.command(name="favourite")
    async def favourite(self, ctx, card_id: str):
        """
        Set a card as your favourite (showcase) card.
        Usage: !favourite <card_global_id>
        """
        user_data = get_user(ctx.author.id)
        if not user_data:
            await ctx.send("No profile data found, please claim some cards first!")
            return

        cards = user_data.get("cards", [])
        fav_card = None
        for card in cards:
            if card.get("global_id") == card_id:
                fav_card = card
                break

        if not fav_card:
            await ctx.send("Card not found in your collection!")
            return

        user_data["favourite_card"] = fav_card
        update_user(ctx.author.id, "favourite_card", fav_card)
        await ctx.send(f"{ctx.author.mention}, your favourite card has been set to **{fav_card.get('name', 'Unknown')}**!")

    @commands.command(name="color")
    async def color(self, ctx, action: str, hex_code: str = None):
        """
        Set or view your profile color.
        Usage: !color set <hex_code>  |  !color view
        """
        user_data = get_user(ctx.author.id)
        if not user_data:
            await ctx.send("No profile data found, please claim some cards first!")
            return

        if action.lower() == "set":
            if not hex_code:
                await ctx.send("Please provide a hex code. Example: !color set #FF5733")
                return
            if not hex_code.startswith("#") or len(hex_code) not in (4, 7):
                await ctx.send("Invalid hex code format. Please use a format like #ABC or #A1B2C3.")
                return
            user_data["profile_color"] = hex_code
            update_user(ctx.author.id, "profile_color", hex_code)
            await ctx.send(f"{ctx.author.mention}, your profile color has been updated to {hex_code}!")
        elif action.lower() == "view":
            custom_color = user_data.get("profile_color", "Not set")
            await ctx.send(f"{ctx.author.mention}, your current profile color is: {custom_color}")
        else:
            await ctx.send("Invalid action. Use 'set' or 'view'.")

async def setup(bot):
    await bot.add_cog(Profile(bot))
