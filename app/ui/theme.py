"""Tema visual centralizado do Fluxo Barber.

Paleta escura inspirada no branding da Brodz:
- Fundo escuro (não preto puro) para reduzir fadiga ocular em uso prolongado.
- Dourado/bronze como cor de acento (associado à masculinidade e premium).
- Verde/vermelho para sinalização positiva/negativa nos dashboards.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Cores
# ---------------------------------------------------------------------------

# Fundos
BG_APP = "#0F1216"          # fundo da janela
BG_SIDEBAR = "#161A20"      # sidebar um tom acima
BG_SURFACE = "#1C2128"      # cards, frames internos
BG_SURFACE_ALT = "#232933"  # elementos clicáveis (hover base)
BG_HOVER = "#2D343F"        # hover de botões sutis

# Texto
FG_PRIMARY = "#EAEEF5"      # texto principal
FG_SECONDARY = "#9AA4B2"    # texto secundário / labels
FG_MUTED = "#606875"        # dicas, placeholders

# Acentos
ACCENT = "#C8A15A"          # dourado Brodz (botões principais)
ACCENT_HOVER = "#D8B46C"
ACCENT_FG = "#0F1216"       # texto sobre o acento

# Semântica
OK = "#2FBF71"              # receita / sucesso
OK_DARK = "#239B58"
WARN = "#E8B93B"             # atenção
ERR = "#E74C3C"              # despesa / erro
ERR_DARK = "#B7382A"
INFO = "#5DADE2"             # informação

# Bordas e divisórias
BORDER = "#2A313C"

# ---------------------------------------------------------------------------
# Tipografia
# ---------------------------------------------------------------------------

FONT_FAMILY = "Segoe UI"        # padrão Windows
FONT_FAMILY_MONO = "Consolas"   # valores monetários em grids

FONT_H1 = (FONT_FAMILY, 22, "bold")
FONT_H2 = (FONT_FAMILY, 16, "bold")
FONT_H3 = (FONT_FAMILY, 13, "bold")
FONT_BODY = (FONT_FAMILY, 12)
FONT_BODY_BOLD = (FONT_FAMILY, 12, "bold")
FONT_SMALL = (FONT_FAMILY, 10)
FONT_MONEY = (FONT_FAMILY_MONO, 13, "bold")
FONT_MONEY_BIG = (FONT_FAMILY_MONO, 22, "bold")

# ---------------------------------------------------------------------------
# Geometria / espaçamento
# ---------------------------------------------------------------------------

PAD_XS = 4
PAD_SM = 8
PAD_MD = 12
PAD_LG = 20
PAD_XL = 32

RADIUS_SM = 6
RADIUS_MD = 10
RADIUS_LG = 14

SIDEBAR_WIDTH = 220
BTN_HEIGHT = 36
BTN_HEIGHT_LG = 44

# ---------------------------------------------------------------------------
# Aplicação do tema em CustomTkinter
# ---------------------------------------------------------------------------


def aplicar_tema_global() -> None:
    """Configura defaults globais do CustomTkinter. Chamar uma vez no boot."""
    import customtkinter as ctk

    ctk.set_appearance_mode("dark")
    # Usamos o tema dark-blue como base e sobrescrevemos cores pontuais nos widgets.
    ctk.set_default_color_theme("dark-blue")
