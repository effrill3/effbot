import os, time
import discord
import asyncio
from discord.ext import commands
from random import choice as rndchoice
from discord.ext.commands import DisabledCommand
class RestrictedWhiteListError(Exception):
    pass
class RestrictedBlackListError(Exception):
    pass

def is_curator_or_higher():
    async def predicate(ctx):
        msg = ctx.message
        g = await ctx.bot.cogs['Helpers'].get_record('server', msg.guild.id)
        #print([a.id for a in msg.author.roles])
        u_roles = [a.id for a in msg.author.roles]
        is_admin = g['config'].role_admin in u_roles
        is_mod = g['config'].role_moderator in u_roles
        is_cur = g['config'].role_curator in u_roles
        if is_admin or is_mod or is_curator:
            return True
        else:
            await ctx.send('You need to be curator+ in order to use this command.')
            return False
    return commands.check(predicate)


class CurationCog():
    """docstring for CurationCog"""
    def __init__(self, bot):
        
        self.bot = bot
        self.helpers = self.bot.get_cog('Helpers')

    @commands.group(pass_context=True, name="curation")
    async def curation(self, ctx):
        pass

    @commands.command(pass_context=True, name="whitelist", aliases=["wl"])
    @is_curator_or_higher()
    async def whitelist(self, ctx, command: str, channels: str=''):
        chans = channels.split(',')
        m = ctx.message
        g = await self.helpers.get_record('server', m.guild.id)
        if not hasattr(g['config'], 'restrictions'):
            setattr(g['config'], 'restrictions', [])
        if command.strip().lower() in self.bot.all_commands:
            chans = [await self.helpers.get_obj(
                m.guild, 'channel', 'name', c
            ) for c in chans if not c.isdigit()] + [
                int(c) for c in chans if c.isdigit()
            ]
        
            command = self.bot.all_commands[command.strip().lower()].name
            g['config'].restrictions = [r for r in g['config'].restrictions
                              if not r['command'] == command]
            g['config'].restrictions.append({'kind': 'wl', 'command': command,
                                   'channels': [c for c in chans]})

    @commands.command(pass_context=True, name="blacklist", aliases=["bl"])
    @is_curator_or_higher()
    async def blacklist(self, ctx, command: str, channels: str=''):
        chans = channels.split(',')
        m = ctx.message
        g = await self.helpers.get_record('server', m.guild.id)
        if not hasattr(g['config'], 'restrictions'):
            setattr(g['config'], 'restrictions', [])
        if command.strip().lower() in self.bot.all_commands:
            chans = [await self.helpers.get_obj(
                m.guild, 'channel', 'name', c
            ) for c in chans if not c.isdigit()] + [
                int(c) for c in chans if c.isdigit()
            ]
        
            command = self.bot.all_commands[command.strip().lower()].name
            g['config'].restrictions = [r for r in g['config'].restrictions
                              if not r['command'] == command]
            g['config'].restrictions.append({'kind': 'bl', 'command': command,
                                   'channels': [c for c in chans]})

    @commands.command(pass_context=True, name="quote")
    @is_curator_or_higher()
    async def quote(self, ctx, channel: str, message_id: str):
        m = ctx.message
        g = await self.helpers.get_record('server', m.guild.id)
        q = g['config'].chan_quotes
        if not q:
            await ctx.send('Oops, ask an admin to set up a quotes channel')
            return
        result = await self.helpers.get_obj(m.guild, 'channel', 'name', channel)
        if result and message_id.isdigit():
            c = self.bot.get_channel(result)
            message = await c.get_message(message_id)
            if message:
                a = message.author
                embed = await self.helpers.build_embed(message.content, a.color)
                embed.set_author(name=f'{a.name}#{a.discriminator}', icon_url=a.avatar_url_as(format='jpeg'))
                embed.add_field(name="In", value=f'<#{c.id}>')
                embed.add_field(name="Author", value=f'<@{a.id}>')
                await self.bot.get_channel(q).send(embed=embed)
                await ctx.send('Quote added successfully!')
            else:
                await ctx.send('Did not find that message, sorry!')
        else:
            await ctx.send('Check you supplied a valid channel name+message id')

    async def curate_channels(self, message):
        if hasattr(message, 'guild'):
            m = message
            c, guild, a = m.channel, m.guild, m.author
            g = await self.helpers.get_record('server', guild.id)
            if g and c.id in g['config'].chan_curated:
                if not m.embeds and not m.attachments:
                    await m.delete()
                    await self.bot.get_user(a.id).send(
                        (f'Hey {a.name}, <#{c.id}> is a curated channel,'
                          ' meaning you can only send links or pictures.')
                    )

    async def quote_react(self, reaction, user):
        m = reaction.message
        if hasattr(m, 'guild') and reaction.emoji == "⭐":
            g = await self.helpers.get_record('server', m.guild.id)
            u = user
            q = g['config'].chan_quotes
            u_roles = [a.id for a in u.roles]
            is_admin = g['config'].role_admin in u_roles
            is_mod = g['config'].role_moderator in u_roles
            is_cur = g['config'].role_curator in u_roles
            if is_admin or is_mod or is_curator:
                a = m.author
                c = m.channel
                e = await self.helpers.build_embed(m.content, a.color)
                e.set_author(name=f'{a.name}#{a.discriminator}', icon_url=a.avatar_url_as(format='jpeg'))
                e.add_field(name="In", value=f'<#{c.id}>')
                e.add_field(name="Author", value=f'<@{a.id}>')
                await self.bot.get_channel(q).send(embed=e)


    def check_restricted(self, kind, channel, channels):
        if kind == 'wl' and channel not in channels:
            raise RestrictedWhiteListError
        elif kind == 'bl' and channel in channels:
            raise RestrictedBlackListError
    
    async def check_restrictions(self, ctx):
        if hasattr(ctx.message, 'guild'):
            # if not hasattr(ctx,'was_limited'):
            c = ctx.command
            m = ctx.message
            g = await self.helpers.get_record('server', m.guild.id)
            chan = ctx.channel
            if hasattr(g['config'], 'restrictions'):
                restricted = [r for r in g['config'].restrictions
                              if r['command']==c.name]
                if len(restricted) > 0:
                    
                    r = restricted[0]
                    try:
                        self.check_restricted(r['kind'], chan.id, r['channels'])
                    except RestrictedBlackListError:
                        await ctx.send('Sorry, that command is restricted and '
                                       'cannot be used here.')
                        setattr(ctx, 'was_limited', True)
                        return False
                    except RestrictedWhiteListError:
                        await ctx.send('Sorry, that command is restricted and '
                                       'can only be used in: {}.'.format(
                                        ', '.join([f'<#{c}>' for c in r['channels']])
                                       ))
                        setattr(ctx, 'was_limited', True)
                        return False
            return True

def setup(bot):
    cog = CurationCog(bot)
    bot.add_listener(cog.curate_channels, "on_message")
    bot.add_check(cog.check_restrictions, call_once=False)
    bot.add_listener(cog.quote_react, "on_reaction_add")
    bot.add_cog(cog)
