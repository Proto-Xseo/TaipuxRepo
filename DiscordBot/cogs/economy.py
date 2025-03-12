from discord.ext import commands

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="balance")
    async def balance(self, ctx):
        await ctx.send("Your balance is 1000 coins.")

async def setup(bot):
    await bot.add_cog(Economy(bot))
