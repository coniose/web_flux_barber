"""Configurações — nome da empresa, meta mensal, backup."""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from app.services import configuracao_service
from app.ui import theme
from app.ui.widgets.currency_entry import CurrencyEntry
from app.utils import backup


class ConfigScreen(ctk.CTkFrame):
    def __init__(self, master, app_window) -> None:
        super().__init__(master, fg_color=theme.BG_APP, corner_radius=0)
        self.app = app_window
        self.conn = app_window.conn

        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text="Configurações",
            font=theme.FONT_H1, text_color=theme.FG_PRIMARY,
        ).grid(row=0, column=0, sticky="w",
               padx=theme.PAD_LG, pady=(theme.PAD_LG, theme.PAD_MD))

        self._construir_card_empresa()
        self._construir_card_meta()
        self._construir_card_backup()

        self.lbl_status = ctk.CTkLabel(
            self, text="", font=theme.FONT_SMALL, text_color=theme.OK,
        )
        self.lbl_status.grid(row=10, column=0, sticky="w",
                             padx=theme.PAD_LG, pady=theme.PAD_SM)

    # ------------------------------------------------------------------

    def _card(self, titulo: str) -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            self, fg_color=theme.BG_SURFACE, corner_radius=theme.RADIUS_MD,
        )
        ctk.CTkLabel(
            card, text=titulo,
            font=theme.FONT_H3, text_color=theme.FG_SECONDARY,
        ).pack(anchor="w", padx=theme.PAD_MD, pady=(theme.PAD_MD, theme.PAD_SM))
        return card

    def _construir_card_empresa(self) -> None:
        card = self._card("Identidade")
        card.grid(row=1, column=0, sticky="we",
                  padx=theme.PAD_LG, pady=theme.PAD_XS)

        linha = ctk.CTkFrame(card, fg_color="transparent")
        linha.pack(fill="x", padx=theme.PAD_MD, pady=(0, theme.PAD_MD))
        ctk.CTkLabel(linha, text="Nome da empresa:",
                     text_color=theme.FG_SECONDARY, font=theme.FONT_BODY)\
            .pack(side="left", padx=(0, theme.PAD_SM))
        self.entry_nome = ctk.CTkEntry(
            linha, width=280,
            fg_color=theme.BG_SURFACE_ALT, border_color=theme.BORDER,
            text_color=theme.FG_PRIMARY, font=theme.FONT_BODY,
        )
        self.entry_nome.insert(0, configuracao_service.nome_empresa(self.conn))
        self.entry_nome.pack(side="left", padx=(0, theme.PAD_SM))
        ctk.CTkButton(
            linha, text="Salvar",
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
            text_color=theme.ACCENT_FG, font=theme.FONT_BODY_BOLD,
            width=90, command=self._salvar_nome,
        ).pack(side="left")

    def _construir_card_meta(self) -> None:
        card = self._card("Meta de receita mensal")
        card.grid(row=2, column=0, sticky="we",
                  padx=theme.PAD_LG, pady=theme.PAD_XS)

        linha = ctk.CTkFrame(card, fg_color="transparent")
        linha.pack(fill="x", padx=theme.PAD_MD, pady=(0, theme.PAD_MD))
        ctk.CTkLabel(linha, text="Meta:", text_color=theme.FG_SECONDARY,
                     font=theme.FONT_BODY)\
            .pack(side="left", padx=(0, theme.PAD_SM))
        self.entry_meta = CurrencyEntry(
            linha,
            valor_inicial_centavos=configuracao_service.meta_mensal_centavos(self.conn),
            width=180,
        )
        self.entry_meta.pack(side="left", padx=(0, theme.PAD_SM))
        ctk.CTkButton(
            linha, text="Salvar",
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
            text_color=theme.ACCENT_FG, font=theme.FONT_BODY_BOLD,
            width=90, command=self._salvar_meta,
        ).pack(side="left")

    def _construir_card_backup(self) -> None:
        card = self._card("Backup e restauração")
        card.grid(row=3, column=0, sticky="we",
                  padx=theme.PAD_LG, pady=theme.PAD_XS)

        info = ctk.CTkLabel(
            card,
            text=(
                f"Banco de dados: {self.app.db_path}\n"
                f"Backups automáticos (24h) em: "
                f"{backup.pasta_backups_padrao(self.app.db_path)}"
            ),
            font=theme.FONT_SMALL, text_color=theme.FG_MUTED, justify="left",
        )
        info.pack(anchor="w", padx=theme.PAD_MD, pady=(0, theme.PAD_SM))

        linha = ctk.CTkFrame(card, fg_color="transparent")
        linha.pack(fill="x", padx=theme.PAD_MD, pady=(0, theme.PAD_MD))
        ctk.CTkButton(
            linha, text="Fazer backup agora",
            fg_color=theme.BG_SURFACE_ALT, hover_color=theme.BG_HOVER,
            text_color=theme.FG_PRIMARY, font=theme.FONT_BODY,
            command=self._backup_agora,
        ).pack(side="left", padx=(0, theme.PAD_SM))
        ctk.CTkButton(
            linha, text="Restaurar de arquivo…",
            fg_color=theme.BG_SURFACE_ALT, hover_color=theme.BG_HOVER,
            text_color=theme.FG_PRIMARY, font=theme.FONT_BODY,
            command=self._restaurar,
        ).pack(side="left")

    # ------------------------------------------------------------------

    def _salvar_nome(self) -> None:
        try:
            configuracao_service.definir_nome_empresa(self.conn, self.entry_nome.get())
            self.app.atualizar_titulo()
            self._status("Nome da empresa atualizado.", ok=True)
        except Exception as e:
            self._status(str(e), ok=False)

    def _salvar_meta(self) -> None:
        try:
            configuracao_service.definir_meta_mensal(self.conn, self.entry_meta.centavos)
            self._status("Meta mensal atualizada.", ok=True)
        except Exception as e:
            self._status(str(e), ok=False)

    def _backup_agora(self) -> None:
        try:
            destino = backup.backup_agora(self.app.db_path)
            self._status(f"Backup criado em {destino.name}", ok=True)
        except Exception as e:
            self._status(str(e), ok=False)

    def _restaurar(self) -> None:
        arq = filedialog.askopenfilename(
            title="Selecione o arquivo de backup (.db)",
            filetypes=[("SQLite", "*.db"), ("Todos", "*.*")],
            parent=self.winfo_toplevel(),
        )
        if not arq:
            return
        confirmar = messagebox.askyesno(
            "Restaurar backup",
            "Isto vai substituir o banco atual pelo backup selecionado. "
            "Um snapshot 'pre_restore' do estado atual será salvo antes. Continuar?",
            parent=self.winfo_toplevel(),
        )
        if not confirmar:
            return
        try:
            # É necessário fechar a conexão antes de sobrescrever o arquivo.
            messagebox.showinfo(
                "Reinício necessário",
                "Após a restauração, feche e reabra o aplicativo.",
                parent=self.winfo_toplevel(),
            )
            self.conn.close()
            backup.restaurar(self.app.db_path, Path(arq), manter_pre_restore=True)
            self._status("Restauração concluída — feche e reabra o app.", ok=True)
        except Exception as e:
            self._status(str(e), ok=False)

    def _status(self, msg: str, *, ok: bool) -> None:
        cor = theme.OK if ok else theme.ERR
        prefixo = "✓" if ok else "✗"
        self.lbl_status.configure(text=f"{prefixo} {msg}", text_color=cor)
        self.after(4000, lambda: self.lbl_status.configure(text=""))
