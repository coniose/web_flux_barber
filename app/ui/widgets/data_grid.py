"""DataGrid simples baseado em ttk.Treeview estilizado.

Usado nas telas de Receitas e Despesas para listar registros com colunas
selecionáveis. Suporta duplo-clique para editar e atalho Delete para excluir.
"""

from __future__ import annotations

from tkinter import ttk
from typing import Any, Callable, Dict, List, Optional, Sequence

import customtkinter as ctk

from app.ui import theme


class DataGrid(ctk.CTkFrame):
    """Wrapper estilizado sobre ttk.Treeview."""

    def __init__(
        self,
        master,
        *,
        colunas: Sequence[tuple],        # [(id, titulo, largura, anchor)]
        on_duplo_clique: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_delete: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        super().__init__(master, fg_color=theme.BG_SURFACE, corner_radius=theme.RADIUS_MD)
        self._colunas = colunas
        self._on_duplo_clique = on_duplo_clique
        self._on_delete = on_delete
        # Guardamos os dicts originais indexados pelo iid do Treeview.
        self._itens: Dict[str, Dict[str, Any]] = {}

        self._configurar_estilo()

        cols_ids = [c[0] for c in colunas]
        self.tree = ttk.Treeview(
            self,
            columns=cols_ids,
            show="headings",
            style="FluxoBarber.Treeview",
            selectmode="browse",
        )
        for cid, titulo, largura, anchor in colunas:
            self.tree.heading(cid, text=titulo, anchor=anchor)
            self.tree.column(cid, width=largura, anchor=anchor, stretch=True)

        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(theme.PAD_SM, 0), pady=theme.PAD_SM)
        vsb.pack(side="right", fill="y", pady=theme.PAD_SM, padx=(0, theme.PAD_SM))

        self.tree.bind("<Double-1>", self._on_double)
        self.tree.bind("<Delete>", self._on_del)

    # ------------------------------------------------------------------

    def _configurar_estilo(self) -> None:
        style = ttk.Style()
        # O tema 'clam' respeita melhor customização do que 'vista' no Windows.
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            "FluxoBarber.Treeview",
            background=theme.BG_SURFACE,
            fieldbackground=theme.BG_SURFACE,
            foreground=theme.FG_PRIMARY,
            bordercolor=theme.BORDER,
            lightcolor=theme.BG_SURFACE,
            darkcolor=theme.BG_SURFACE,
            rowheight=28,
            font=theme.FONT_BODY,
        )
        style.configure(
            "FluxoBarber.Treeview.Heading",
            background=theme.BG_SURFACE_ALT,
            foreground=theme.FG_SECONDARY,
            font=theme.FONT_BODY_BOLD,
            bordercolor=theme.BORDER,
            relief="flat",
        )
        style.map(
            "FluxoBarber.Treeview",
            background=[("selected", theme.ACCENT)],
            foreground=[("selected", theme.ACCENT_FG)],
        )
        style.map("FluxoBarber.Treeview.Heading", background=[("active", theme.BG_HOVER)])

    # ------------------------------------------------------------------

    def carregar(self, registros: List[Dict[str, Any]], *, id_key: str = "id") -> None:
        """Substitui todo o conteúdo. ``id_key`` indica o campo que vira iid."""
        self.limpar()
        for reg in registros:
            iid = str(reg[id_key])
            valores = [self._valor_coluna(reg, cid) for cid, *_ in self._colunas]
            self.tree.insert("", "end", iid=iid, values=valores)
            self._itens[iid] = reg

    def _valor_coluna(self, reg: Dict[str, Any], chave: str) -> Any:
        v = reg.get(chave, "")
        return v if v is not None else ""

    def limpar(self) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        self._itens.clear()

    def selecionado(self) -> Optional[Dict[str, Any]]:
        sel = self.tree.selection()
        if not sel:
            return None
        return self._itens.get(sel[0])

    # ------------------------------------------------------------------

    def _on_double(self, _event) -> None:
        if self._on_duplo_clique is None:
            return
        reg = self.selecionado()
        if reg is not None:
            self._on_duplo_clique(reg)

    def _on_del(self, _event) -> None:
        if self._on_delete is None:
            return
        reg = self.selecionado()
        if reg is not None:
            self._on_delete(reg)
