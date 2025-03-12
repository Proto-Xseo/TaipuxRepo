import discord
from discord.ext import commands
import json
import asyncio
from typing import Dict, List, Optional, TypedDict, Union, Set

# Import from utils folder
from utils.db import get_user, update_user

class CardData(TypedDict):
    name: str
    global_id: str
    rarity: str
    series: str

class UserData(TypedDict):
    cards: List[CardData]
    gold: int
    shards: int
    username: str

class TradeItems(TypedDict):
    cards: List[CardData]
    gold: int
    shards: int

class TradeSession:
    def __init__(self, initiator: discord.Member, recipient: discord.Member):
        self.initiator = initiator
        self.recipient = recipient
        self.initiator_items: TradeItems = {
            "cards": [],
            "gold": 0,
            "shards": 0
        }
        self.recipient_items: TradeItems = {
            "cards": [],
            "gold": 0,
            "shards": 0
        }
        self.initiator_confirmed: bool = False
        self.recipient_confirmed: bool = False
        self.initiator_closed: bool = False
        self.recipient_closed: bool = False
        self.trade_message: Optional[discord.Message] = None
        self.status: str = "PENDING"  # PENDING, ACCEPTED, REJECTED, COMPLETED, CANCELLED
        self.last_interaction_time = asyncio.get_event_loop().time()

class ViewCardsButton(discord.ui.Button):
    def __init__(self, label: str, user_type: str, trade_session: 'TradeSession'):
        super().__init__(style=discord.ButtonStyle.primary, label=label)
        self.user_type = user_type  # "initiator" or "recipient"
        self.trade_session = trade_session

    async def callback(self, interaction: discord.Interaction):
        # Only allow the trade participants to view cards
        if interaction.user not in [self.trade_session.initiator, self.trade_session.recipient]:
            await interaction.response.send_message("You're not part of this trade!", ephemeral=True)
            return

        # Get the cards to display
        if self.user_type == "initiator":
            cards = self.trade_session.initiator_items["cards"]
            user = self.trade_session.initiator
        else:
            cards = self.trade_session.recipient_items["cards"]
            user = self.trade_session.recipient

        if not cards:
            await interaction.response.send_message(f"{user.display_name} hasn't added any cards to the trade.", ephemeral=True)
            return

        # Create an embed to display the cards with images
        embed = discord.Embed(
            title=f"🃏 {user.display_name}'s Trade Cards",
            description=f"Cards added to the trade by {user.display_name}:",
            color=discord.Color.blue()
        )

        # Display cards with images (similar to !view command)
        # Note: This is a simplified version - actual implementation would need to fetch card images
        for i, card in enumerate(cards, 1):
            embed.add_field(
                name=f"{i}. {card.get('name', 'Unknown')} ({card.get('rarity', 'N/A')})",
                value=f"Global ID: {card.get('global_id', 'N/A')}\nSeries: {card.get('series', 'N/A')}",
                inline=True
            )
            # In a real implementation, you would add the card image here
            # embed.set_image(url=card.get('image_url'))

        # Send the embed
        await interaction.response.send_message(embed=embed, ephemeral=False)
        
        # Make the trade embed return to the bottom of the chat
        await self.trade_session.trade_message.delete()
        new_message = await interaction.channel.send(
            f"🔄 **Trade in progress** between {self.trade_session.initiator.mention} and {self.trade_session.recipient.mention}",
            embed=await create_trade_embed(self.trade_session),
            view=self.view
        )
        self.trade_session.trade_message = new_message

class TradeView(discord.ui.View):
    def __init__(self, trade_session: TradeSession):
        super().__init__(timeout=600)  # 10 minutes timeout
        self.trade_session = trade_session
        
        # Add view cards buttons - only keeping these as per requirements
        self.add_item(ViewCardsButton(f"View {trade_session.initiator.display_name}'s Cards", "initiator", trade_session))
        self.add_item(ViewCardsButton(f"View {trade_session.recipient.display_name}'s Cards", "recipient", trade_session))

async def create_trade_embed(trade_session: TradeSession):
    """Create a trade embed based on the current trade session state"""
    # Determine embed color based on trade status
    embed_color = discord.Color.gold()
    if trade_session.status == "COMPLETED":
        embed_color = discord.Color.green()
    elif trade_session.status == "CANCELLED":
        embed_color = discord.Color.red()
    elif trade_session.status == "REJECTED":
        embed_color = discord.Color.dark_red()
    
    # Create trade embed
    embed = discord.Embed(
        title="💱 Trade Offer", 
        color=embed_color
    )
    
    # Add status information as description with more visual elements
    status_text = ""
    if trade_session.status == "PENDING":
        status_text = f"⏳ **PENDING:** Waiting for {trade_session.recipient.mention} to accept the trade invitation."
    elif trade_session.status == "ACCEPTED":
        status_text = "✅ **ACTIVE TRADE:** Add items and close when ready."
        if trade_session.initiator_closed and trade_session.recipient_closed:
            status_text = "🔄 **FINALIZING TRADE:** Both sides closed, completing trade..."
        elif trade_session.initiator_closed:
            status_text = f"⏳ **WAITING:** {trade_session.initiator.display_name} closed their side, waiting for {trade_session.recipient.display_name}."
        elif trade_session.recipient_closed:
            status_text = f"⏳ **WAITING:** {trade_session.recipient.display_name} closed their side, waiting for {trade_session.initiator.display_name}."
    elif trade_session.status == "REJECTED":
        status_text = "❌ **REJECTED:** Trade invitation was declined."
    elif trade_session.status == "COMPLETED":
        status_text = "🎉 **TRADE COMPLETED!** Items have been exchanged successfully."
    elif trade_session.status == "CANCELLED":
        status_text = "🚫 **TRADE CANCELLED:** This trade was abandoned."
    embed.description = status_text

    # Calculate wishlist counts
    initiator_wishlist_count = sum(1 for card in trade_session.initiator_items['cards'] if card.get('wishlist', False))
    recipient_wishlist_count = sum(1 for card in trade_session.recipient_items['cards'] if card.get('wishlist', False))

    # Initiator section
    initiator_cards_text = ""
    for card in trade_session.initiator_items['cards']:
        initiator_cards_text += f"`{card.get('rarity', '')} {card.get('name', 'Unknown')}` (G-{card.get('global_id', 'N/A')})\n"
    
    if trade_session.initiator_items['gold'] > 0:
        initiator_cards_text += f"💰 Gold: `{trade_session.initiator_items['gold']}`\n"
    
    if trade_session.initiator_items['shards'] > 0:
        initiator_cards_text += f"💎 Shards: `{trade_session.initiator_items['shards']}`\n"
    
    if initiator_wishlist_count > 0:
        initiator_cards_text += f"✨ Wishlist: `{initiator_wishlist_count}`\n"
        
    if not initiator_cards_text:
        initiator_cards_text = "No items added yet."
    
    # Add status indicator
    if trade_session.status == "ACCEPTED":
        if trade_session.initiator_closed:
            initiator_cards_text += "\n🔒 **CLOSED**"
        else:
            initiator_cards_text += "\n🔓 **OPEN**"
    
    embed.add_field(
        name=f"**Host: {trade_session.initiator.mention}**", 
        value=initiator_cards_text, 
        inline=True
    )

    # Recipient section
    recipient_cards_text = ""
    for card in trade_session.recipient_items['cards']:
        recipient_cards_text += f"`{card.get('rarity', '')} {card.get('name', 'Unknown')}` (G-{card.get('global_id', 'N/A')})\n"
    
    if trade_session.recipient_items['gold'] > 0:
        recipient_cards_text += f"💰 Gold: `{trade_session.recipient_items['gold']}`\n"
    
    if trade_session.recipient_items['shards'] > 0:
        recipient_cards_text += f"💎 Shards: `{trade_session.recipient_items['shards']}`\n"
    
    if recipient_wishlist_count > 0:
        recipient_cards_text += f"✨ Wishlist: `{recipient_wishlist_count}`\n"
        
    if not recipient_cards_text:
        recipient_cards_text = "No items added yet."
    
    # Add status indicator
    if trade_session.status == "ACCEPTED":
        if trade_session.recipient_closed:
            recipient_cards_text += "\n🔒 **CLOSED**"
        else:
            recipient_cards_text += "\n🔓 **OPEN**"
    
    embed.add_field(
        name=f"**Invited: {trade_session.recipient.mention}**", 
        value=recipient_cards_text, 
        inline=True
    )
    
    # Add trade fairness indicator
    if trade_session.status == "ACCEPTED" and (trade_session.initiator_items['cards'] or trade_session.recipient_items['cards']):
        fairness_text = ""
        if initiator_wishlist_count > 0 and recipient_wishlist_count > 0:
            ratio = initiator_wishlist_count / recipient_wishlist_count
            if 0.8 <= ratio <= 1.2:
                fairness_text = "✅ **Fair Trade:** Wishlist values are balanced."
            elif ratio > 1.2:
                fairness_text = "⚠️ **Caution:** Host is offering more wishlist value."
            else:
                fairness_text = "⚠️ **Caution:** Invited user is offering more wishlist value."
        elif initiator_wishlist_count > 0 and recipient_wishlist_count == 0:
            fairness_text = "⚠️ **Caution:** Only the host is offering wishlist cards."
        elif initiator_wishlist_count == 0 and recipient_wishlist_count > 0:
            fairness_text = "⚠️ **Caution:** Only the invited user is offering wishlist cards."
        
        if fairness_text:
            embed.add_field(name="Trade Fairness", value=fairness_text, inline=False)
    
    # Add footer with instructions
    footer_text = ""
    if trade_session.status == "PENDING":
        footer_text = "Type '!tac' to accept or '!tradereject' to decline this invitation."
    elif trade_session.status == "ACCEPTED":
        if trade_session.initiator_closed and not trade_session.recipient_closed:
            footer_text = f"Waiting for {trade_session.recipient.display_name} to close their side of the trade with '!tc'."
        elif trade_session.recipient_closed and not trade_session.initiator_closed:
            footer_text = f"Waiting for {trade_session.initiator.display_name} to close their side of the trade with '!tc'."
        else:
            footer_text = "Add items with '!ta <global_id>' or '!taddresource <type> <amount>'. Close with '!tc' when ready."
    
    if footer_text:
        embed.set_footer(text=footer_text)
    
    return embed

async def update_trade_embed(trade_session: TradeSession):
    """Update the trade message with the current trade embed"""
    embed = await create_trade_embed(trade_session)
    
    # Update trade message
    if trade_session.trade_message:
        try:
            await trade_session.trade_message.edit(embed=embed)
        except discord.NotFound:
            # Message was deleted, can't update
            pass

async def complete_trade(trade_session: TradeSession):
    # Validate trade (not completely empty)
    if (not trade_session.initiator_items['cards'] and 
        not trade_session.initiator_items['gold'] and 
        not trade_session.initiator_items['shards'] and
        not trade_session.recipient_items['cards'] and 
        not trade_session.recipient_items['gold'] and 
        not trade_session.recipient_items['shards']):
        await trade_session.trade_message.channel.send("Trade cannot be empty!")
        return

    # Perform actual trade
    initiator_data = get_user(trade_session.initiator.id)
    recipient_data = get_user(trade_session.recipient.id)

    # Transfer cards
    initiator_data['cards'] = [
        card for card in initiator_data['cards'] 
        if card not in trade_session.initiator_items['cards']
    ]
    initiator_data['cards'].extend(trade_session.recipient_items['cards'])

    recipient_data['cards'] = [
        card for card in recipient_data['cards'] 
        if card not in trade_session.recipient_items['cards']
    ]
    recipient_data['cards'].extend(trade_session.initiator_items['cards'])

    # Transfer resources
    initiator_data['gold'] = initiator_data.get('gold', 0) - trade_session.initiator_items['gold']
    initiator_data['gold'] = initiator_data['gold'] + trade_session.recipient_items['gold']
    
    recipient_data['gold'] = recipient_data.get('gold', 0) - trade_session.recipient_items['gold']
    recipient_data['gold'] = recipient_data['gold'] + trade_session.initiator_items['gold']
    
    initiator_data['shards'] = initiator_data.get('shards', 0) - trade_session.initiator_items['shards']
    initiator_data['shards'] = initiator_data['shards'] + trade_session.recipient_items['shards']
    
    recipient_data['shards'] = recipient_data.get('shards', 0) - trade_session.recipient_items['shards']
    recipient_data['shards'] = recipient_data['shards'] + trade_session.initiator_items['shards']

    # Update user data
    update_user(trade_session.initiator.id, "cards", initiator_data['cards'])
    update_user(trade_session.initiator.id, "gold", initiator_data['gold'])
    update_user(trade_session.initiator.id, "shards", initiator_data['shards'])
    
    update_user(trade_session.recipient.id, "cards", recipient_data['cards'])
    update_user(trade_session.recipient.id, "gold", recipient_data['gold'])
    update_user(trade_session.recipient.id, "shards", recipient_data['shards'])

    # Update trade status
    trade_session.status = "COMPLETED"
    
    # Update the trade embed
    await update_trade_embed(trade_session)

    # Send completion message
    await trade_session.trade_message.channel.send(
        f"🎉 Trade completed between {trade_session.initiator.mention} and {trade_session.recipient.mention}!"
    )

async def cancel_trade(trade_session: TradeSession):
    # Update trade status
    trade_session.status = "CANCELLED"
    
    # Update the trade embed
    await update_trade_embed(trade_session)
    
    # Send cancellation message
    await trade_session.trade_message.channel.send(
        f"🚫 Trade cancelled between {trade_session.initiator.mention} and {trade_session.recipient.mention}"
    )

class GiftData(TypedDict):
    sender_id: int
    recipient_id: int
    card: Optional[CardData]
    gold: int
    shards: int
    message: str
    timestamp: float

class GiftModal(discord.ui.Modal, title="Gift Items"):
    card_id = discord.ui.TextInput(
        label="Card Global ID (optional)",
        placeholder="Enter the global ID of the card to gift",
        required=False,
        style=discord.TextStyle.short
    )
    gold = discord.ui.TextInput(
        label="Gold Amount (optional)",
        placeholder="Enter amount of gold to gift",
        required=False,
        style=discord.TextStyle.short
    )
    shards = discord.ui.TextInput(
        label="Shards Amount (optional)",
        placeholder="Enter amount of shards to gift",
        required=False,
        style=discord.TextStyle.short
    )
    message = discord.ui.TextInput(
        label="Gift Message (optional)",
        placeholder="Add a personal message with your gift",
        required=False,
        style=discord.TextStyle.paragraph
    )
    
    def __init__(self, sender: discord.Member, recipient: discord.Member, bot):
        super().__init__()
        self.sender = sender
        self.recipient = recipient
        self.bot = bot
        
    async def on_submit(self, interaction: discord.Interaction):
        # Get sender data
        sender_data = get_user(self.sender.id)
        
        # Initialize gift data
        gift_data = {
            "sender_id": self.sender.id,
            "recipient_id": self.recipient.id,
            "card": None,
            "gold": 0,
            "shards": 0,
            "message": self.message.value if self.message.value else "",
            "timestamp": asyncio.get_event_loop().time()
        }
        
        gift_details = []
        gift_successful = False
        
        # Process card gift if provided
        if self.card_id.value:
            card_id = self.card_id.value.strip()
            card_to_gift = None
            
            # Find the card by global ID
            for card in sender_data.get('cards', []):
                if card.get('global_id') == card_id:
                    card_to_gift = card
                    break
            
            if card_to_gift:
                # Remove card from sender
                sender_data['cards'] = [c for c in sender_data.get('cards', []) if c.get('global_id') != card_id]
                
                # Store card in gift data
                gift_data["card"] = card_to_gift
                
                # Update gift details
                gift_details.append(f"Card: {card_to_gift.get('name', 'Unknown')} (ID: {card_id})")
                gift_successful = True
                
                # Update sender data
                update_user(self.sender.id, "cards", sender_data['cards'])
            else:
                await interaction.response.send_message(f"Card with Global ID {card_id} not found in your collection!", ephemeral=True)
                return
        
        # Process gold gift if provided
        if self.gold.value:
            try:
                gold_amount = int(self.gold.value)
                if gold_amount <= 0:
                    await interaction.response.send_message("Gold amount must be positive!", ephemeral=True)
                    return
                
                sender_gold = sender_data.get('gold', 0)
                if gold_amount > sender_gold:
                    await interaction.response.send_message(f"You don't have enough gold! You have {sender_gold} gold.", ephemeral=True)
                    return
                
                # Deduct gold from sender
                sender_data['gold'] = sender_gold - gold_amount
                
                # Store gold in gift data
                gift_data["gold"] = gold_amount
                
                # Update gift details
                gift_details.append(f"Gold: {gold_amount}")
                gift_successful = True
                
                # Update sender data
                update_user(self.sender.id, "gold", sender_data['gold'])
            except ValueError:
                await interaction.response.send_message("Invalid gold amount!", ephemeral=True)
                return
        
        # Process shards gift if provided
        if self.shards.value:
            try:
                shards_amount = int(self.shards.value)
                if shards_amount <= 0:
                    await interaction.response.send_message("Shards amount must be positive!", ephemeral=True)
                    return
                
                sender_shards = sender_data.get('shards', 0)
                if shards_amount > sender_shards:
                    await interaction.response.send_message(f"You don't have enough shards! You have {sender_shards} shards.", ephemeral=True)
                    return
                
                # Deduct shards from sender
                sender_data['shards'] = sender_shards - shards_amount
                
                # Store shards in gift data
                gift_data["shards"] = shards_amount
                
                # Update gift details
                gift_details.append(f"Shards: {shards_amount}")
                gift_successful = True
                
                # Update sender data
                update_user(self.sender.id, "shards", sender_data['shards'])
            except ValueError:
                await interaction.response.send_message("Invalid shards amount!", ephemeral=True)
                return
        
        # Check if any gift was successful
        if not gift_successful:
            await interaction.response.send_message("You must gift at least one item (card, gold, or shards)!", ephemeral=True)
            return
        
        # Store the gift in the pending gifts
        cog = self.bot.get_cog("TradeCog")
        if cog:
            gift_id = f"{self.sender.id}_{self.recipient.id}_{int(gift_data['timestamp'])}"
            cog.pending_gifts[gift_id] = gift_data
        
        # Create gift notification embed
        embed = discord.Embed(
            title="🎁 Gift Sent!",
            description=f"{self.sender.mention} has sent a gift to {self.recipient.mention}!",
            color=discord.Color.purple()
        )
        
        # Add gift details
        embed.add_field(name="Gift Contents", value="\n".join(gift_details), inline=False)
        
        # Add message if provided
        if self.message.value:
            embed.add_field(name="Message", value=self.message.value, inline=False)
        
        # Send gift notification to sender
        await interaction.response.send_message(embed=embed)
        
        # Send gift notification to recipient
        recipient_embed = discord.Embed(
            title="🎁 Gift Received!",
            description=f"You have received a gift from {self.sender.mention}!",
            color=discord.Color.purple()
        )
        
        recipient_embed.add_field(name="Gift Contents", value="\n".join(gift_details), inline=False)
        
        if self.message.value:
            recipient_embed.add_field(name="Message", value=self.message.value, inline=False)
            
        recipient_embed.set_footer(text="Type '!og' or '!giftopen' to open this gift.")
        
        try:
            await self.recipient.send(embed=recipient_embed)
        except:
            # If DM fails, send in the channel
            await interaction.followup.send(
                f"{self.recipient.mention}, you have received a gift from {self.sender.mention}! Type `!og` or `!giftopen` to open it.",
                embed=recipient_embed
            )

class TradeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_trades = {}
        self.pending_invites = {}
        self.pending_gifts = {}
        
        # Start background task to clean up expired trades and gifts
        self.cleanup_task = bot.loop.create_task(self.cleanup_expired_items())
        
    def cog_unload(self):
        # Cancel the cleanup task when the cog is unloaded
        self.cleanup_task.cancel()
        
    async def cleanup_expired_items(self):
        """Background task to clean up expired trades, invites, and gifts"""
        try:
            while not self.bot.is_closed():
                current_time = asyncio.get_event_loop().time()
                
                # Clean up expired trades (inactive for more than 30 minutes)
                expired_trades = []
                for trade_id, trade_session in self.active_trades.items():
                    if current_time - trade_session.last_interaction_time > 1800:  # 30 minutes
                        expired_trades.append(trade_id)
                        
                # Remove expired trades
                for trade_id in expired_trades:
                    trade_session = self.active_trades.pop(trade_id, None)
                    if trade_session and trade_session.trade_message:
                        try:
                            await trade_session.trade_message.channel.send(
                                f"Trade between {trade_session.initiator.mention} and {trade_session.recipient.mention} has expired due to inactivity."
                            )
                            await update_trade_embed(trade_session)
                        except:
                            pass
                
                # Clean up expired invites (pending for more than 10 minutes)
                expired_invites = []
                for invite_id, (_, invite_time) in self.pending_invites.items():
                    if current_time - invite_time > 600:  # 10 minutes
                        expired_invites.append(invite_id)
                        
                # Remove expired invites
                for invite_id in expired_invites:
                    self.pending_invites.pop(invite_id, None)
                
                # Clean up expired gifts (pending for more than 7 days)
                expired_gifts = []
                for gift_id, gift_data in self.pending_gifts.items():
                    if current_time - gift_data["timestamp"] > 604800:  # 7 days
                        expired_gifts.append(gift_id)
                        
                # Remove expired gifts
                for gift_id in expired_gifts:
                    self.pending_gifts.pop(gift_id, None)
                
                # Sleep for 5 minutes before checking again
                await asyncio.sleep(300)
        except asyncio.CancelledError:
            # Task was cancelled, clean up
            pass
        except Exception as e:
            print(f"Error in cleanup task: {e}")

    @commands.command(aliases=['trade'])
    async def start_trade(self, ctx, recipient: discord.Member):
        if recipient == ctx.author:
            await ctx.send("You can't trade with yourself!")
            return
            
        if recipient.bot:
            await ctx.send("You can't trade with a bot!")
            return
            
        # Check if there's already an active trade between these users
        trade_id = f"{ctx.author.id}_{recipient.id}"
        reverse_trade_id = f"{recipient.id}_{ctx.author.id}"
        
        if trade_id in self.active_trades or reverse_trade_id in self.active_trades:
            await ctx.send("There's already an active trade between you and this user!")
            return
            
        # Check if there's a pending invite
        if trade_id in self.pending_invites or reverse_trade_id in self.pending_invites:
            await ctx.send("There's already a pending trade invitation between you and this user!")
            return

        # Create a pending invite
        self.pending_invites[trade_id] = (recipient, asyncio.get_event_loop().time())
        
        # Send trade invitation as a normal message instead of an embed
        await ctx.send(f"🔄 **TRADE INVITATION:** {ctx.author.mention} wants to trade with {recipient.mention}!\n{recipient.mention}, use `!tac` to accept or `!tradereject` to decline this invitation.")

    @commands.command(aliases=['tac'])
    async def trade_accept(self, ctx):
        """Accept a pending trade invitation"""
        # Check if there's a pending invite for this user
        invite_id = None
        for trade_id, (recipient, _) in self.pending_invites.items():
            if recipient.id == ctx.author.id:
                invite_id = trade_id
                break
                
        if not invite_id:
            await ctx.send("You don't have any pending trade invitations!")
            return
            
        # Get the initiator from the invite ID
        initiator_id = int(invite_id.split('_')[0])
        initiator = ctx.guild.get_member(initiator_id)
        
        # If initiator not found in guild members, try to fetch from bot's users
        if not initiator:
            try:
                initiator = await self.bot.fetch_user(initiator_id)
            except Exception as e:
                print(f"Trade accept - Error fetching initiator: {e}")
        
        if not initiator:
            await ctx.send("The trade initiator is no longer available!")
            self.pending_invites.pop(invite_id, None)
            return
            
        # Remove the pending invite
        self.pending_invites.pop(invite_id, None)
        
        # Create trade session
        trade_session = TradeSession(initiator, ctx.author)
        trade_session.status = "ACCEPTED"
        
        # Create trade view
        trade_view = TradeView(trade_session)
        
        # Create the trade embed using the standard function
        embed = await create_trade_embed(trade_session)
        
        # Send initial trade message
        trade_message = await ctx.send(
            f"🤝 **TRADE STARTED:** {initiator.mention} and {ctx.author.mention} are now trading!",
            embed=embed,
            view=trade_view
        )
        
        # Store trade session
        trade_session.trade_message = trade_message
        self.active_trades[invite_id] = trade_session
        
        # Update last interaction time
        trade_session.last_interaction_time = asyncio.get_event_loop().time()

    @commands.command(aliases=['tradereject'])
    async def trade_reject(self, ctx):
        # Check if there's a pending invite for this user
        invite_id = None
        for trade_id, (recipient, _) in self.pending_invites.items():
            if recipient.id == ctx.author.id:
                invite_id = trade_id
                break
                
        if not invite_id:
            await ctx.send("You don't have any pending trade invitations!")
            return
            
        # Get the initiator from the invite ID
        initiator_id = int(invite_id.split('_')[0])
        initiator = ctx.guild.get_member(initiator_id)
        
        # Remove the pending invite
        self.pending_invites.pop(invite_id, None)
        
        # Send rejection message
        await ctx.send(f"{ctx.author.mention} has rejected the trade invitation from {initiator.mention if initiator else 'someone'}.")

    @commands.command(aliases=['ta'])
    async def tradeadd(self, ctx, global_id: str):
        """Add a card to the trade by its global ID"""
        # Find active trade involving this user
        trade_session = None
        trade_id = None
        
        for tid, session in self.active_trades.items():
            if ctx.author.id == session.initiator.id or ctx.author.id == session.recipient.id:
                trade_session = session
                trade_id = tid
                break
                
        if not trade_session:
            await ctx.send("You don't have an active trade session!")
            return
            
        # Check if trade is still in progress
        if trade_session.status != "ACCEPTED":
            await ctx.send("This trade is not active!")
            return
            
        # Check if user has already closed their side
        if (ctx.author == trade_session.initiator and trade_session.initiator_closed) or \
           (ctx.author == trade_session.recipient and trade_session.recipient_closed):
            await ctx.send("You've already closed your side of the trade!")
            return
            
        # Get user data
        user_data = get_user(ctx.author.id)
        user_cards = user_data.get('cards', [])
        
        # Find the card by global ID
        card_to_add = None
        for card in user_cards:
            if card.get('global_id') == global_id:
                card_to_add = card
                break
                
        if not card_to_add:
            await ctx.send(f"Card with Global ID {global_id} not found in your collection!")
            return
            
        # Add the card to the trade
        if ctx.author == trade_session.initiator:
            # Check if card is already in the trade
            if any(c.get('global_id') == global_id for c in trade_session.initiator_items['cards']):
                await ctx.send("This card is already in the trade!")
                return
                
            # Check if we've reached the limit
            if len(trade_session.initiator_items['cards']) >= 20:
                await ctx.send("You can only trade up to 20 cards!")
                return
                
            # Add card to trade (preserving its global_id)
            trade_session.initiator_items['cards'].append(card_to_add)
        else:
            # Check if card is already in the trade
            if any(c.get('global_id') == global_id for c in trade_session.recipient_items['cards']):
                await ctx.send("This card is already in the trade!")
                return
                
            # Check if we've reached the limit
            if len(trade_session.recipient_items['cards']) >= 20:
                await ctx.send("You can only trade up to 20 cards!")
                return
                
            # Add card to trade (preserving its global_id)
            trade_session.recipient_items['cards'].append(card_to_add)
            
        # Update the trade embed
        await update_trade_embed(trade_session)
        
        # Update last interaction time
        trade_session.last_interaction_time = asyncio.get_event_loop().time()
        
        # Send confirmation (only one notification)
        await ctx.send(f"Added card {card_to_add.get('name', 'Unknown')} to the trade!")

    @commands.command(aliases=['tr'])
    async def traderemove(self, ctx, global_id: str):
        # Find active trade involving this user
        trade_session = None
        trade_id = None
        
        for tid, session in self.active_trades.items():
            if ctx.author.id == session.initiator.id or ctx.author.id == session.recipient.id:
                trade_session = session
                trade_id = tid
                break
                
        if not trade_session:
            await ctx.send("You don't have an active trade session!")
            return
            
        # Check if trade is still in progress
        if trade_session.status != "ACCEPTED":
            await ctx.send("This trade is not active!")
            return
            
        # Check if user has already closed their side
        if (ctx.author == trade_session.initiator and trade_session.initiator_closed) or \
           (ctx.author == trade_session.recipient and trade_session.recipient_closed):
            await ctx.send("You've already closed your side of the trade!")
            return
            
        # Remove the card from the trade
        card_removed = False
        card_name = "Unknown"
        
        if ctx.author == trade_session.initiator:
            for i, card in enumerate(trade_session.initiator_items['cards']):
                if card.get('global_id') == global_id:
                    card_name = card.get('name', 'Unknown')
                    trade_session.initiator_items['cards'].pop(i)
                    card_removed = True
                    break
        else:
            for i, card in enumerate(trade_session.recipient_items['cards']):
                if card.get('global_id') == global_id:
                    card_name = card.get('name', 'Unknown')
                    trade_session.recipient_items['cards'].pop(i)
                    card_removed = True
                    break
                    
        if not card_removed:
            await ctx.send(f"Card with Global ID {global_id} not found in your trade items!")
            return
            
        # Update the trade embed
        await update_trade_embed(trade_session)
        
        # Update last interaction time
        trade_session.last_interaction_time = asyncio.get_event_loop().time()
        
        # Send confirmation
        await ctx.send(f"Removed card {card_name} from the trade!")
        
        # Make sure the trade message stays visible
        if trade_session.trade_message:
            try:
                await trade_session.trade_message.channel.send(
                    f"{ctx.author.mention} removed a card from the trade!",
                    delete_after=5
                )
            except:
                pass

    @commands.command(aliases=['taddresource', 'tar'])
    async def tradeaddresource(self, ctx, resource_type: str, amount: int):
        """Add a resource (gold or shards) to the trade"""
        # Find active trade involving this user
        trade_session = None
        trade_id = None
        
        for tid, session in self.active_trades.items():
            if ctx.author.id == session.initiator.id or ctx.author.id == session.recipient.id:
                trade_session = session
                trade_id = tid
                break
                
        if not trade_session:
            await ctx.send("You don't have an active trade session!")
            return
            
        # Check if trade is still in progress
        if trade_session.status != "ACCEPTED":
            await ctx.send("This trade is not active!")
            return
            
        # Check if user has already closed their side
        if (ctx.author == trade_session.initiator and trade_session.initiator_closed) or \
           (ctx.author == trade_session.recipient and trade_session.recipient_closed):
            await ctx.send("You've already closed your side of the trade!")
            return
            
        # Validate resource type
        resource_type = resource_type.lower()
        if resource_type not in ['gold', 'shards']:
            await ctx.send("Invalid resource type! Use 'gold' or 'shards'.")
            return
            
        # Validate amount
        if amount <= 0:
            await ctx.send(f"{resource_type.capitalize()} amount must be positive!")
            return
            
        # Get user data
        user_data = get_user(ctx.author.id)
        user_resource = user_data.get(resource_type, 0)
        
        # Check if user has enough of the resource
        if amount > user_resource:
            await ctx.send(f"You don't have enough {resource_type}! You have {user_resource} {resource_type}.")
            return
            
        # Add resource to the trade
        if ctx.author == trade_session.initiator:
            trade_session.initiator_items[resource_type] = amount
        else:
            trade_session.recipient_items[resource_type] = amount
            
        # Update the trade embed
        await update_trade_embed(trade_session)
        
        # Update last interaction time
        trade_session.last_interaction_time = asyncio.get_event_loop().time()
        
        # Send confirmation
        await ctx.send(f"Added {amount} {resource_type} to the trade!")

    @commands.command(aliases=['tab', 'tradeabandon'])
    async def trade_abandon(self, ctx):
        # Find active trade involving this user
        trade_session = None
        trade_id = None
        
        for tid, session in self.active_trades.items():
            if ctx.author.id == session.initiator.id or ctx.author.id == session.recipient.id:
                trade_session = session
                trade_id = tid
                break
                
        if not trade_session:
            await ctx.send("You don't have an active trade session!")
            return
            
        # Check if trade is still in progress
        if trade_session.status != "ACCEPTED":
            await ctx.send("This trade is not active!")
            return
            
        # Cancel the trade
        trade_session.status = "CANCELLED"
        await cancel_trade(trade_session)
        
        # Remove the trade from active trades
        self.active_trades.pop(trade_id, None)
        
        # Send confirmation
        await ctx.send(f"{ctx.author.mention} has abandoned the trade!")

    @commands.command(aliases=['tc'])
    async def tradeclose(self, ctx):
        # Find active trade involving this user
        trade_session = None
        trade_id = None
        
        for tid, session in self.active_trades.items():
            if ctx.author.id == session.initiator.id or ctx.author.id == session.recipient.id:
                trade_session = session
                trade_id = tid
                break
                
        if not trade_session:
            await ctx.send("You don't have an active trade session!")
            return
            
        # Check if trade is still in progress
        if trade_session.status != "ACCEPTED":
            await ctx.send("This trade is not active!")
            return
            
        # Check if user has already closed their side
        if (ctx.author == trade_session.initiator and trade_session.initiator_closed) or \
           (ctx.author == trade_session.recipient and trade_session.recipient_closed):
            await ctx.send("You've already closed your side of the trade!")
            return
            
        # Close the user's side of the trade
        if ctx.author == trade_session.initiator:
            trade_session.initiator_closed = True
        else:
            trade_session.recipient_closed = True
            
        # Update the trade embed
        await update_trade_embed(trade_session)
        
        # Update last interaction time
        trade_session.last_interaction_time = asyncio.get_event_loop().time()
        
        # Send confirmation
        await ctx.send(f"{ctx.author.mention} has closed their side of the trade!")
        
        # Check if both sides are closed
        if trade_session.initiator_closed and trade_session.recipient_closed:
            # Complete the trade
            await complete_trade(trade_session)
            
            # Remove the trade from active trades
            self.active_trades.pop(trade_id, None)

    async def process_gift(self, gift_id: str, ctx):
        """Process a pending gift and transfer items to the recipient"""
        # Check if the gift exists
        if gift_id not in self.pending_gifts:
            await ctx.send("This gift doesn't exist or has already been opened!")
            return
            
        # Get the gift data
        gift_data = self.pending_gifts[gift_id]
        
        # Check if the user is the recipient
        if ctx.author.id != gift_data["recipient_id"]:
            await ctx.send("This gift is not for you!")
            return
            
        # Get recipient data
        recipient_data = get_user(ctx.author.id)
        
        # Process card gift if provided
        if gift_data["card"]:
            # Add card to recipient
            recipient_cards = recipient_data.get('cards', [])
            recipient_cards.append(gift_data["card"])
            recipient_data['cards'] = recipient_cards
            
            # Update recipient data
            update_user(ctx.author.id, "cards", recipient_data['cards'])
            
        # Process gold gift if provided
        if gift_data["gold"] > 0:
            # Add gold to recipient
            recipient_gold = recipient_data.get('gold', 0) + gift_data["gold"]
            
            # Update recipient data
            update_user(ctx.author.id, "gold", recipient_gold)
            
        # Process shards gift if provided
        if gift_data["shards"] > 0:
            # Add shards to recipient
            recipient_shards = recipient_data.get('shards', 0) + gift_data["shards"]
            
            # Update recipient data
            update_user(ctx.author.id, "shards", recipient_shards)
            
        # Create gift opened embed
        embed = discord.Embed(
            title="🎁 Gift Opened!",
            description=f"You have opened a gift from <@{gift_data['sender_id']}>!",
            color=discord.Color.green()
        )
        
        # Add gift details
        gift_details = []
        if gift_data["card"]:
            card = gift_data["card"]
            gift_details.append(f"Card: {card.get('name', 'Unknown')} (ID: {card.get('global_id', 'N/A')})")
            
        if gift_data["gold"] > 0:
            gift_details.append(f"Gold: {gift_data['gold']}")
            
        if gift_data["shards"] > 0:
            gift_details.append(f"Shards: {gift_data['shards']}")
            
        embed.add_field(name="Gift Contents", value="\n".join(gift_details), inline=False)
        
        # Add message if provided
        if gift_data["message"]:
            embed.add_field(name="Message", value=gift_data["message"], inline=False)
            
        # Send gift opened notification
        await ctx.send(embed=embed)
        
        # Remove the gift from pending gifts
        self.pending_gifts.pop(gift_id, None)
        
        # Try to notify the sender
        try:
            sender = await self.bot.fetch_user(gift_data["sender_id"])
            if sender:
                sender_embed = discord.Embed(
                    title="🎁 Gift Opened!",
                    description=f"{ctx.author.mention} has opened your gift!",
                    color=discord.Color.green()
                )
                
                sender_embed.add_field(name="Gift Contents", value="\n".join(gift_details), inline=False)
                
                await sender.send(embed=sender_embed)
        except:
            # Ignore errors when trying to notify the sender
            pass

    @commands.command(aliases=['og', 'go', 'opengift'])
    async def giftopen(self, ctx):
        """Open a pending gift"""
        # Check if the user has any pending gifts
        user_gifts = []
        for gift_id, gift_data in self.pending_gifts.items():
            if gift_data["recipient_id"] == ctx.author.id:
                user_gifts.append((gift_id, gift_data))
                
        if not user_gifts:
            await ctx.send("You don't have any pending gifts!")
            return
            
        # If there's only one gift, open it
        if len(user_gifts) == 1:
            gift_id, _ = user_gifts[0]
            await self.process_gift(gift_id, ctx)
            return
            
        # If there are multiple gifts, let the user choose which one to open
        embed = discord.Embed(
            title="🎁 Pending Gifts",
            description="You have multiple pending gifts. Please choose which one to open:",
            color=discord.Color.purple()
        )
        
        for i, (gift_id, gift_data) in enumerate(user_gifts, 1):
            sender = await self.bot.fetch_user(gift_data["sender_id"])
            sender_name = sender.display_name if sender else "Unknown"
            
            gift_details = []
            if gift_data["card"]:
                card = gift_data["card"]
                gift_details.append(f"Card: {card.get('name', 'Unknown')}")
                
            if gift_data["gold"] > 0:
                gift_details.append(f"Gold: {gift_data['gold']}")
                
            if gift_data["shards"] > 0:
                gift_details.append(f"Shards: {gift_data['shards']}")
                
            embed.add_field(
                name=f"{i}. Gift from {sender_name}",
                value="\n".join(gift_details),
                inline=False
            )
            
        embed.set_footer(text="Type '!og <number>' to open a specific gift.")
        
        await ctx.send(embed=embed)

    @commands.command(aliases=['ogn'])
    async def giftopennum(self, ctx, number: int):
        """Open a specific pending gift by number"""
        # Check if the user has any pending gifts
        user_gifts = []
        for gift_id, gift_data in self.pending_gifts.items():
            if gift_data["recipient_id"] == ctx.author.id:
                user_gifts.append((gift_id, gift_data))
                
        if not user_gifts:
            await ctx.send("You don't have any pending gifts!")
            return
            
        # Check if the number is valid
        if number < 1 or number > len(user_gifts):
            await ctx.send(f"Invalid gift number! You have {len(user_gifts)} pending gifts.")
            return
            
        # Open the specified gift
        gift_id, _ = user_gifts[number - 1]
        await self.process_gift(gift_id, ctx)

    @commands.command(aliases=['gift'])
    async def gift_item(self, ctx, recipient: discord.Member):
        if recipient == ctx.author:
            await ctx.send("You can't gift items to yourself!")
            return
            
        if recipient.bot:
            await ctx.send("You can't gift items to a bot!")
            return
            
        # Create and send the gift modal
        modal = GiftModal(ctx.author, recipient, self.bot)
        await ctx.send("Please fill out the gift form:", view=discord.ui.View().add_item(
            discord.ui.Button(label="Open Gift Form", style=discord.ButtonStyle.primary, custom_id="gift_form")
        ))
        
        # Wait for the button interaction
        def check(interaction):
            return (interaction.data.get("custom_id") == "gift_form" and 
                    interaction.user.id == ctx.author.id)
            
        try:
            interaction = await self.bot.wait_for("interaction", check=check, timeout=60)
            await interaction.response.send_modal(modal)
        except asyncio.TimeoutError:
            await ctx.send("Gift form timed out. Please try again.")

async def setup(bot):
    try:
        await bot.add_cog(TradeCog(bot))
        print("Trade cog loaded successfully")
    except Exception as e:
        print(f"Error loading Trade cog: {e}")
        raise