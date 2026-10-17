"""Identidade visual: LOCAIS FIXOS dos arquivos de marca.

Coloque os arquivos oficiais em  app/static/brand/  com EXATAMENTE estes nomes (PNG).
Cada arquivo abaixo já existe como placeholder; basta substituir pelo arquivo real.
O painel /admin/identidade mostra o estado de cada slot.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

BRAND_DIR = Path(__file__).resolve().parent / "static" / "brand"
BRAND_URL = "/static/brand"


@dataclass(frozen=True)
class Slot:
    key: str
    file: str
    width: int
    height: int
    onde: str
    nota: str = ""

    @property
    def url(self) -> str:
        return f"{BRAND_URL}/{self.file}"

    @property
    def path(self) -> Path:
        return BRAND_DIR / self.file


SLOTS: tuple[Slot, ...] = (
    Slot("logo", "logo.png", 480, 96, "Cabeçalho de todas as páginas (exibido com 32 px de altura)", "PNG transparente, para fundo escuro do cabeçalho"),
    Slot("logo_dark", "logo-dark.png", 480, 96, "Reservado: fundos escuros, rodapé e relatórios", "Versão do logo para fundo escuro"),
    Slot("logo_mark", "logo-mark.png", 256, 256, "Reservado: símbolo/ícone isolado (PDF, app)", "Quadrado, transparente"),
    Slot("favicon", "favicon.png", 64, 64, "Aba do navegador", "Quadrado; legível em 16 px"),
    Slot("hero", "hero.png", 900, 1200, "Imagem de destaque nas telas de login e cadastro", "Retrato (3:4)"),
    Slot("empty_state", "empty-state.png", 640, 400, "Imagem de 'lista vazia' (ex.: nenhuma usina)", "Exibida com 240 px de largura"),
    Slot("og_image", "og-image.png", 1200, 630, "Pré-visualização ao compartilhar links (Open Graph)", "PNG ou JPG; 1200x630"),
    Slot("mascot", "mascot.png", 256, 256, "Mascote do bot de dicas (exibido com 64 px)", "Fundo transparente"),
    Slot("institution_logo", "institution-logo.png", 400, 112, "Rodapé: logo da instituição parceira (só aparece se Brand.institution_name estiver preenchido)", "Exibido com 28 px de altura"),
)

BY_KEY = {s.key: s for s in SLOTS}
PLACEHOLDER_MARK = b"simetal-placeholder"


def png_size(path: Path) -> tuple[int, int] | None:
    """Largura x altura lidas do cabeçalho IHDR do PNG (sem Pillow)."""
    try:
        with path.open("rb") as fh:
            head = fh.read(24)
        if head[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")
    except OSError:
        return None


def is_placeholder(path: Path) -> bool:
    try:
        return PLACEHOLDER_MARK in path.read_bytes()
    except OSError:
        return False


def status() -> list[dict]:
    """Estado de cada slot para o painel administrativo."""
    out = []
    for s in SLOTS:
        exists = s.path.is_file()
        size = png_size(s.path) if exists else None
        out.append(
            {
                "slot": s,
                "existe": exists,
                "placeholder": exists and is_placeholder(s.path),
                "dimensoes": size,
                "bytes": s.path.stat().st_size if exists else 0,
                "valido": bool(size),
            }
        )
    return out
