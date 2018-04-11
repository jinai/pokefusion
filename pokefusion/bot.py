import asyncio
import datetime
import logging
import os
import random
import sys

import discord
from discord.colour import Color
from discord.ext import commands
from selenium import webdriver
from selenium.common.exceptions import UnexpectedAlertPresentException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.remote_connection import LOGGER

import database
import pokedex
import utils

os.chdir(sys.path[0])

db = database.Database()
dex = pokedex.Pokedex()
bot = commands.Bot(command_prefix=os.environ["COMMAND_PREFIX"], case_insensitive=True)

LOGGER.setLevel(logging.WARNING)
chrome_bin = os.environ['GOOGLE_CHROME_SHIM']
chrome_options = Options()
chrome_options.binary_location = chrome_bin
chrome_options.add_argument("--headless")
chrome_options.add_argument("--log-level=3")
chrome = webdriver.Chrome(chrome_options=chrome_options, executable_path="chromedriver")

last_queries = {}
oauth_url = "https://discordapp.com/oauth2/authorize?client_id={client_id}&permissions=124992&scope=bot"


# TODO : Refactor this huge mess


@bot.before_invoke
async def log(ctx):
    ts = utils.get_timestamp()
    print(f"{ts} {ctx.message.content:<20} in '{ctx.guild}/{ctx.channel}'")


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
            await ctx.send(f"Use `{os.getenv['COMMAND_PREFIX']}lang [{param}]`")


@bot.command(aliases=["f"])
async def fusion(ctx, head="?", body="?", color="0"):
    guild = db.find_guild(ctx.guild)
    if guild:
        lang = pokedex.Language(guild['lang'])
    else:
        lang = pokedex.Language.DEFAULT
        db.update_guild(ctx.guild, lang=lang.value, name=ctx.guild.name)

    head_result = dex.resolve(utils.ensure_int(head), lang)
    body_result = dex.resolve(utils.ensure_int(body), lang)
    color_result = dex.resolve(utils.ensure_int(color), lang)
    if None in (head_result, body_result, color_result):
        head_guess = dex.guess(head, lang)[0] if head_result is None else head
        body_guess = dex.guess(body, lang)[0] if body_result is None else body
        color_guess = dex.guess(color, lang)[0] if color_result is None else color
        body_tmp = body_guess
        color_tmp = color_guess if color_guess != "0" else ""
        if body_tmp in pokedex.Pokedex.RANDOM_QUERIES and not color_tmp:
            body_tmp = ""
        cmd = utils.strict_whitespace(f"**{bot.command_prefix}f {head_guess} {body_tmp} {color_tmp}**")
        desc = f"Did you mean   {cmd}   ?\n\nType **yes** to proceed, or **no** to cancel."
        embed = discord.Embed(description=desc, color=Color.light_grey())
        embed.set_thumbnail(url="https://i.imgur.com/Rcys72H.png")
        embed.set_footer(text=f"Requested by {ctx.author}")
        await ctx.send(embed=embed)
        check = lambda m: m.author == ctx.author and m.channel == ctx.channel and utils.yes_or_no(m.content)
        try:
            reply = await bot.wait_for("message", check=check, timeout=60)
        except asyncio.TimeoutError:
            pass
        else:
            if reply.content.lower() == "yes":
                await ctx.invoke(fusion, head=head_guess, body=body_guess, color=color_guess)
    else:
        h_id, h = head_result
        b_id, b = body_result
        c_id, c = color_result
        last_queries[ctx.message.channel] = h, b, c

        script = f"http://pokefusion.japeal.com/PKMColourV5.php?ver=3.2&p1={h_id}&p2={b_id}&c={c_id}"
        try:
            chrome.get(script)
            data = chrome.find_element_by_id("image1").get_attribute("src").split(",", 1)[1]
        except UnexpectedAlertPresentException:
            chrome.switch_to.alert.dismiss()
        else:
            if c_id == "0":
                filename = f"fusion_{h_id.zfill(3)}{h}_{b_id.zfill(3)}{b}.png"
            else:
                filename = f"fusion_{h_id.zfill(3)}{h}_{b_id.zfill(3)}{b}_{c_id.zfill(3)}{c}.png"
            fp = utils.base64_to_file(data)
            f = discord.File(fp=fp, filename=filename)
            color = Color.from_rgb(*utils.get_dominant_color(fp))
            fp.seek(0)
            share_url = f"http://pokefusion.japeal.com/{b_id}/{h_id}/{c_id}"
            embed = discord.Embed(title="PokéFusion", url=share_url, color=color)
            embed.add_field(name="Head", value=f"{h.title()} ({h_id.zfill(3)})", inline=True)
            embed.add_field(name="Body", value=f"{b.title()} ({b_id.zfill(3)})", inline=True)
            if c_id != "0":
                embed.add_field(name="Palette", value=f"{c.title()} ({c_id.zfill(3)})")
            embed.set_image(url=f"attachment://{filename}")
            embed.set_footer(text=f"Requested by {ctx.author}")
            await ctx.send(embed=embed, file=f)


@bot.command(aliases=["old"])
async def oldfusion(ctx, head="?", body="?"):
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
        desc = f"Did you mean   **{bot.command_prefix}f {head_guess} {body_tmp}**   ?\n".replace(" ** ", "** ")
        desc += "Type **yes** to proceed, or **no** to cancel."
        embed = discord.Embed(description=desc, color=Color.light_grey())
        embed.set_thumbnail(url="https://i.imgur.com/Rcys72H.png")
        embed.set_footer(text=f"Requested by {ctx.author}")
        await ctx.send(embed=embed)
        check = lambda m: m.author == ctx.author and m.channel == ctx.channel and utils.yes_or_no(m.content)
        try:
            reply = await bot.wait_for("message", check=check, timeout=60)
        except asyncio.TimeoutError:
            pass
        else:
            if reply.lower() == "yes":
                await ctx.invoke(fusion, head=head_guess, body=body_guess)
    else:
        last_queries[ctx.message.channel] = head_result[1], body_result[1]
        url = f"http://images.alexonsager.net/pokemon/fused/{body_result[0]}/{body_result[0]}.{head_result[0]}.png"
        color = Color.from_rgb(*utils.get_dominant_color(utils.url_to_file(url)))
        embed = discord.Embed(title="PokéFusion", url="https://fr.pokemon.alexonsager.net/", color=color)
        embed.add_field(name="Head", value=head_result[1].title(), inline=True)
        embed.add_field(name="Body", value=body_result[1].title(), inline=True)
        embed.set_image(url=url)
        embed.set_footer(text=f"Requested by {ctx.author}")
        await ctx.send(embed=embed)


@bot.command(aliases=["s"])
async def swap(ctx):
    if ctx.channel in last_queries:
        head, body, color = last_queries[ctx.channel]
        await ctx.invoke(fusion, head=body, body=head, color=color)


@bot.command(aliases=["t"])
async def totem(ctx, user: discord.User = None):
    guild = db.find_guild(ctx.guild)
    if guild:
        lang = pokedex.Language(guild['lang'])
    else:
        lang = pokedex.Language.DEFAULT
        db.update_guild(ctx.guild, lang=lang.value, name=ctx.guild.name)

    if user:
        random.seed(user.id)
        totem_of = user.display_name
        avatar_url = user.avatar_url
    else:
        random.seed(ctx.author.id)
        totem_of = ctx.author.display_name
        avatar_url = ctx.author.avatar_url

    head = str(random.randint(pokedex.Pokedex.MIN_ID, pokedex.Pokedex.MAX_ID))
    body = str(random.randint(pokedex.Pokedex.MIN_ID, pokedex.Pokedex.MAX_ID))
    head_id, head = dex.resolve(head, lang)
    body_id, body = dex.resolve(body, lang)
    last_queries[ctx.message.channel] = head, body
    url = f"http://images.alexonsager.net/pokemon/fused/{body_id}/{body_id}.{head_id}.png"
    color = Color(utils.get_dominant_color(url))
    embed = discord.Embed(title=f"Totem of {totem_of}", color=color)
    embed.set_thumbnail(url=avatar_url)
    embed.add_field(name="Head", value=head.title(), inline=True)
    embed.add_field(name="Body", value=body.title(), inline=True)
    embed.set_image(url=url)
    await ctx.send(embed=embed)


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
    if ctx.author.permissions_in(ctx.channel).manage_messages or bot.is_owner(ctx.author):
        await ctx.message.delete()
        messages = []
        async for m in ctx.channel.history().filter(lambda m: m.author == bot.user):
            if len(messages) == amount:
                break
            messages.append(m)
        await ctx.channel.delete_messages(messages)


@bot.command()
async def invite(ctx):
    await ctx.channel.send(oauth_url.format(client_id=bot.user.id))


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
        message += f"Current Pokedex language : `{lang.value}`    (use `{os.getenv['COMMAND_PREFIX']}lang [{param}]` to change it)."
        await channel.send(message)


@bot.event
async def on_ready():
    ts = utils.get_timestamp()
    print(f"{ts} Logged in as {bot.user} (ID {bot.user.id})")
    print("=" * 50)


bot.run(utils.get_token())
