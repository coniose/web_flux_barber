"""Seletor de período (De / Até) com atalhos rápidos.

Não usa `tkcalendar` (evita dependência externa pesada). Entrada em texto
ISO ou DD/MM/AAAA, com botões para "Hoje", "Mês atual", "Últimos 30 dias" etc.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Callable, Optional, Tuple

import customtkinter as ctk

from app.ui import theme


class DateRangeSelector(ctk.CTkFrame):
    """Par de inputs de data com atalhos."""

    def __init__(
        self,
        master,
        *,
        on_change: Optional[Callable[[date, date], None]] = None,
        inicial: str = "mes_atual",
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self._on_change = on_change

        # Inputs
        self.var_de = ctk.StringVar()
        self.var_ate = ctk.StringVar()

        ctk.CTkLabel(self, text="De:", text_color=theme.FG_SECONDARY, font=theme.FONT_BODY).grid(
            row=0, column=0, padx=(0, theme.PAD_XS)
        )
        self.entry_de = ctk.CTkEntry(
            self, textvariable=self.var_de, width=110,
            fg_color=theme.BG_SURFACE_ALT, border_color=theme.BORDER,
            text_color=theme.FG_PRIMARY, font=theme.FONT_BODY,
        )
        self.entry_de.grid(row=0, column=1, padx=(0, theme.PAD_SM))

        ctk.CTkLabel(self, text="até:", text_color=theme.FG_SECONDARY, font=theme.FONT_BODY).grid(
            row=0, column=2, padx=(0, theme.PAD_XS)
        )
        self.entry_ate = ctk.CTkEntry(
            self, textvariable=self.var_ate, width=110,
            fg_color=theme.BG_SURFACE_ALT, border_color=theme.BORDER,
            text_color=theme.FG_PRIMARY, font=theme.FONT_BODY,
        )
        self.entry_ate.grid(row=0, column=3, padx=(0, theme.PAD_MD))

        # Atalhos
        atalhos = [
            ("Hoje", "hoje"),
            ("7 dias", "7dias"),
            ("Mês", "mes_atual"),
            ("30 dias", "30dias"),
            ("Ano", "ano_atual"),
        ]
        for i, (rot, chave) in enumerate(atalhos):
            ctk.CTkButton(
                self,
                text=rot,
                width=60,
                height=28,
                corner_radius=theme.RADIUS_SM,
                fg_color=theme.BG_SURFACE,
                hover_color=theme.BG_HOVER,
                text_color=theme.FG_SECONDARY,
                font=theme.FONT_SMALL,
                command=lambda c=chave: self.aplicar_atalho(c),
            ).grid(row=0, column=4 + i, padx=2)

        # Disparar change ao sair do input
        self.entry_de.bind("<FocusOut>", lambda e: self._emit())
        self.entry_ate.bind("<FocusOut>", lambda e: self._emit())
        self.entry_de.bind("<Return>", lambda e: self._emit())
        self.entry_ate.bind("<Return>", lambda e: self._emit())

        # Estado inicial
        self.aplicar_atalho(inicial, emitir=False)

    # ------------------------------------------------------------------

    def aplicar_atalho(self, chave: str, emitir: bool = True) -> None:
        hoje = date.today()
        if chave == "hoje":
            de, ate = hoje, hoje
        elif chave == "7dias":
            de, ate = hoje - timedelta(days=6), hoje
        elif chave == "30dias":
            de, ate = hoje - timedelta(days=29), hoje
        elif chave == "mes_atual":
            de = hoje.replace(day=1)
            ate = hoje
        elif chave == "ano_atual":
            de = hoje.replace(month=1, day=1)
            ate = hoje
        else:
            return
        self.set_range(de, ate, emitir=emitir)

    def set_range(self, de: date, ate: date, *, emitir: bool = True) -> None:
        self.var_de.set(de.strftime("%d/%m/%Y"))
        self.var_ate.set(ate.strftime("%d/%m/%Y"))
        if emitir:
            self._emit()

    def get_range(self) -> Tuple[date, date]:
        """Retorna (de, ate). Em caso de parse inválido, levanta ValueError."""
        de = _parse_br(self.var_de.get())
        ate = _parse_br(self.var_ate.get())
        if de > ate:
            raise ValueError("Data inicial posterior à final.")
        return de, ate

    def _emit(self) -> None:
        if self._on_change is None:
            return
        try:
            de, ate = self.get_range()
        except Exception:
            return
        try:
            self._on_change(de, ate)
        except Exception as e:
            print(f"[DateRangeSelector] on_change falhou: {e}")


def _parse_br(s: str) -> date:
    s = s.strip()
    if not s:
        raise ValueError("Data vazia.")
    # Aceita DD/MM/AAAA ou AAAA-MM-DD
    if "/" in s:
        d, m, a = s.split("/")
        return date(int(a), int(m), int(d))
    return date.fromisoformat(s)
