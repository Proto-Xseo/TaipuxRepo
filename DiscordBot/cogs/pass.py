import discord
from discord.ext import commands

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help")
    async def help_command(self, ctx):
        embed = discord.Embed(
            title="📜 Help Menu",
            description="Here are the available commands:",
            color=discord.Color.red()
        )
        embed.add_field(name="❤️ Affection (Coming Soon)", value="Commands to increase character affection.", inline=False)
        embed.add_field(name="🍫 !chocolate", value="Increases a character's affection by 5 using chocolate.", inline=True)
        embed.add_field(name="🌹 !rose", value="Increases a character's affection by 10 using a rose.", inline=True)
        # Archive
        embed.add_field(name="📁 Archive", value="`!card` → View archived cards.", inline=False)
        # Claiming System
        embed.add_field(name="🎁 Claim", value="`!claim` → Claim your daily rewards.", inline=False)
        # Collection System
        embed.add_field(name="📦 Collection", value="`!collection` → View your collected items and cards.", inline=False)
        # Economy System
        embed.add_field(name="💰 Economy", value="`!balance` → Check your current balance.", inline=False)
        # Gacha (Activator)
        embed.add_field(name="🎲 Gacha", value="`!gacha` → Roll for new cards and items!", inline=False)
        # Leaderboard
        embed.add_field(name="🏆 Leaderboard", value="`!leaderboard` → View top players.", inline=False)
        # Lookup System
        embed.add_field(name="🔍 Lookup", value="`!lookup` → Search for specific items or stats.", inline=False)
        # Management Commands
        embed.add_field(name="🛠️ Management", value="`!wishlist` → Manage your wishlist.", inline=False)
        # PVE (Activator)
        embed.add_field(name="⚔️ PVE", value="`!pve` → Start a battle!", inline=False)
        # Profile
        embed.add_field(name="👤 Profile", value="`!profile` → View your player profile. ", inline=False)
        # Trade System
        embed.add_field(
    name="🔄 Trade System",
    value=(
        "🎁 `!gift_item` → Gift an item to another player.\n"
        "📦 `!giftopen` → Open a pending gift.\n"
        "🎟️ `!giftopennum <number>` → Open a specific pending gift by number.\n"
        "🤝 `!start_trade` → Start a new trade with another player.\n"
        "❌ `!trade_abandon` → Cancel an ongoing trade.\n"
        "✅ `!trade_accept` → Accept a trade invitation.\n"
        "🚫 `!trade_reject` → Reject a trade invitation.\n"
        "➕ `!tradeadd <item>` → Add a card/item to the trade by its global ID.\n"
        "💰 `!tradeaddresource <amount>` → Add a resource (gold or shards) to the trade.\n"
        "🔒 `!tradeclose` → Finalize and close a trade.\n"
        "➖ `!traderemove <item>` → Remove a card/item from the trade."
    ),
    inline=False
)

        embed.set_footer(text="Use !help <command> for more details.")

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(HelpCog(bot))

