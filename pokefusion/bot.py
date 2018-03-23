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
bot = commands.Bot(command_prefix="!")
last_queries = {}


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
        await ctx.send(f"Current language : `{lang.value}`")
    else:
        try:
            lang = pokedex.Language(lang.lower())
            db.update_guild(ctx.guild, name=ctx.guild.name, lang=lang.value)
            await ctx.send(f"Set language : `{lang.value}`")
        except ValueError:
            param = "/".join([lang.value for lang in pokedex.Language])
            await ctx.send(f"Use `!lang [{param}]`")


@bot.command(aliases=["Fusion", "f", "F"])
async def fusion(ctx, head="random", body="random"):
    guild = db.find_guild(ctx.guild)
    if guild:
        lang = pokedex.Language(guild['lang'])
    else:
        lang = pokedex.Language.DEFAULT
        db.update_guild(ctx.guild, lang=lang.value, name=ctx.guild.name)
    try:
        head_id, head = dex.resolve(head, lang)
        body_id, body = dex.resolve(body, lang)
    except KeyError:
        # TODO : Fuzzy search : try to guess what the user meant to type ?
        # Example :
        #   [User] !f bulbasuar mew
        #   [Bot] Did you mean `!f bulbasaur mew` ? If so, type `yes`
        #   [User] yes
        #   [Bot] [Image]
        return
    last_queries[ctx.message.channel] = head, body
    url = f"http://images.alexonsager.net/pokemon/fused/{body_id}/{body_id}.{head_id}.png"
    color = Color(utils.get_dominant_color(url))
    embed = discord.Embed(title="PokéFusion", url="https://fr.pokemon.alexonsager.net/", color=color)
    embed.add_field(name="Head", value=head.title(), inline=True)
    embed.add_field(name="Body", value=body.title(), inline=True)
    embed.set_image(url=url)
    await ctx.send(embed=embed)


@bot.command(aliases=["Swap", "s", "S"])
async def swap(ctx):
    if ctx.channel in last_queries:
        head, body = last_queries[ctx.channel]
        await ctx.invoke(fusion, head=body, body=head)


@bot.command(aliases=["Pokemon", "p", "P"])
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


@bot.command()
async def debug(ctx, expr):
    if bot.is_owner(ctx.author):
        await ctx.send(eval(expr))
    else:
        await ctx.send("**Nice try**")


@bot.command()
async def clear(ctx, amount: int = 5):
    ctx.message.delete()
    messages = []
    async for m in ctx.channel.history().filter(lambda m: m.author == bot.user):
        if len(messages) == amount:
            break
        messages.append(m)
    await ctx.channel.delete_messages(messages)


@bot.command()
async def changelog(ctx):
    changelog = f"```md\n{utils.get_changelog()}\n```"
    await ctx.send(changelog)


@bot.event
async def on_ready():
    print("Successfully logged in as {0} (ID {0.id})".format(bot.user))


bot.run(utils.get_token())
