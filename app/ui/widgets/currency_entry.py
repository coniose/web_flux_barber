"""Entry de moeda em pt-BR com máscara viva.

Estratégia: sempre armazenamos o valor internamente em CENTAVOS (int).
O que o usuário vê é derivado disso. A cada tecla numérica, o dígito vira o
"último centavo" (estilo maquininha de cartão). Isso elimina ambiguidade
com vírgulas/pontos e previne erros.

Exemplo de digitação:
    (vazio)    → "R$ 0,00"
    1          → "R$ 0,01"
    12         → "R$ 0,12"
    1234       → "R$ 12,34"
    350000     → "R$ 3.500,00"
"""

from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from app.ui import theme
from app.utils.formato import centavos_para_reais


class CurrencyEntry(ctk.CTkEntry):
    """Entry que só aceita dígitos e exibe valor formatado em R$."""

    def __init__(
        self,
        master,
        *,
        valor_inicial_centavos: int = 0,
        on_change: Optional[Callable[[int], None]] = None,
        width: int = 180,
        height: int = 36,
        placeholder: str = "R$ 0,00",
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            width=width,
            height=height,
            font=theme.FONT_MONEY,
            corner_radius=theme.RADIUS_SM,
            fg_color=theme.BG_SURFACE_ALT,
            border_color=theme.BORDER,
            text_color=theme.FG_PRIMARY,
            placeholder_text=placeholder,
            placeholder_text_color=theme.FG_MUTED,
            justify="right",
            **kwargs,
        )
        self._centavos = max(0, int(valor_inicial_centavos))
        self._on_change = on_change
        self._refresh()

        # Só capturamos teclas — bloqueamos paste e edição por mouse.
        self.bind("<Key>", self._on_key, add="+")
        self.bind("<FocusIn>", lambda e: self._select_all(), add="+")
        self.bind("<Button-1>", lambda e: self.after(1, self._cursor_fim), add="+")
        # Impede que o cursor seja movido para o meio por drag/double-click.
        self.bind("<B1-Motion>", lambda e: "break", add="+")

    # ------------------------------------------------------------------

    @property
    def centavos(self) -> int:
        return self._centavos

    def set_centavos(self, valor: int) -> None:
        self._centavos = max(0, int(valor))
        self._refresh()
        if self._on_change:
            self._on_change(self._centavos)

    def limpar(self) -> None:
        self.set_centavos(0)

    def focus_set(self) -> None:  # type: ignore[override]
        super().focus_set()
        self._cursor_fim()

    # ------------------------------------------------------------------
    # Tratamento de teclas
    # ------------------------------------------------------------------

    def _on_key(self, event) -> Optional[str]:
        # Deixa passar Tab, setas laterais, Enter etc.
        if event.keysym in ("Tab", "ISO_Left_Tab", "Return", "KP_Enter",
                            "Left", "Right", "Up", "Down",
                            "Home", "End", "Escape"):
            return None

        if event.keysym in ("BackSpace", "Delete"):
            self._centavos //= 10
            self._refresh()
            self._notify()
            return "break"

        ch = event.char
        if ch and ch.isdigit():
            # Limite sanitário: 999.999,99 (R$ 999 mil)
            novo = self._centavos * 10 + int(ch)
            if novo > 99_999_999:  # ~R$ 999.999,99
                return "break"
            self._centavos = novo
            self._refresh()
            self._notify()
            return "break"

        # Qualquer outra tecla é ignorada.
        return "break"

    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        texto = f"R$ {centavos_para_reais(self._centavos)}"
        # Atualiza sem disparar o bind.
        self.configure(state="normal")
        super().delete(0, "end")
        super().insert(0, texto)
        self._cursor_fim()

    def _notify(self) -> None:
        if self._on_change:
            try:
                self._on_change(self._centavos)
            except Exception as e:
                print(f"[CurrencyEntry] on_change falhou: {e}")

    def _cursor_fim(self) -> None:
        self.icursor("end")

    def _select_all(self) -> None:
        try:
            self.select_range(0, "end")
            self.icursor("end")
        except Exception:
            pass
