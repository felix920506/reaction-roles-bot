import discord
import discord.ext.commands

import sqlite3

intents = discord.Intents.default()
intents.reactions = True

bot = discord.Bot(intents=intents)

#
# Load token
#

with open('token.txt', 'r') as tokenfile:
    token = tokenfile.read().strip()

# 
# Init Database
#

dbcon = sqlite3.connect('./database.db')
dbcur = dbcon.cursor()

dbcur.execute('CREATE TABLE IF NOT EXISTS "reactionRoles" ( \
	"message" INTEGER NOT NULL, \
	"emoji" TEXT NOT NULL, \
	"role" INTEGER NOT NULL \
    );')

#
#   Validate Permissions function
#

async def validate_permissions(ctx):

    if not ctx.author.guild_permissions.manage_roles:
        await ctx.respond("You don't have permission to use this command")
        return False
    
    else:
        return True

#
#   Create command group
#

group = bot.create_group("reactionroles", "Commands related to reaction roles")

#
# Logged in message
#

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    print(f'add me to your server using this link: https://discord.com/oauth2/authorize?client_id={bot.user.id}&scope=bot&permissions=268501056')

#
# Handle commands
#

@group.command(description = 'Adds a reaction role to your previous message in this channel')
# @discord.ext.commands.has_permissions(manage_roles = True)
async def add(ctx: discord.commands.context.ApplicationContext,
              emoji: discord.Option(str, description= 'Sticker / Emoji for this reaction role'), 
              role: discord.Option(discord.Role, description= 'Discord Role for this reaction'), 
              ):

    #
    # Validate Permissions
    # 

    if not await validate_permissions(ctx):
        return
    
    #
    # Get message object
    #
    
    channel = ctx.channel
    latestmessage = channel.history(limit=100)
    
    targetmessage = None

    async for message in latestmessage:
        if message.author == ctx.author:
            targetmessage = message
            break
    
    if message is None:
        await ctx.respond('No messages from you were found within the last 100.', ephemeral=True)
        return

    #
    # Validate Emoji
    #

    try:
        await targetmessage.add_reaction(emoji)
    except:
        await ctx.respond('The reaction is invalid or inaccessable to the Bot. Please use a default reaction or a reaction from this Discord server.', ephemeral=True)
        return
    
    sqlargs = {
        'message': targetmessage.id,
        'emoji': emoji,
        'role' : role.id
    }

    dbcur.execute('INSERT INTO reactionRoles (message, emoji, role) VALUES (:message, :emoji, :role)', sqlargs)
    dbcon.commit()

    await ctx.respond('Reaction role registered.' , ephemeral=True)

#
# Delete Command
#

@group.command(description = 'Removes specified reaction role from message')
async def remove(ctx: discord.commands.context.ApplicationContext,
                  message: discord.Option(str, description= 'Message ID of the target message'),
                  emoji: discord.Option(str, description= 'Target Emoji')):
    
    #
    # Validate Permissions
    # 

    if not await validate_permissions(ctx):
        return

    sqlargs = {
        'message': message,
        'emoji': emoji
    }


    dbcur.execute('DELETE FROM reactionRoles WHERE \
                  message = :message AND \
                  emoji = :emoji', sqlargs)
    dbcon.commit()

    await ctx.respond('Reaction role removed (if it existed). Reactions will have to be removed manually due to technical limitations.', ephemeral=True)

#
#   Clear message command
#

@group.command(description = 'Removes all reaction roles from message')
async def clear(ctx: discord.commands.context.ApplicationContext,
                message: discord.Option(str, 'Message ID of the target message')):
    
    if not await validate_permissions(ctx):
        return
    
    sqlargs = {
        'message': message
    }

    dbcur.execute(' DELETE FROM reactionRoles WHERE message = :message', sqlargs)
    dbcon.commit()

    await ctx.respond('All existing reaction roles cleared from message. Reactions will have to be removed manually due to technical limitations.', ephemeral=True)

#
# Handle reaction events
#

@bot.event
async def on_raw_reaction_add(ctx: discord.RawReactionActionEvent):
    if (ctx.member != bot.user) and (ctx.guild_id is not None):
        
        sqlargs = {
            'message': ctx.message_id,
            'emoji': str(ctx.emoji)
        }

        rolequery = dbcur.execute('SELECT role FROM reactionRoles WHERE message = :message AND emoji = :emoji', sqlargs).fetchone()
        
        if rolequery is None:
            return
        else:
            roleID = rolequery[0]

        role = bot.get_guild(ctx.guild_id).get_role(roleID)
        
        await ctx.member.add_roles(role, reason='Reaction Role')
    


if __name__ == '__main__':
    bot.run(token)
