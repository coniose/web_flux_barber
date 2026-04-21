"""Botão grande de serviço — usado em grid para lançamento rápido.

Mostra: nome do serviço + preço sugerido em reais.
Clique dispara callback com o id do serviço e o preço sugerido.
"""

from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from app.ui import theme
from app.utils.formato import centavos_para_reais


class ServiceButton(ctk.CTkButton):
    """Botão retangular para um serviço do catálogo."""

    def __init__(
        self,
        master,
        *,
        servico_id: int,
        nome: str,
        preco_centavos: int,
        on_click: Callable[[int, int], None],
        width: int = 170,
        height: int = 72,
        **kwargs,
    ) -> None:
        self.servico_id = servico_id
        self.preco_centavos = preco_centavos
        texto = f"{nome}\nR$ {centavos_para_reais(preco_centavos)}"
        super().__init__(
            master,
            text=texto,
            width=width,
            height=height,
            corner_radius=theme.RADIUS_MD,
            fg_color=theme.BG_SURFACE,
            hover_color=theme.BG_HOVER,
            border_color=theme.BORDER,
            border_width=1,
            text_color=theme.FG_PRIMARY,
            font=theme.FONT_BODY_BOLD,
            command=lambda: on_click(self.servico_id, self.preco_centavos),
            **kwargs,
        )


class FrequentExpenseButton(ctk.CTkButton):
    """Botão de item de despesa frequente (1 clique registra)."""

    def __init__(
        self,
        master,
        *,
        item_id: int,
        descricao: str,
        valor_sugerido_centavos: int,
        on_click: Callable[[int, int], None],
        width: int = 170,
        height: int = 72,
        **kwargs,
    ) -> None:
        self.item_id = item_id
        self.valor_sugerido = valor_sugerido_centavos
        texto = f"{descricao}\nR$ {centavos_para_reais(valor_sugerido_centavos)}"
        super().__init__(
            master,
            text=texto,
            width=width,
            height=height,
            corner_radius=theme.RADIUS_MD,
            fg_color=theme.BG_SURFACE,
            hover_color=theme.BG_HOVER,
            border_color=theme.ERR,
            border_width=1,
            text_color=theme.FG_PRIMARY,
            font=theme.FONT_BODY_BOLD,
            command=lambda: on_click(self.item_id, self.valor_sugerido),
            **kwargs,
        )
