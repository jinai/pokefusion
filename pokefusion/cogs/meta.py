from datetime import timedelta

from discord import Permissions
from discord.ext import commands
from discord.utils import oauth_url

from pokefusion.bot import PokeFusion
from pokefusion.context import Context
from .cogutils import base_embed


class Meta(commands.Cog):
    def __init__(self, bot: PokeFusion):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx: Context):
        m = await ctx.send("Measuring ping...")
        elapsed = (m.created_at - ctx.message.created_at) / timedelta(milliseconds=1)
        await m.edit(content=f"Pong! {int(elapsed)}ms.")

    @commands.command()
    async def uptime(self, ctx: Context):
        hours, rem = divmod(int(self.bot.uptime), 3600)
        minutes, seconds = divmod(rem, 60)
        await ctx.send(f"{str(hours).zfill(2)}h{str(minutes).zfill(2)}m{str(seconds).zfill(2)}s")

    @commands.command()
    async def invite(self, ctx):
        perms = Permissions.text()
        perms.use_external_apps = False
        perms.create_public_threads = False
        perms.create_private_threads = False
        perms.send_tts_messages = False
        perms.manage_threads = False
        perms.mention_everyone = False
        perms.send_voice_messages = False
        perms.create_polls = False
        await ctx.send(oauth_url(self.bot.application_id, permissions=perms))

    @commands.command(aliases=["ver", "v"])
    async def version(self, ctx: Context):
        embed, _ = base_embed(ctx, description=(
            "```asciidoc\n"
            "Sprite pack :: 120_November_2025\n"
            "Timestamp   :: 2026-01-08 00:23:00\n"
            "Changes     :: +1203/-17 custom fusions\n"
            "```"
        ))
        await ctx.send(embed=embed)


async def setup(bot: PokeFusion) -> None:
    await bot.add_cog(Meta(bot))
