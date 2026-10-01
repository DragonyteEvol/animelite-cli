"""Adaptadores por fuente.

Cada modulo expone el mismo contrato:
    buscar(query: str) -> list[Anime]
    episodios(anime: Anime) -> list[Episodio]
    embeds(episodio: Episodio) -> list[Embed]
"""
from . import animeflv, jkanime, monoschinos, tioanime

SITIOS = [tioanime, jkanime, animeflv, monoschinos]

__all__ = ["SITIOS", "animeflv", "jkanime", "monoschinos", "tioanime"]