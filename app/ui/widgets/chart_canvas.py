"""Widget que embute uma figura matplotlib dentro de um CTkFrame.

Usa a paleta do tema para manter consistência visual. Cada tipo de gráfico
(barra, linha, pizza) tem um método dedicado. Ao chamar um método de plot,
a figura é limpa e redesenhada — evita o antipattern de criar um canvas
novo a cada refresh (memory leak com ticks/callbacks do Tk).
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import customtkinter as ctk
import matplotlib

matplotlib.use("TkAgg")  # precisa vir antes de qualquer import de pyplot
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from app.ui import theme
from app.utils.formato import centavos_para_reais


# Paleta para séries múltiplas
_PALETA = [
    theme.ACCENT,      # dourado
    theme.OK,          # verde
    theme.INFO,        # azul
    theme.ERR,         # vermelho
    theme.WARN,        # amarelo
    "#A58DE8",         # roxo suave
    "#E87DC1",         # rosa
    "#5FD5B7",         # verde-água
]


def _aplicar_estilo(fig: Figure) -> None:
    fig.patch.set_facecolor(theme.BG_SURFACE)


def _aplicar_estilo_axes(ax) -> None:
    ax.set_facecolor(theme.BG_SURFACE)
    ax.tick_params(colors=theme.FG_SECONDARY, labelsize=8)
    for spine in ax.spines.values():
        spine.set_color(theme.BORDER)
    ax.xaxis.label.set_color(theme.FG_SECONDARY)
    ax.yaxis.label.set_color(theme.FG_SECONDARY)
    if ax.get_title():
        ax.title.set_color(theme.FG_PRIMARY)
    ax.grid(True, color=theme.BORDER, linestyle=":", linewidth=0.6, alpha=0.6)


def _fmt_moeda_curto(centavos: int) -> str:
    """R$ 1,2k / R$ 12,3k / R$ 1,2M — útil para eixos com pouco espaço."""
    reais = centavos / 100
    if abs(reais) >= 1_000_000:
        return f"R$ {reais / 1_000_000:.1f}M".replace(".", ",")
    if abs(reais) >= 1_000:
        return f"R$ {reais / 1_000:.1f}k".replace(".", ",")
    return f"R$ {reais:.0f}"


class ChartCanvas(ctk.CTkFrame):
    """Frame contendo uma figura matplotlib reutilizável."""

    def __init__(
        self,
        master,
        *,
        titulo: Optional[str] = None,
        altura_px: int = 220,
        largura_px: int = 400,
        dpi: int = 100,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color=theme.BG_SURFACE,
                         corner_radius=theme.RADIUS_MD, **kwargs)

        if titulo:
            ctk.CTkLabel(
                self, text=titulo,
                font=theme.FONT_H3, text_color=theme.FG_SECONDARY,
                anchor="w",
            ).pack(fill="x", padx=theme.PAD_MD, pady=(theme.PAD_MD, 0))

        self._fig = Figure(
            figsize=(largura_px / dpi, altura_px / dpi),
            dpi=dpi,
            tight_layout=True,
        )
        _aplicar_estilo(self._fig)
        # Atenção: CTkFrame já usa ``self._canvas`` internamente (tk.Canvas do
        # próprio CTk). Sobrescrever esse atributo com o FigureCanvasTkAgg
        # quebra o CTk ao redesenhar (ele chama ``winfo_exists()``). Por isso
        # guardamos o canvas do matplotlib em ``_fig_canvas``.
        self._fig_canvas = FigureCanvasTkAgg(self._fig, master=self)
        widget = self._fig_canvas.get_tk_widget()
        widget.configure(
            bg=theme.BG_SURFACE, highlightthickness=0, borderwidth=0,
        )
        widget.pack(fill="both", expand=True,
                    padx=theme.PAD_SM, pady=(theme.PAD_XS, theme.PAD_SM))

    # ------------------------------------------------------------------
    # API de plot (cada método limpa a figura antes de desenhar).
    # ------------------------------------------------------------------

    def limpar(self) -> None:
        self._fig.clear()
        self._fig_canvas.draw_idle()

    def plot_linhas_receita_despesa(
        self,
        datas: Sequence[str],
        receitas_centavos: Sequence[int],
        despesas_centavos: Sequence[int],
    ) -> None:
        """Duas linhas: receita e despesa por dia."""
        self._fig.clear()
        ax = self._fig.add_subplot(111)

        if not datas:
            self._desenhar_vazio(ax, "Sem dados no período")
            self._fig_canvas.draw_idle()
            return

        xs = list(range(len(datas)))
        ax.plot(xs, [c / 100 for c in receitas_centavos],
                color=theme.OK, linewidth=2, marker="o", markersize=4,
                label="Receita")
        ax.plot(xs, [c / 100 for c in despesas_centavos],
                color=theme.ERR, linewidth=2, marker="o", markersize=4,
                label="Despesa")
        ax.fill_between(xs, [c / 100 for c in receitas_centavos],
                        alpha=0.12, color=theme.OK)

        # Reduzir labels do eixo X para caber visualmente.
        passo = max(1, len(datas) // 8)
        ax.set_xticks(xs[::passo])
        ax.set_xticklabels(
            [_dia_abrev(datas[i]) for i in xs[::passo]],
            rotation=0,
        )
        ax.yaxis.set_major_formatter(
            plt.FuncFormatter(lambda v, _: _fmt_moeda_curto(int(v * 100)))
        )
        _aplicar_estilo_axes(ax)
        leg = ax.legend(
            loc="upper left", frameon=False, fontsize=8,
            labelcolor=theme.FG_SECONDARY,
        )
        for t in leg.get_texts():
            t.set_color(theme.FG_SECONDARY)
        self._fig_canvas.draw_idle()

    def plot_barras_horizontais(
        self,
        rotulos: Sequence[str],
        valores_centavos: Sequence[int],
        cor: str = theme.ACCENT,
    ) -> None:
        """Barras horizontais — ideal para ranking top N."""
        self._fig.clear()
        ax = self._fig.add_subplot(111)

        if not rotulos:
            self._desenhar_vazio(ax, "Sem dados no período")
            self._fig_canvas.draw_idle()
            return

        # Inverte pra o maior ficar em cima.
        rot = list(reversed(rotulos))
        val = [c / 100 for c in reversed(valores_centavos)]
        bars = ax.barh(rot, val, color=cor, edgecolor=theme.BG_SURFACE)

        # Rotular cada barra com o valor.
        for b, v in zip(bars, val):
            ax.text(
                b.get_width() * 1.01, b.get_y() + b.get_height() / 2,
                _fmt_moeda_curto(int(v * 100)),
                va="center", ha="left",
                color=theme.FG_SECONDARY, fontsize=8,
            )

        ax.xaxis.set_major_formatter(
            plt.FuncFormatter(lambda v, _: _fmt_moeda_curto(int(v * 100)))
        )
        ax.tick_params(axis="y", labelsize=9)
        _aplicar_estilo_axes(ax)
        # Remove grade vertical (fica poluída em barras horizontais).
        ax.grid(True, axis="x", color=theme.BORDER, linestyle=":", linewidth=0.6, alpha=0.6)
        ax.set_axisbelow(True)
        self._fig_canvas.draw_idle()

    def plot_pizza(
        self,
        rotulos: Sequence[str],
        valores_centavos: Sequence[int],
    ) -> None:
        """Pizza com proporções e legenda lateral."""
        self._fig.clear()
        ax = self._fig.add_subplot(111)

        if not rotulos or sum(valores_centavos) == 0:
            self._desenhar_vazio(ax, "Sem dados no período")
            self._fig_canvas.draw_idle()
            return

        cores = [_PALETA[i % len(_PALETA)] for i in range(len(rotulos))]
        wedges, _ = ax.pie(
            list(valores_centavos),
            colors=cores,
            startangle=90,
            wedgeprops={"edgecolor": theme.BG_SURFACE, "linewidth": 2},
        )

        total = sum(valores_centavos) or 1
        legenda = [
            f"{rot}  ·  {val/total*100:.0f}%  ·  {_fmt_moeda_curto(val)}"
            for rot, val in zip(rotulos, valores_centavos)
        ]
        leg = ax.legend(
            wedges, legenda,
            loc="center left", bbox_to_anchor=(1.02, 0.5),
            frameon=False, fontsize=8,
        )
        for t in leg.get_texts():
            t.set_color(theme.FG_SECONDARY)

        ax.set_facecolor(theme.BG_SURFACE)
        self._fig_canvas.draw_idle()

    def plot_progresso(
        self,
        atual_centavos: int,
        meta_centavos: int,
    ) -> None:
        """Barra horizontal de progresso (atual vs meta)."""
        self._fig.clear()
        ax = self._fig.add_subplot(111)

        if meta_centavos <= 0:
            self._desenhar_vazio(ax, "Meta não definida")
            self._fig_canvas.draw_idle()
            return

        pct = min(1.5, atual_centavos / meta_centavos)  # permite > 100%
        cor_barra = theme.OK if pct >= 1.0 else (theme.WARN if pct >= 0.7 else theme.ERR)

        ax.barh([0], [1.0], color=theme.BG_SURFACE_ALT, edgecolor=theme.BORDER)
        ax.barh([0], [min(pct, 1.0)], color=cor_barra)
        if pct > 1.0:
            # Excesso em outra cor, a direita da meta
            ax.barh([0], [pct - 1.0], left=[1.0], color=theme.ACCENT)

        ax.set_xlim(0, max(1.05, pct + 0.05))
        ax.set_yticks([])

        # Etiqueta central
        ax.text(
            pct / 2, 0,
            f"{pct * 100:.0f}% · {_fmt_moeda_curto(atual_centavos)} de "
            f"{_fmt_moeda_curto(meta_centavos)}",
            ha="center", va="center",
            color=theme.FG_PRIMARY, fontsize=10, fontweight="bold",
        )
        ax.xaxis.set_visible(False)
        for spine in ax.spines.values():
            spine.set_visible(False)
        self._fig_canvas.draw_idle()

    # ------------------------------------------------------------------

    def _desenhar_vazio(self, ax, msg: str) -> None:
        ax.text(
            0.5, 0.5, msg, ha="center", va="center",
            transform=ax.transAxes, color=theme.FG_MUTED, fontsize=10,
        )
        ax.set_xticks([]); ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.set_facecolor(theme.BG_SURFACE)


def _dia_abrev(data_iso: str) -> str:
    """'2026-04-17' -> '17/04'."""
    try:
        partes = data_iso.split("-")
        return f"{partes[2]}/{partes[1]}"
    except Exception:
        return data_iso
