import asyncio
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
async def ping(ctx):
    random.seed(ctx.author.id)
    r = lambda: random.randint(0, 255)
    rgb = (r(), r(), r())
    desc = f"Pong ! {round(bot.latency * 1000)} ms"
    embed = discord.Embed(description=desc, color=Color.from_rgb(*rgb))
    embed.set_footer(text=f"Requested by {ctx.author}")
    await ctx.send(embed=embed)


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
    elif ctx.author.permissions_in(ctx.channel).manage_guild or await bot.is_owner(ctx.author):
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

    head_result = dex.resolve(head, lang)
    body_result = dex.resolve(body, lang)
    color_result = dex.resolve(color, lang) if color != "0" else (color, "")
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
        last_queries[ctx.message.channel] = h_id, b_id, c_id

        script = f"http://pokefusion.japeal.com/PKMColourV5.php?ver=3.2&p1={h_id}&p2={b_id}&c={c_id}"
        try:
            chrome.get(script)
            data = chrome.find_element_by_id("image1").get_attribute("src").split(",", 1)[1]
        except UnexpectedAlertPresentException:
            chrome.switch_to.alert.dismiss()
        else:
            if c_id == "0":
                filename = f"fusion_{h_id}{h}_{b_id}{b}.png"
            else:
                filename = f"fusion_{h_id}{h}_{b_id}{b}_{c_id}{c}.png"
            fp = utils.base64_to_file(data)
            f = discord.File(fp=fp, filename=filename)
            color = Color.from_rgb(*utils.get_dominant_color(fp))
            fp.seek(0)
            share_url = f"http://pokefusion.japeal.com/{b_id}/{h_id}/{c_id}"
            embed = discord.Embed(title="PokéFusion", url=share_url, color=color)
            embed.add_field(name="Head", value=f"{h.title()} #{h_id}", inline=True)
            embed.add_field(name="Body", value=f"{b.title()} #{b_id}", inline=True)
            if c_id != "0":
                embed.add_field(name="Colors", value=f"{c.title()} #{c_id}")
            embed.set_image(url=f"attachment://{filename.replace('(', '').replace(')', '')}")
            embed.set_footer(text=f"Requested by {ctx.author}")
            await ctx.send(embed=embed, file=f)


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

    user = user or ctx.author
    user_db = db.find_user(user)
    settings = db.get_settings()
    rc = user_db['reroll_count'] if user_db else 0
    global_rc = settings['global_rc'] if settings else 100

    random.seed(user.id + rc + global_rc)
    head = str(random.randint(pokedex.Pokedex.MIN_ID, pokedex.Pokedex.MAX_ID))
    body = str(random.randint(pokedex.Pokedex.MIN_ID, pokedex.Pokedex.MAX_ID))
    color = str(random.randint(pokedex.Pokedex.MIN_ID, pokedex.Pokedex.MAX_ID))
    head_id, head = dex.resolve(head, lang)
    body_id, body = dex.resolve(body, lang)
    color_id, color = dex.resolve(color, lang)
    last_queries[ctx.message.channel] = head, body, color

    script = f"http://pokefusion.japeal.com/PKMColourV5.php?ver=3.2&p1={head_id}&p2={body_id}&c={color_id}"
    try:
        chrome.get(script)
        data = chrome.find_element_by_id("image1").get_attribute("src").split(",", 1)[1]
    except UnexpectedAlertPresentException:
        chrome.switch_to.alert.dismiss()
    else:
        if color_id == "0":
            filename = f"fusion_{head_id}{head}_{body_id}{body}.png"
        else:
            filename = f"fusion_{head_id}{head}_{body_id}{body}_{color_id}{color}.png"
        fp = utils.base64_to_file(data)
        f = discord.File(fp=fp, filename=filename)
        c = Color.from_rgb(*utils.get_dominant_color(fp))
        fp.seek(0)
        share_url = f"http://pokefusion.japeal.com/{body_id}/{head_id}/{color_id}"
        embed = discord.Embed(title=f"{user.display_name}'s totem", url=share_url, color=c)
        embed.set_thumbnail(url=user.avatar_url)
        embed.add_field(name="Head", value=f"{head.title()} #{head_id}", inline=True)
        embed.add_field(name="Body", value=f"{body.title()} #{body_id}", inline=True)
        if color_id != "0":
            embed.add_field(name="Colors", value=f"{color.title()} #{color_id}")
        embed.set_image(url=f"attachment://{filename.replace('(', '').replace(')', '')}")
        embed.set_footer(text=f"Requested by {ctx.author}")
        await ctx.send(embed=embed, file=f)


@bot.command(hidden=True, aliases=["reroll"])
async def reroll_totem(ctx, user: discord.User = None, value: int = None):
    if await bot.is_owner(ctx.author):
        user = user or ctx.author
        user_db = db.find_user(user)
        if value is not None:
            count = value
        elif user_db:
            count = user_db['reroll_count'] + 1
        else:
            count = 1
        db.update_user(user, reroll_count=count, name=str(user))
        await ctx.invoke(totem, user=user)
    else:
        m = await ctx.send("**Nice try**")
        await asyncio.sleep(2)
        await ctx.channel.delete_messages((ctx.message, m))


@bot.command(hidden=True, aliases=["renew", "recycle"])
async def reroll_all(ctx, value: int = None):
    if await bot.is_owner(ctx.author):
        desc = f"Reroll **all** totems  ?\n\nType **yes** to proceed, or **no** to cancel."
        embed = discord.Embed(description=desc, color=Color.red())
        embed.set_footer(text=f"Requested by {ctx.author}")
        await ctx.send(embed=embed)
        check = lambda m: m.author == ctx.author and m.channel == ctx.channel and utils.yes_or_no(m.content)
        try:
            reply = await bot.wait_for("message", check=check, timeout=5)
        except asyncio.TimeoutError:
            pass
        else:
            if reply.content.lower() == "yes":
                settings = db.get_settings()
                if value is not None:
                    count = value
                elif settings:
                    count = settings['global_rc'] + 1
                else:
                    count = 101
                db.update_settings(global_rc=count, last_update=utils.now())
    else:
        m = await ctx.send("**Nice try**")
        await asyncio.sleep(2)
        await ctx.channel.delete_messages((ctx.message, m))


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
    color = Color.from_rgb(*utils.get_dominant_color(utils.url_to_file(url)))
    embed = discord.Embed(title=pkmn.title(), color=color)
    embed.set_image(url=url)
    await ctx.send(embed=embed)


@bot.command(hidden=True)
async def debug(ctx, expr):
    if await bot.is_owner(ctx.author):
        try:
            if expr.startswith("await "):
                await ctx.send(await eval(expr))
            await ctx.send(eval(expr))
        except Exception as e:
            await ctx.send(str(e))
    else:
        m = await ctx.send("**Nice try**")
        await asyncio.sleep(2)
        await ctx.channel.delete_messages((ctx.message, m))


@bot.command()
async def clear(ctx, amount: int = 5):
    if ctx.author.permissions_in(ctx.channel).manage_messages or await bot.is_owner(ctx.author):
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
    now = utils.now()
    channel = guild.text_channels[0]
    guild_db = db.find_guild(guild)
    if guild_db:
        # Might not be our first time in this guild
        db.update_guild(guild, name=guild.name, rejoined_at=now)
        await channel.send(f"Welcome back !\nCurrent Pokedex language : `{guild_db['lang']}`")
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
