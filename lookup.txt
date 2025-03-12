import discord
import random
import io
import os
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
from utils.db import get_user, update_user

RARITY_ORDER = {"N": 1, "R": 2, "SR": 3, "SSR": 4, "UR": 5, "LR": 6, "ER": 7}
developer_ids = {816735778339291186, 984783866072039435}

class Profile(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="profile")
    async def profile(self, ctx, member: discord.Member = None):
        if member is None:
            member = ctx.author

        user_data = get_user(member.id)
        if not user_data:
            return await ctx.send("No profile data found. Claim some cards first!")

        cards = user_data.get("cards", [])
        total_cards = len(cards)
        join_date = user_data.get("join_date", "2023-01-01")
        leaderboard_rank = user_data.get("leaderboard_rank", "Unranked")
        badges = ", ".join(user_data.get("badges", ["No badges"]))

        if cards:
            biggest_simp = max(cards, key=lambda c: c.get("affection", 0))
            biggest_simp_name = biggest_simp.get("name", "N/A")
        else:
            biggest_simp_name = "N/A"

        favourite_card = user_data.get("favourite_card")
        if not favourite_card and cards:
            favourite_card = max(cards, key=lambda c: RARITY_ORDER.get(c.get("rarity", "N"), 0))
        showcase_image = favourite_card.get("claimed_artwork", "https://via.placeholder.com/800x600")
        favourite_name = favourite_card.get("name", "None")

        try:
            if member.avatar:
                avatar_bytes = io.BytesIO(await member.avatar.read())
            else:
                avatar_bytes = io.BytesIO()
            avatar_img = Image.open(avatar_bytes).convert("RGBA").resize((100, 100))
        except Exception as e:
            print(f"Error processing avatar: {e}")
            avatar_img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))

        custom_color = user_data.get("profile_color", "#3498db")
        try:
            embed_color = discord.Color(int(custom_color.strip("#"), 16))
        except:
            embed_color = discord.Color.blue()

        embed = discord.Embed(
            title=f"{member.display_name}'s PROFILE",
            description=(
                f"👤 **Username:** {member.name}\n"
                f"📅 **Joined:** {join_date}\n"
                f"📦 **Total Cards:** {total_cards}\n"
                f"🏆 **Leaderboard Rank:** {leaderboard_rank}\n"
                f"💖 **Biggest Simp:** {biggest_simp_name}\n"
                f"🎴 **Showcase Card:** {favourite_name}\n"
                f"🎖️ **Badges:** {badges}\n"
            ),
            color=embed_color
        )
        embed.set_image(url=showcase_image)
        embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
        embed.set_footer(text="Click 🔍 to see statistics!")

        message = await ctx.send(embed=embed)
        await message.add_reaction("🔍")

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == "🔍"

        try:
            reaction, user = await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
            await self.show_statistics(ctx, member, user_data)
        except:
            pass

    async def show_statistics(self, ctx, member, user_data):
        cards = user_data.get("cards", [])
        if not cards:
            return await ctx.send("No cards found!")
        
        rarest_cards = sorted(cards, key=lambda c: RARITY_ORDER.get(c.get("rarity", "N"), 0), reverse=True)[:5]
        stats_description = "\n".join([f"{c['name']} ({c['rarity']})" for c in rarest_cards])
        embed = discord.Embed(title=f"{member.display_name}'s Rarest Cards", description=stats_description, color=discord.Color.gold())
        await ctx.send(embed=embed)

    @commands.command(name="favourite", aliases=["fav", "favorite"])
    async def favourite(self, ctx, card_id: str):
        user_data = get_user(ctx.author.id)
        if not user_data:
            return await ctx.send("No profile data found. Claim some cards first!")

        cards = user_data.get("cards", [])
        fav_card = next((card for card in cards if card.get("global_id") == card_id), None)
        if not fav_card:
            return await ctx.send("Card not found in your collection!")

        user_data["favourite_card"] = fav_card
        update_user(ctx.author.id, "favourite_card", fav_card)
        await ctx.send(f"{ctx.author.mention}, your favourite card is now **{fav_card.get('name', 'Unknown')}**!")

    @commands.command(name="color")
    async def color(self, ctx, action: str, hex_code: str = None):
        user_data = get_user(ctx.author.id)
        if not user_data:
            return await ctx.send("No profile data found. Claim some cards first!")

        if action.lower() == "set":
            if not hex_code or not hex_code.startswith("#") or len(hex_code) not in (4, 7):
                return await ctx.send("Invalid hex code. Use #ABC or #A1B2C3 format.")
            update_user(ctx.author.id, "profile_color", hex_code)
            await ctx.send(f"Your profile color is now {hex_code}!")
        elif action.lower() == "view":
            custom_color = user_data.get("profile_color", "Not set")
            await ctx.send(f"Your current profile color is: {custom_color}")
        else:
            await ctx.send("Invalid action. Use 'set' or 'view'.")

async def setup(bot):
    await bot.add_cog(Profile(bot))
