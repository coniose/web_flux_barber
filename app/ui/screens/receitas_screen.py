"""Tela Receitas — listagem, filtro por período, edição, exclusão."""

from __future__ import annotations

from datetime import date
from tkinter import messagebox
from typing import Dict, List

import customtkinter as ctk

from app.services import receita_service
from app.ui import theme
from app.ui.widgets.data_grid import DataGrid
from app.ui.widgets.date_range import DateRangeSelector
from app.ui.widgets.modal_atendimento import ModalAtendimento
from app.utils.formato import formatar_moeda


class ReceitasScreen(ctk.CTkFrame):
    """Listagem de atendimentos (receitas) com filtro por período."""

    def __init__(self, master, app_window) -> None:
        super().__init__(master, fg_color=theme.BG_APP, corner_radius=0)
        self.app = app_window
        self.conn = app_window.conn

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._construir_cabecalho()
        self._construir_filtro()
        self._construir_grid()
        self._construir_resumo()

    # ------------------------------------------------------------------

    def _construir_cabecalho(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="we",
                    padx=theme.PAD_LG, pady=(theme.PAD_LG, theme.PAD_SM))

        ctk.CTkLabel(
            header, text="Receitas",
            font=theme.FONT_H1, text_color=theme.FG_PRIMARY,
        ).pack(side="left")

        ctk.CTkButton(
            header, text="+ Novo atendimento",
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
            text_color=theme.ACCENT_FG, font=theme.FONT_BODY_BOLD,
            height=theme.BTN_HEIGHT, corner_radius=theme.RADIUS_SM,
            command=self._novo,
        ).pack(side="right")

    def _construir_filtro(self) -> None:
        frame = ctk.CTkFrame(
            self, fg_color=theme.BG_SURFACE, corner_radius=theme.RADIUS_MD,
        )
        frame.grid(row=1, column=0, sticky="we",
                   padx=theme.PAD_LG, pady=(0, theme.PAD_SM))
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(padx=theme.PAD_MD, pady=theme.PAD_SM)

        self.date_range = DateRangeSelector(
            inner, on_change=self._on_periodo_change, inicial="mes_atual",
        )
        self.date_range.pack(side="left")

    def _construir_grid(self) -> None:
        self.data_grid = DataGrid(
            self,
            colunas=[
                ("data", "Data", 90, "center"),
                ("servico_nome", "Serviço", 220, "w"),
                ("cliente_nome", "Cliente", 150, "w"),
                ("plano_nome", "Plano", 130, "w"),
                ("valor_fmt", "Valor", 110, "e"),
                ("forma_pagamento", "Forma", 90, "center"),
            ],
            on_duplo_clique=self._editar,
            on_delete=self._confirmar_excluir,
        )
        self.data_grid.grid(row=2, column=0, sticky="nswe",
                       padx=theme.PAD_LG, pady=(0, theme.PAD_SM))

    def _construir_resumo(self) -> None:
        self.resumo = ctk.CTkFrame(
            self, fg_color=theme.BG_SURFACE, corner_radius=theme.RADIUS_MD,
        )
        self.resumo.grid(row=3, column=0, sticky="we",
                         padx=theme.PAD_LG, pady=(0, theme.PAD_LG))
        self.lbl_total = ctk.CTkLabel(
            self.resumo, text="Total: R$ 0,00  ·  0 atendimentos",
            font=theme.FONT_BODY_BOLD, text_color=theme.OK,
        )
        self.lbl_total.pack(padx=theme.PAD_MD, pady=theme.PAD_SM, anchor="w")

    # ------------------------------------------------------------------

    def _on_periodo_change(self, de: date, ate: date) -> None:
        self._recarregar()

    def _recarregar(self) -> None:
        try:
            de, ate = self.date_range.get_range()
        except Exception:
            return
        rows = receita_service.listar_periodo(self.conn, de, ate)
        registros: List[Dict] = []
        for r in rows:
            d = dict(r)
            d["valor_fmt"] = formatar_moeda(d["valor"])
            # Exibir data em BR
            try:
                d["data"] = date.fromisoformat(d["data"]).strftime("%d/%m/%Y")
            except Exception:
                pass
            registros.append(d)
        self.data_grid.carregar(registros)

        tot = receita_service.totais_periodo(self.conn, de, ate)
        self.lbl_total.configure(
            text=(
                f"Total: {formatar_moeda(tot['total_centavos'])}  ·  "
                f"{tot['qtd_atendimentos']} atendimentos"
            )
        )

    def _novo(self) -> None:
        ModalAtendimento(
            self.winfo_toplevel(), self.conn,
            registro=None, on_ok=self._recarregar,
        )

    def _editar(self, registro: Dict) -> None:
        # Reconstituir com data ISO esperada pelo modal.
        reg = dict(registro)
        try:
            d, m, a = reg["data"].split("/")
            reg["data"] = f"{a}-{m.zfill(2)}-{d.zfill(2)}"
        except Exception:
            pass
        ModalAtendimento(
            self.winfo_toplevel(), self.conn,
            registro=reg, on_ok=self._recarregar,
        )

    def _confirmar_excluir(self, registro: Dict) -> None:
        resp = messagebox.askyesno(
            "Excluir atendimento",
            f"Excluir atendimento de {registro.get('servico_nome')} "
            f"({formatar_moeda(registro['valor'])}) do dia {registro['data']}?",
            parent=self.winfo_toplevel(),
        )
        if resp:
            try:
                receita_service.excluir_atendimento(self.conn, registro["id"])
                self._recarregar()
            except Exception as e:
                messagebox.showerror("Erro", str(e), parent=self.winfo_toplevel())

    # ------------------------------------------------------------------

    def ao_mostrar(self) -> None:
        self._recarregar()
