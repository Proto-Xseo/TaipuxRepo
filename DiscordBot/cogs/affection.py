import discord
import random
from discord.ext import commands
from utils.db import get_user, update_user

class Affection(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _apply_affection(self, user_id: int, card_id: str, increase: int) -> tuple:
        """
        Increase the affection score of a card by the given amount.
        Returns a tuple (card_name, new_affection) or (None, None) if card not found.
        """
        user_data = get_user(user_id)
        if "cards" not in user_data or not user_data["cards"]:
            return None, None

        card_found = None
        for card in user_data["cards"]:
            if card["global_id"] == card_id:
                card_found = card
                break

        if not card_found:
            return None, None

        # Increase affection (you can add randomness or fixed value)
        card_found["affection"] += increase
        update_user(user_id, "cards", user_data["cards"])
        return card_found["name"], card_found["affection"]

    @commands.command(name="flirt")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def flirt(self, ctx, card_id: str):
        """
        Flirt with a card to increase its affection.
        Usage: !flirt <card_global_id>
        """
        # Increase affection by a random amount between 1 and 5
        card_name, new_affection = self._apply_affection(ctx.author.id, card_id, random.randint(1, 5))
        if not card_name:
            await ctx.send("❌ Card not found in your collection!")
        else:
            await ctx.send(f"{ctx.author.mention}, you flirted with **{card_name}**! New affection is {new_affection}.")

    @commands.command(name="hug")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def hug(self, ctx, card_id: str):
        """
        Hug a card to boost its affection.
        Usage: !hug <card_global_id>
        """
        # Increase affection by a random amount between 2 and 6
        card_name, new_affection = self._apply_affection(ctx.author.id, card_id, random.randint(2, 6))
        if not card_name:
            await ctx.send("❌ Card not found in your collection!")
        else:
            await ctx.send(f"{ctx.author.mention}, you hugged **{card_name}**! New affection is {new_affection}.")

    @commands.command(name="kiss")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def kiss(self, ctx, card_id: str):
        """
        Kiss a card to raise its affection.
        Usage: !kiss <card_global_id>
        """
        # Increase affection by a random amount between 3 and 8
        card_name, new_affection = self._apply_affection(ctx.author.id, card_id, random.randint(3, 8))
        if not card_name:
            await ctx.send("❌ Card not found in your collection!")
        else:
            await ctx.send(f"{ctx.author.mention}, you kissed **{card_name}**! New affection is {new_affection}.")

async def setup(bot):
    await bot.add_cog(Affection(bot))
