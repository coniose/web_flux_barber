"""Tela Despesas — listagem, filtro por período + categoria, edição, exclusão."""

from __future__ import annotations

from datetime import date
from tkinter import messagebox
from typing import Dict, List, Optional

import customtkinter as ctk

from app.repositories import categoria_repo
from app.services import despesa_service
from app.ui import theme
from app.ui.widgets.data_grid import DataGrid
from app.ui.widgets.date_range import DateRangeSelector
from app.ui.widgets.modal_despesa import ModalDespesa
from app.utils.formato import formatar_moeda


class DespesasScreen(ctk.CTkFrame):
    """Listagem de despesas com filtros."""

    TODOS = "— Todas as categorias —"

    def __init__(self, master, app_window) -> None:
        super().__init__(master, fg_color=theme.BG_APP, corner_radius=0)
        self.app = app_window
        self.conn = app_window.conn

        self._categorias = categoria_repo.listar_ativas(self.conn)
        self._mapa_nome_id = {c["nome"]: c["id"] for c in self._categorias}

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
            header, text="Despesas",
            font=theme.FONT_H1, text_color=theme.FG_PRIMARY,
        ).pack(side="left")

        ctk.CTkButton(
            header, text="+ Nova despesa",
            fg_color=theme.ERR, hover_color=theme.ERR_DARK,
            text_color="#FFFFFF", font=theme.FONT_BODY_BOLD,
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
        inner.pack(padx=theme.PAD_MD, pady=theme.PAD_SM, fill="x")

        self.date_range = DateRangeSelector(
            inner, on_change=lambda d, a: self._recarregar(), inicial="mes_atual",
        )
        self.date_range.pack(side="left")

        ctk.CTkLabel(
            inner, text="Categoria:", text_color=theme.FG_SECONDARY,
            font=theme.FONT_BODY,
        ).pack(side="left", padx=(theme.PAD_LG, theme.PAD_XS))

        nomes = [self.TODOS] + [c["nome"] for c in self._categorias]
        self.combo_categoria = ctk.CTkComboBox(
            inner, values=nomes, width=220,
            fg_color=theme.BG_SURFACE_ALT, border_color=theme.BORDER,
            button_color=theme.BG_HOVER, text_color=theme.FG_PRIMARY,
            dropdown_fg_color=theme.BG_SURFACE,
            command=lambda _: self._recarregar(),
        )
        self.combo_categoria.set(self.TODOS)
        self.combo_categoria.pack(side="left")

    def _construir_grid(self) -> None:
        self.data_grid = DataGrid(
            self,
            colunas=[
                ("data", "Data", 90, "center"),
                ("categoria_nome", "Categoria", 180, "w"),
                ("descricao", "Descrição", 260, "w"),
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
            self.resumo, text="Total: R$ 0,00  ·  0 despesas",
            font=theme.FONT_BODY_BOLD, text_color=theme.ERR,
        )
        self.lbl_total.pack(padx=theme.PAD_MD, pady=theme.PAD_SM, anchor="w")

    # ------------------------------------------------------------------

    def _categoria_filtrada(self) -> Optional[int]:
        valor = self.combo_categoria.get()
        if valor == self.TODOS:
            return None
        return self._mapa_nome_id.get(valor)

    def _recarregar(self) -> None:
        try:
            de, ate = self.date_range.get_range()
        except Exception:
            return
        cat_id = self._categoria_filtrada()
        rows = despesa_service.listar_periodo(self.conn, de, ate, categoria_id=cat_id)
        registros: List[Dict] = []
        for r in rows:
            d = dict(r)
            d["valor_fmt"] = formatar_moeda(d["valor"])
            try:
                d["data"] = date.fromisoformat(d["data"]).strftime("%d/%m/%Y")
            except Exception:
                pass
            registros.append(d)
        self.data_grid.carregar(registros)

        # Total respeita apenas o período (não filtra por categoria — é intencional:
        # mostramos o total do período para contexto). Se quiser total filtrado,
        # aqui somamos a partir de ``registros``:
        total = sum(d["valor"] for d in registros)
        self.lbl_total.configure(
            text=f"Total: {formatar_moeda(total)}  ·  {len(registros)} despesas"
        )

    def _novo(self) -> None:
        ModalDespesa(
            self.winfo_toplevel(), self.conn,
            registro=None, on_ok=self._recarregar,
        )

    def _editar(self, registro: Dict) -> None:
        reg = dict(registro)
        try:
            d, m, a = reg["data"].split("/")
            reg["data"] = f"{a}-{m.zfill(2)}-{d.zfill(2)}"
        except Exception:
            pass
        ModalDespesa(
            self.winfo_toplevel(), self.conn,
            registro=reg, on_ok=self._recarregar,
        )

    def _confirmar_excluir(self, registro: Dict) -> None:
        resp = messagebox.askyesno(
            "Excluir despesa",
            f"Excluir despesa '{registro.get('descricao')}' "
            f"({formatar_moeda(registro['valor'])}) do dia {registro['data']}?",
            parent=self.winfo_toplevel(),
        )
        if resp:
            try:
                despesa_service.excluir_despesa(self.conn, registro["id"])
                self._recarregar()
            except Exception as e:
                messagebox.showerror("Erro", str(e), parent=self.winfo_toplevel())

    # ------------------------------------------------------------------

    def ao_mostrar(self) -> None:
        self._recarregar()
