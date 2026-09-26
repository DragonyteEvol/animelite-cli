from dataclasses import dataclass


@dataclass
class Anime:
    sitio: str
    titulo: str
    slug: str
    url: str = ""


@dataclass
class Episodio:
    numero: int
    url: str = ""


@dataclass
class Stream:
    host: str
    url: str
    referer: str = ""
    tipo: str = ""

    def __repr__(self):
        return f"<Stream {self.host} {self.tipo} {self.url[:90]}>"


@dataclass
class Embed:
    host: str
    url: str
    pagina: str = ""