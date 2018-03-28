import asyncio
import datetime
import os
import sys

import discord
from discord.colour import Color
from discord.ext import commands

import database
import pokedex
import utils

os.chdir(sys.path[0])

db = database.Database()
dex = pokedex.Pokedex()
bot = commands.Bot(command_prefix="!", case_insensitive=True)
last_queries = {}
oauth_url = "https://discordapp.com/oauth2/authorize?client_id={}&permissions=124992&scope=bot"


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.guild)
async def lang(ctx, lang=None):
    if lang is None:
        guild = db.find_guild(ctx.guild)
        if guild:
            lang = pokedex.Language(guild['lang'])
        else:
            lang = pokedex.Language.DEFAULT
            db.update_guild(ctx.guild, lang=lang.value, name=ctx.guild.name)
        await ctx.send(f"Current Pokedex language : `{lang.value}`")
    elif ctx.author.permissions_in(ctx.channel).manage_guild or bot.is_owner(ctx.author):
        try:
            lang = pokedex.Language(lang.lower())
            db.update_guild(ctx.guild, name=ctx.guild.name, lang=lang.value)
            await ctx.send(f"Set Pokedex language : `{lang.value}`")
        except ValueError:
            param = "/".join([lang.value for lang in pokedex.Language])
            await ctx.send(f"Use `!lang [{param}]`")


@bot.command(aliases=["f"])
async def fusion(ctx, head="?", body="?"):
    guild = db.find_guild(ctx.guild)
    if guild:
        lang = pokedex.Language(guild['lang'])
    else:
        lang = pokedex.Language.DEFAULT
        db.update_guild(ctx.guild, lang=lang.value, name=ctx.guild.name)

    head_result = dex.resolve(head, lang)
    body_result = dex.resolve(body, lang)
    if None in (head_result, body_result):
        head_guess = dex.guess(head, lang)[0] if head_result is None else head
        body_guess = dex.guess(body, lang)[0] if body_result is None else body
        body_tmp = body_guess if body_guess not in pokedex.Pokedex.RANDOM_QUERIES else ""
        desc = f"Did you mean   **{bot.command_prefix}f {head_guess} {body_tmp}**   ?\n\n".replace(" ** ", "** ")
        desc += "To proceed, type **yes**."
        embed = discord.Embed(description=desc, color=Color.dark_red())
        embed.set_thumbnail(url="https://i.imgur.com/Rcys72H.png")
        await ctx.send(embed=embed)
        check = lambda m: m.author == ctx.author and utils.yes(m.content) and m.channel == ctx.channel
        try:
            await bot.wait_for("message", check=check, timeout=60)
        except asyncio.TimeoutError:
            pass
        else:
            await ctx.invoke(fusion, head=head_guess, body=body_guess)
    else:
        last_queries[ctx.message.channel] = head, body
        url = f"http://images.alexonsager.net/pokemon/fused/{body_result[0]}/{body_result[0]}.{head_result[0]}.png"
        color = Color(utils.get_dominant_color(url))
        embed = discord.Embed(title="PokéFusion", url="https://fr.pokemon.alexonsager.net/", color=color)
        embed.add_field(name="Head", value=head_result[1].title(), inline=True)
        embed.add_field(name="Body", value=body_result[1].title(), inline=True)
        embed.set_image(url=url)
        await ctx.send(embed=embed)


@bot.command(aliases=["s"])
async def swap(ctx):
    if ctx.channel in last_queries:
        head, body = last_queries[ctx.channel]
        await ctx.invoke(fusion, head=body, body=head)


@bot.command(aliases=["p"])
async def pokemon(ctx, pkmn="random"):
    guild = db.find_guild(ctx.guild)
    if guild:
        lang = pokedex.Language(guild['lang'])
    else:
        lang = pokedex.Language.DEFAULT
        db.update_guild(ctx.guild, lang=lang.value, name=ctx.guild.name)
    dex_num, pkmn = dex.resolve(pkmn, lang)
    url = f"http://images.alexonsager.net/pokemon/{dex_num}.png"
    color = Color(utils.get_dominant_color(url))
    embed = discord.Embed(title=pkmn.title(), color=color)
    embed.set_image(url=url)
    await ctx.send(embed=embed)


@bot.command(hidden=True)
async def debug(ctx, expr):
    if bot.is_owner(ctx.author):
        await ctx.send(eval(expr))
    else:
        await ctx.send("**Nice try**")


@bot.command()
async def clear(ctx, amount: int = 5):
    await ctx.message.delete()
    messages = []
    async for m in ctx.channel.history().filter(lambda m: m.author == bot.user):
        if len(messages) == amount:
            break
        messages.append(m)
    await ctx.channel.delete_messages(messages)


@bot.command()
async def inviteme(ctx):
    await ctx.channel.send(oauth_url.format(bot.user.id))


@bot.command()
async def changelog(ctx):
    changelog = f"```md\n{utils.get_changelog()}\n```"
    await ctx.send(changelog)


@bot.event
async def on_guild_join(guild):
    now = datetime.datetime.now()
    channel = guild.text_channels[0]
    guild_db = db.find_guild(guild)
    if guild_db:
        # Might not be our first time in this guild
        lang = pokedex.Language(guild_db['lang'])
        db.update_guild(guild, lang=lang.value, name=guild.name, rejoined_at=now)
        await channel.send(f"Welcome back !\nCurrent Pokedex language : `{lang.value}`")
    else:
        lang = pokedex.Language.DEFAULT
        db.update_guild(guild, lang=lang.value, name=guild.name, joined_at=now)
        param = "/".join([lang.value for lang in pokedex.Language])
        message = "Thank you for adding PokeFusion to your server !\n"
        message += f"Current Pokedex language : `{lang.value}`    (use `!lang [{param}]` to change it)."
        await channel.send(message)


@bot.event
async def on_ready():
    print("Successfully logged in as {0} (ID {0.id})".format(bot.user))


bot.run(utils.get_token())
