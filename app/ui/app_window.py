"""Janela principal do Fluxo Barber.

Estrutura:
- Sidebar fixa à esquerda com navegação.
- Área de conteúdo à direita que troca de tela ("página") conforme o clique.
- Cada tela é uma classe `CTkFrame` registrada em ``self.telas``.
- Usamos um único `grid` para alternar telas (sem destruir/recriar widgets).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Callable, Dict, Optional

import customtkinter as ctk

from app.repositories.db import default_db_path, ensure_db
from app.services import configuracao_service
from app.ui import theme
from app.utils import backup


class AppWindow(ctk.CTk):
    """Janela raiz do aplicativo."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        super().__init__()

        # --- Conexão ---
        self.db_path = db_path or default_db_path()
        self._conn = ensure_db(self.db_path, seed=True)

        # Backup automático na abertura (silencioso se dentro do intervalo).
        try:
            backup.backup_auto_se_necessario(self.db_path)
        except Exception:
            # Backup não deve nunca bloquear a abertura do app.
            pass

        # --- Configuração da janela ---
        self.title(self._titulo())
        self.geometry("1280x800")
        self.minsize(1100, 700)
        self.configure(fg_color=theme.BG_APP)

        # Grid raiz: col 0 = sidebar, col 1 = conteúdo
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Sidebar ---
        self.sidebar = _Sidebar(
            self,
            nome_empresa=configuracao_service.nome_empresa(self._conn),
            on_navegar=self.mostrar_tela,
        )
        self.sidebar.grid(row=0, column=0, sticky="nswe")

        # --- Container de conteúdo ---
        self.container = ctk.CTkFrame(self, fg_color=theme.BG_APP, corner_radius=0)
        self.container.grid(row=0, column=1, sticky="nswe")
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        # --- Registro de telas ---
        # Construídas sob demanda (lazy) para reduzir tempo de boot.
        self.telas: Dict[str, ctk.CTkFrame] = {}
        self._tela_atual: Optional[str] = None

        # --- Fechamento limpo ---
        self.protocol("WM_DELETE_WINDOW", self._ao_fechar)

        # Tela inicial
        self.mostrar_tela("lancar")

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    @property
    def conn(self) -> sqlite3.Connection:
        return self._conn

    def mostrar_tela(self, chave: str) -> None:
        """Exibe (ou constrói sob demanda) a tela identificada por ``chave``."""
        if chave not in self.telas:
            tela = self._construir_tela(chave)
            if tela is None:
                return
            self.telas[chave] = tela
            tela.grid(row=0, column=0, sticky="nswe")

        # Oculta a anterior, mostra a nova.
        if self._tela_atual and self._tela_atual in self.telas:
            self.telas[self._tela_atual].grid_remove()
        self.telas[chave].grid()
        self._tela_atual = chave
        self.sidebar.destacar(chave)

        # Hook opcional de refresh quando a tela fica visível.
        tela = self.telas[chave]
        if hasattr(tela, "ao_mostrar"):
            try:
                tela.ao_mostrar()
            except Exception as e:
                print(f"[UI] erro em ao_mostrar({chave}): {e}")

    def atualizar_titulo(self) -> None:
        """Rechama após mudar nome_empresa nas configurações."""
        self.title(self._titulo())
        self.sidebar.set_nome_empresa(configuracao_service.nome_empresa(self._conn))

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _titulo(self) -> str:
        nome = configuracao_service.nome_empresa(self._conn)
        return f"Fluxo Barber — {nome}"

    def _construir_tela(self, chave: str) -> Optional[ctk.CTkFrame]:
        # Imports locais para evitar import circular e adiar custo.
        if chave == "lancar":
            from app.ui.screens.lancar_screen import LancarScreen
            return LancarScreen(self.container, self)
        if chave == "receitas":
            from app.ui.screens.receitas_screen import ReceitasScreen
            return ReceitasScreen(self.container, self)
        if chave == "despesas":
            from app.ui.screens.despesas_screen import DespesasScreen
            return DespesasScreen(self.container, self)
        if chave == "dashboard":
            from app.ui.screens.dashboard_screen import DashboardScreen
            return DashboardScreen(self.container, self)
        if chave == "relatorios":
            from app.ui.screens.relatorios_screen import RelatoriosScreen
            return RelatoriosScreen(self.container, self)
        if chave == "config":
            from app.ui.screens.config_screen import ConfigScreen
            return ConfigScreen(self.container, self)
        return None

    def _ao_fechar(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass
        self.destroy()


class _Sidebar(ctk.CTkFrame):
    """Barra lateral com logo e botões de navegação."""

    ITENS = [
        ("lancar", "Lançar", "➕"),
        ("receitas", "Receitas", "💈"),
        ("despesas", "Despesas", "💸"),
        ("dashboard", "Dashboard", "📊"),
        ("relatorios", "Relatórios", "📋"),
        ("config", "Configurações", "⚙"),
    ]

    def __init__(
        self,
        master,
        *,
        nome_empresa: str,
        on_navegar: Callable[[str], None],
    ) -> None:
        super().__init__(
            master,
            width=theme.SIDEBAR_WIDTH,
            fg_color=theme.BG_SIDEBAR,
            corner_radius=0,
        )
        self.grid_propagate(False)
        self.configure(width=theme.SIDEBAR_WIDTH)
        self._on_navegar = on_navegar
        self._botoes: Dict[str, ctk.CTkButton] = {}

        # --- Logo / nome ---
        self.lbl_logo = ctk.CTkLabel(
            self,
            text="FLUXO",
            font=(theme.FONT_FAMILY, 20, "bold"),
            text_color=theme.ACCENT,
        )
        self.lbl_logo.pack(pady=(theme.PAD_LG, 0), padx=theme.PAD_MD)

        self.lbl_sub = ctk.CTkLabel(
            self,
            text="barber",
            font=(theme.FONT_FAMILY, 12),
            text_color=theme.FG_SECONDARY,
        )
        self.lbl_sub.pack(pady=(0, theme.PAD_MD), padx=theme.PAD_MD)

        self.lbl_empresa = ctk.CTkLabel(
            self,
            text=nome_empresa,
            font=theme.FONT_BODY_BOLD,
            text_color=theme.FG_PRIMARY,
        )
        self.lbl_empresa.pack(pady=(0, theme.PAD_LG), padx=theme.PAD_MD)

        # Divisor
        ctk.CTkFrame(self, height=1, fg_color=theme.BORDER).pack(
            fill="x", padx=theme.PAD_MD, pady=(0, theme.PAD_SM)
        )

        # --- Botões ---
        for chave, titulo, icone in self.ITENS:
            btn = ctk.CTkButton(
                self,
                text=f"  {icone}   {titulo}",
                anchor="w",
                height=theme.BTN_HEIGHT,
                corner_radius=theme.RADIUS_SM,
                fg_color="transparent",
                hover_color=theme.BG_HOVER,
                text_color=theme.FG_SECONDARY,
                font=theme.FONT_BODY,
                command=lambda k=chave: self._on_navegar(k),
            )
            btn.pack(fill="x", padx=theme.PAD_MD, pady=2)
            self._botoes[chave] = btn

        # Espaço flexível empurrando rodapé para baixo
        ctk.CTkLabel(self, text="").pack(expand=True, fill="both")

        # Rodapé: versão
        self.lbl_versao = ctk.CTkLabel(
            self,
            text="v0.1.0 · offline",
            font=theme.FONT_SMALL,
            text_color=theme.FG_MUTED,
        )
        self.lbl_versao.pack(side="bottom", pady=theme.PAD_MD)

    def destacar(self, chave_ativa: str) -> None:
        for k, btn in self._botoes.items():
            if k == chave_ativa:
                btn.configure(
                    fg_color=theme.ACCENT,
                    text_color=theme.ACCENT_FG,
                    hover_color=theme.ACCENT_HOVER,
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=theme.FG_SECONDARY,
                    hover_color=theme.BG_HOVER,
                )

    def set_nome_empresa(self, nome: str) -> None:
        self.lbl_empresa.configure(text=nome)
