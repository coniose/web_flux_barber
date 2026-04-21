"""Dashboard — KPIs e gráficos do fechamento.

Layout:
  ┌──────────────────────────────────────────────────────────────┐
  │  Dashboard                     [De: … Até: …] [Hoje][Mês]…   │
  ├──────────────────────────────────────────────────────────────┤
  │  ╔═KPI═╗  ╔═KPI═╗  ╔═KPI═╗  ╔═KPI═╗  ╔═KPI═╗  ╔═KPI═╗         │
  │  Receita  Despesa   Saldo   Atend.   Ticket  Meta             │
  ├──────────────────────────────────────────────────────────────┤
  │  ┌ Evolução (linhas) ────────┐  ┌ Top serviços (barras) ──┐  │
  │  │                           │  │                         │  │
  │  └───────────────────────────┘  └─────────────────────────┘  │
  │  ┌ Forma de pagamento (pizza)┐  ┌ Progresso da meta ──────┐  │
  │  │                           │  │                         │  │
  │  └───────────────────────────┘  └─────────────────────────┘  │
  └──────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from datetime import date, timedelta

import customtkinter as ctk

from app.services import configuracao_service, despesa_service, receita_service
from app.ui import theme
from app.ui.widgets.chart_canvas import ChartCanvas
from app.ui.widgets.date_range import DateRangeSelector
from app.utils.formato import formatar_moeda


class DashboardScreen(ctk.CTkFrame):
    def __init__(self, master, app_window) -> None:
        super().__init__(master, fg_color=theme.BG_APP, corner_radius=0)
        self.app = app_window
        self.conn = app_window.conn

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._construir_cabecalho()
        self._construir_kpis()
        self._construir_graficos()

    # ------------------------------------------------------------------

    def _construir_cabecalho(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="we",
                    padx=theme.PAD_LG, pady=(theme.PAD_LG, theme.PAD_SM))
        ctk.CTkLabel(
            header, text="Dashboard",
            font=theme.FONT_H1, text_color=theme.FG_PRIMARY,
        ).pack(side="left")
        self.date_range = DateRangeSelector(
            header, on_change=lambda d, a: self._refresh(), inicial="mes_atual",
        )
        self.date_range.pack(side="right")

    # ------------------------------------------------------------------

    def _construir_kpis(self) -> None:
        kpis = ctk.CTkFrame(self, fg_color="transparent")
        kpis.grid(row=1, column=0, sticky="we",
                  padx=theme.PAD_LG, pady=(0, theme.PAD_SM))
        for c in range(6):
            kpis.grid_columnconfigure(c, weight=1)

        self._kpi_receita = _KpiCard(kpis, "Receita", theme.OK)
        self._kpi_receita.grid(row=0, column=0, sticky="nswe", padx=theme.PAD_XS)

        self._kpi_despesa = _KpiCard(kpis, "Despesas", theme.ERR)
        self._kpi_despesa.grid(row=0, column=1, sticky="nswe", padx=theme.PAD_XS)

        self._kpi_saldo = _KpiCard(kpis, "Saldo", theme.ACCENT)
        self._kpi_saldo.grid(row=0, column=2, sticky="nswe", padx=theme.PAD_XS)

        self._kpi_atend = _KpiCard(kpis, "Atendimentos", theme.INFO, moeda=False)
        self._kpi_atend.grid(row=0, column=3, sticky="nswe", padx=theme.PAD_XS)

        self._kpi_ticket = _KpiCard(kpis, "Ticket médio", theme.FG_PRIMARY)
        self._kpi_ticket.grid(row=0, column=4, sticky="nswe", padx=theme.PAD_XS)

        self._kpi_meta = _KpiCard(kpis, "Meta (mês atual)", theme.WARN)
        self._kpi_meta.grid(row=0, column=5, sticky="nswe", padx=theme.PAD_XS)

    # ------------------------------------------------------------------

    def _construir_graficos(self) -> None:
        grade = ctk.CTkFrame(self, fg_color="transparent")
        grade.grid(row=2, column=0, sticky="nswe",
                   padx=theme.PAD_LG, pady=(0, theme.PAD_LG))
        grade.grid_columnconfigure(0, weight=1)
        grade.grid_columnconfigure(1, weight=1)
        grade.grid_rowconfigure(0, weight=1)
        grade.grid_rowconfigure(1, weight=1)

        self.grafico_evolucao = ChartCanvas(
            grade, titulo="Evolução diária", altura_px=240, largura_px=480,
        )
        self.grafico_evolucao.grid(row=0, column=0, sticky="nswe",
                                   padx=theme.PAD_XS, pady=theme.PAD_XS)

        self.grafico_ranking = ChartCanvas(
            grade, titulo="Top serviços (faturamento)", altura_px=240, largura_px=480,
        )
        self.grafico_ranking.grid(row=0, column=1, sticky="nswe",
                                  padx=theme.PAD_XS, pady=theme.PAD_XS)

        self.grafico_mix = ChartCanvas(
            grade, titulo="Forma de pagamento", altura_px=240, largura_px=480,
        )
        self.grafico_mix.grid(row=1, column=0, sticky="nswe",
                              padx=theme.PAD_XS, pady=theme.PAD_XS)

        self.grafico_meta = ChartCanvas(
            grade, titulo="Progresso da meta (mês atual)",
            altura_px=240, largura_px=480,
        )
        self.grafico_meta.grid(row=1, column=1, sticky="nswe",
                               padx=theme.PAD_XS, pady=theme.PAD_XS)

    # ------------------------------------------------------------------
    # Refresh
    # ------------------------------------------------------------------

    def ao_mostrar(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        try:
            de, ate = self.date_range.get_range()
        except Exception:
            return

        # ---- KPIs ----
        rec = receita_service.totais_periodo(self.conn, de, ate)
        desp = despesa_service.totais_periodo(self.conn, de, ate)
        saldo = rec["total_centavos"] - desp["total_centavos"]
        ticket = (
            rec["total_centavos"] // rec["qtd_atendimentos"]
            if rec["qtd_atendimentos"] > 0 else 0
        )

        self._kpi_receita.set_valor(rec["total_centavos"])
        self._kpi_despesa.set_valor(desp["total_centavos"])
        self._kpi_saldo.set_valor(
            saldo, color_override=theme.OK if saldo >= 0 else theme.ERR,
        )
        self._kpi_atend.set_numero(rec["qtd_atendimentos"])
        self._kpi_ticket.set_valor(ticket)

        # Meta sempre reflete o mês corrente (não o período selecionado).
        hoje = date.today()
        primeiro = hoje.replace(day=1)
        meta = configuracao_service.meta_mensal_centavos(self.conn)
        rec_mes = receita_service.totais_periodo(self.conn, primeiro, hoje)["total_centavos"]
        if meta > 0:
            pct = (rec_mes / meta) * 100
            self._kpi_meta.set_texto(
                f"{pct:.0f}% de\n{formatar_moeda(meta)}"
            )
        else:
            self._kpi_meta.set_texto("não definida")

        # ---- Gráfico 1: evolução diária (linhas) ----
        dias_no_periodo = _gerar_dias(de, ate)
        serie_r = {
            r["data"]: r["total"]
            for r in receita_service.serie_diaria_receita(self.conn, de, ate)
        }
        serie_d = {
            r["data"]: r["total"]
            for r in despesa_service.serie_diaria_despesa(self.conn, de, ate)
        }
        receitas = [serie_r.get(d, 0) for d in dias_no_periodo]
        despesas = [serie_d.get(d, 0) for d in dias_no_periodo]
        self.grafico_evolucao.plot_linhas_receita_despesa(
            dias_no_periodo, receitas, despesas,
        )

        # ---- Gráfico 2: ranking top 8 serviços ----
        ranking = receita_service.ranking_servicos(self.conn, de, ate, limite=8)
        self.grafico_ranking.plot_barras_horizontais(
            [r["servico_nome"] for r in ranking],
            [r["total"] for r in ranking],
            cor=theme.ACCENT,
        )

        # ---- Gráfico 3: mix por forma de pagamento (pizza) ----
        mix = receita_service.mix_forma_pagamento(self.conn, de, ate)
        self.grafico_mix.plot_pizza(
            [m["forma"] for m in mix],
            [m["total"] for m in mix],
        )

        # ---- Gráfico 4: progresso da meta ----
        self.grafico_meta.plot_progresso(rec_mes, meta)


class _KpiCard(ctk.CTkFrame):
    def __init__(self, master, titulo: str, cor: str, *, moeda: bool = True) -> None:
        super().__init__(master, fg_color=theme.BG_SURFACE,
                         corner_radius=theme.RADIUS_MD)
        self._moeda = moeda
        ctk.CTkLabel(
            self, text=titulo.upper(),
            font=theme.FONT_SMALL, text_color=theme.FG_MUTED,
        ).pack(anchor="w", padx=theme.PAD_MD, pady=(theme.PAD_MD, 0))
        self.lbl_valor = ctk.CTkLabel(
            self, text="—",
            font=theme.FONT_MONEY_BIG, text_color=cor,
            anchor="w", justify="left",
        )
        self.lbl_valor.pack(anchor="w", padx=theme.PAD_MD, pady=(0, theme.PAD_MD))

    def set_valor(self, centavos: int, *, color_override: str | None = None) -> None:
        self.lbl_valor.configure(text=formatar_moeda(centavos))
        if color_override:
            self.lbl_valor.configure(text_color=color_override)

    def set_numero(self, n: int) -> None:
        self.lbl_valor.configure(text=str(n))

    def set_texto(self, txt: str) -> None:
        self.lbl_valor.configure(text=txt)


def _gerar_dias(de: date, ate: date) -> list[str]:
    """Lista de datas ISO entre ``de`` e ``ate`` inclusive."""
    dias: list[str] = []
    cur = de
    while cur <= ate:
        dias.append(cur.isoformat())
        cur += timedelta(days=1)
    return dias
