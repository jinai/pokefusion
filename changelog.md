# Changelog

## 2.0.0 (2025-07-16)
* Complete refactor of code and folder structure (cogs, assets, config, tools, ...)
* Use fusions from Pokémon Infinite Fusion
* Add mini guessing games (by description, sprite, fusion, ...)
* Remove color palette (not compatible anymore)

## 1.0 (2018-04-12)
* Added generations II, III and IV + Victini (from #1 to #494).
* Fusions can now use the color palette of a third Pokémon. Usage: `!f [head] [body] [color]`

## 0.8 (2018-03-29)
* Added `!totem [@user]`.
* Fixed edge case in embed color calculations that would make some fusions unresponsive.

## 0.7 (2018-03-28)
* Typos are detected in `!fusion`. Users have the possibility to apply the most similar names instead.

## 0.6 (2018-03-23)
* Added `!lang [fr/en/de]` to set the pokedex language (default is French). You need the `Manage Server` permission to change it.
* Fixed embed colors not always being accurate.
* Added `!invite` to get the invite link.

## 0.5 (2018-03-18)
* Each channel has its own history for `!swap`.

## 0.4 (2018-03-13)
* Embed colors now match the most dominant color in the resulting image.

## 0.3 (2018-03-12)
* Added `!swap`.
* Added `!pokemon [id/name]`.

## 0.2 (2018-03-10)
* Added `!clear [amount]` (defaults to `5`).
    
## 0.1 (2018-03-08)
* Initial version: `!fusion [head] [body]`.