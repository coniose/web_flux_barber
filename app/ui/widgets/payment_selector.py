"""Seletor de forma de pagamento — botões segmentados (PIX / Dinheiro / Maquininha).

Três botões visuais, apenas um fica ativo por vez.
"""

from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from app.domain.enums import FormaPagamento
from app.ui import theme


class PaymentSelector(ctk.CTkFrame):
    """Linha de 3 botões: PIX / DINHEIRO / MAQUININHA."""

    OPCOES = [
        (FormaPagamento.PIX, "PIX"),
        (FormaPagamento.DINHEIRO, "Dinheiro"),
        (FormaPagamento.MAQUININHA, "Maquininha"),
    ]

    def __init__(
        self,
        master,
        *,
        valor_inicial: FormaPagamento = FormaPagamento.PIX,
        on_change: Optional[Callable[[FormaPagamento], None]] = None,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self._valor = valor_inicial
        self._on_change = on_change
        self._botoes: dict = {}

        for i, (forma, rotulo) in enumerate(self.OPCOES):
            btn = ctk.CTkButton(
                self,
                text=rotulo,
                width=100,
                height=theme.BTN_HEIGHT,
                corner_radius=theme.RADIUS_SM,
                font=theme.FONT_BODY_BOLD,
                command=lambda f=forma: self.set(f),
            )
            btn.grid(row=0, column=i, padx=theme.PAD_XS)
            self._botoes[forma] = btn

        self._refresh()

    def set(self, valor: FormaPagamento) -> None:
        self._valor = valor
        self._refresh()
        if self._on_change:
            try:
                self._on_change(valor)
            except Exception as e:
                print(f"[PaymentSelector] on_change falhou: {e}")

    def get(self) -> FormaPagamento:
        return self._valor

    def _refresh(self) -> None:
        for forma, btn in self._botoes.items():
            if forma == self._valor:
                btn.configure(
                    fg_color=theme.ACCENT,
                    hover_color=theme.ACCENT_HOVER,
                    text_color=theme.ACCENT_FG,
                )
            else:
                btn.configure(
                    fg_color=theme.BG_SURFACE_ALT,
                    hover_color=theme.BG_HOVER,
                    text_color=theme.FG_SECONDARY,
                )
