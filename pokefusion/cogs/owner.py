import io
import logging
import textwrap
import traceback
from contextlib import redirect_stdout
from typing import Annotated

from discord import Member
from discord.ext import commands
from discord.ext.commands import CommandError, NotOwner

from pokefusion import utils
from pokefusion.bot.context import Context, Reply
from pokefusion.bot.converters import ModuleConverter
from pokefusion.bot.pokefusion import PokeFusion
from pokefusion.db import models
from pokefusion.db.models import Settings, User
from .cogutils import confirm_prompt, embed_factory
from .scheduler import NOTIF_CHANNELS

logger = logging.getLogger(__name__)


class Owner(commands.Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot: PokeFusion) -> None:
        self.bot = bot
        self.last_eval = None

    async def cog_check(self, ctx: Context) -> bool:
        return await commands.is_owner().predicate(ctx)

    async def cog_command_error(self, ctx: Context, error: CommandError) -> None:
        if isinstance(error, NotOwner):
            await ctx.send("Owner only.")

    @commands.command(aliases=["mm"])
    async def maintenance(self, ctx: Context, new_state: bool | None = None) -> None:
        if new_state is None:
            current_state = Settings.is_maintenance()
            await ctx.send(f"Maintenance mode is {['off', 'on'][current_state]}.")
        else:
            Settings.set_maintenance(new_state)
            await ctx.send(f"Maintenance mode is now {['off', 'on'][new_state]}.")

    @commands.command(aliases=["rr"])
    async def reroll(self, ctx: Context, target: Member | None = None):
        target = target or ctx.author
        description = f"Reroll {target.display_name}'s totem?"

        reply = await confirm_prompt(ctx, description)

        if reply is Reply.Yes:
            self.bot.totem_service.reroll_totem(target.id)

    @commands.command(aliases=["rrg", "rr_global", "rerall"])
    async def reroll_global(self, ctx: Context):
        description = f"Reroll **all** totems for **every** server?"

        reply = await confirm_prompt(ctx, description)

        if reply is Reply.Yes:
            self.bot.totem_service.reroll_all_totems()

    @commands.command(aliases=["give_fr"])
    async def give_freererolls(self, ctx: Context, amount: int = 1, target: Member | None = None):
        recipient = "everyone" if target is None else target.display_name
        rerolls = "reroll" if amount == 1 else "rerolls"
        description = f"Give **{amount} free {rerolls}** to **{recipient}**?"

        reply = await confirm_prompt(ctx, description)

        if reply is Reply.Yes:
            if target is None:
                User.add_free_rerolls_to_all(amount)
            else:
                User.add_free_rerolls(target.id, amount)

    @commands.command(aliases=["spu"])
    async def sprite_pack_update(self, ctx: Context, free_rerolls: int = 0) -> None:
        title = "Sprite Pack Update"
        description = (
            "The latest sprite pack was imported:\n"
            "```asciidoc\n"
            "Sprite pack :: 127_June_2026\n"
            "Timestamp   :: 2026-08-02 15:36:00\n"
            "Changes     :: +2900/-7 custom fusions and +2 eggs\n"
            "```\n"
        )

        if free_rerolls > 0:
            rerolls = "reroll" if free_rerolls == 1 else "rerolls"
            description += (
                f"⚠️ All Totems have been reset️. As compensation, everyone received "
                f"**+{free_rerolls} free {rerolls}**! Check how many you have with `{ctx.clean_prefix}fru`"
            )

        preview, files = embed_factory(
            title=title,
            description=description,
            color=ctx.bot.main_color,
            thumbnail=ctx.me.display_avatar.url
        )

        await ctx.send(embed=preview, files=files)

        warning = "Send the previewed embed to **all** notification subscribers?"
        reply = await confirm_prompt(ctx, warning, color=ctx.bot.main_color)

        if reply is Reply.Yes:
            if free_rerolls > 0:
                User.add_free_rerolls_to_all(free_rerolls)
                self.bot.totem_service.reroll_all_totems()

            for channel_id in NOTIF_CHANNELS:
                channel = self.bot.get_channel(channel_id)

                if channel:
                    embed, files = embed_factory(
                        title=title,
                        description=description,
                        color=ctx.bot.main_color,
                        thumbnail=self.bot.user.display_avatar.url
                    )

                    await channel.send(embed=embed, files=files)

    @commands.command()
    async def say(self, ctx: Context, *, message: str) -> None:
        await ctx.send(message)

    @commands.command()
    async def load(self, ctx, *, module: Annotated[str, ModuleConverter]) -> None:
        try:
            await self.bot.load_extension(module)
        except commands.ExtensionError as e:
            await ctx.send(f'{e.__class__.__name__}: {e}')
        else:
            await ctx.tick(True)

    @commands.command()
    async def unload(self, ctx, *, module: Annotated[str, ModuleConverter]) -> None:
        try:
            await self.bot.unload_extension(module)
        except commands.ExtensionError as e:
            await ctx.send(f'{e.__class__.__name__}: {e}')
        else:
            await ctx.tick(True)

    @commands.command()
    async def reload(self, ctx, *, module: Annotated[str, ModuleConverter]) -> None:
        try:
            await self.bot.reload_extension(module)
        except commands.ExtensionError as e:
            await ctx.send(f'{e.__class__.__name__}: {e}')
        else:
            await ctx.tick(True)

    @commands.command(aliases=["eval"])
    async def sudo(self, ctx: Context, *, body: str) -> None:
        env = {
            "self": self,
            "bot": self.bot,
            "models": models,
            "totem": self.bot.totem_service,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "guild": ctx.guild,
            "message": ctx.message,
            "_": self.last_eval
        }

        env.update(globals())

        body = utils.cleanup_code(body)
        stdout = io.StringIO()

        to_compile = f"async def _eval():\n{textwrap.indent(body, '  ')}"

        try:
            exec(to_compile, env)
        except Exception as e:
            await ctx.safe_send(f"```py\n{e.__class__.__name__}: {e}\n```")
            return

        func = env["_eval"]
        # noinspection PyBroadException
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception:
            value = stdout.getvalue()
            logger.error(traceback.format_exc())
            await ctx.safe_send(f"```py\n{value}{traceback.format_exc()}\n```")
        else:
            value = stdout.getvalue()
            await ctx.tick(True)

            if ret is None:
                if value:
                    await ctx.safe_send(f"```py\n{value}\n```")
            else:
                self.last_eval = ret
                await ctx.safe_send(f"```py\n{value}{ret}\n```")


async def setup(bot: PokeFusion) -> None:
    await bot.add_cog(Owner(bot))
