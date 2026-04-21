"""Modal para criar ou editar despesa."""

from __future__ import annotations

import sqlite3
from datetime import date
from typing import Callable, Dict, Optional

import customtkinter as ctk

from app.domain.enums import FormaPagamento
from app.repositories import categoria_repo
from app.services import despesa_service
from app.ui import theme
from app.ui.widgets.currency_entry import CurrencyEntry
from app.ui.widgets.payment_selector import PaymentSelector
from app.utils.validators import ValidacaoError


class ModalDespesa(ctk.CTkToplevel):
    """Modal para criar ou editar uma despesa genérica."""

    def __init__(
        self,
        master,
        conn: sqlite3.Connection,
        *,
        registro: Optional[Dict] = None,
        descricao_inicial: str = "",
        categoria_inicial_id: Optional[int] = None,
        valor_inicial: int = 0,
        on_ok: Callable[[], None],
    ) -> None:
        super().__init__(master)
        self._conn = conn
        self._registro = registro
        self._on_ok = on_ok

        titulo = "Editar despesa" if registro else "Nova despesa"
        self.title(titulo)
        self.configure(fg_color=theme.BG_APP)
        self.geometry("480x460")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self._categorias = categoria_repo.listar_ativas(conn)
        self._mapa_nome_id = {c["nome"]: c["id"] for c in self._categorias}
        self._mapa_id_nome = {c["id"]: c["nome"] for c in self._categorias}

        ctk.CTkLabel(
            self, text=titulo,
            font=theme.FONT_H2, text_color=theme.FG_PRIMARY,
        ).pack(pady=(theme.PAD_LG, theme.PAD_MD))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(padx=theme.PAD_LG, pady=theme.PAD_SM, fill="x")

        # Categoria
        ctk.CTkLabel(form, text="Categoria", text_color=theme.FG_SECONDARY, font=theme.FONT_BODY)\
            .grid(row=0, column=0, sticky="w", pady=(0, theme.PAD_XS))
        nomes = [c["nome"] for c in self._categorias]
        if registro:
            cat_ini = registro.get("categoria_nome") or self._mapa_id_nome.get(
                registro.get("categoria_id"), nomes[0]
            )
        elif categoria_inicial_id and categoria_inicial_id in self._mapa_id_nome:
            cat_ini = self._mapa_id_nome[categoria_inicial_id]
        else:
            cat_ini = nomes[0]
        self.combo_categoria = ctk.CTkComboBox(
            form, values=nomes, width=380,
            fg_color=theme.BG_SURFACE_ALT, border_color=theme.BORDER,
            button_color=theme.BG_HOVER, text_color=theme.FG_PRIMARY,
            dropdown_fg_color=theme.BG_SURFACE,
        )
        self.combo_categoria.set(cat_ini)
        self.combo_categoria.grid(row=1, column=0, sticky="w", pady=(0, theme.PAD_MD))

        # Descrição
        ctk.CTkLabel(form, text="Descrição", text_color=theme.FG_SECONDARY, font=theme.FONT_BODY)\
            .grid(row=2, column=0, sticky="w", pady=(0, theme.PAD_XS))
        self.entry_descricao = ctk.CTkEntry(
            form, width=380,
            fg_color=theme.BG_SURFACE_ALT, border_color=theme.BORDER,
            text_color=theme.FG_PRIMARY, font=theme.FONT_BODY,
        )
        desc = registro["descricao"] if registro else descricao_inicial
        if desc:
            self.entry_descricao.insert(0, desc)
        self.entry_descricao.grid(row=3, column=0, sticky="w", pady=(0, theme.PAD_MD))

        # Valor
        ctk.CTkLabel(form, text="Valor", text_color=theme.FG_SECONDARY, font=theme.FONT_BODY)\
            .grid(row=4, column=0, sticky="w", pady=(0, theme.PAD_XS))
        val_ini = registro["valor"] if registro else valor_inicial
        self.entry_valor = CurrencyEntry(form, valor_inicial_centavos=val_ini, width=200)
        self.entry_valor.grid(row=5, column=0, sticky="w", pady=(0, theme.PAD_MD))

        # Forma de pagamento
        ctk.CTkLabel(form, text="Forma de pagamento", text_color=theme.FG_SECONDARY, font=theme.FONT_BODY)\
            .grid(row=6, column=0, sticky="w", pady=(0, theme.PAD_XS))
        forma_ini = (
            FormaPagamento(registro["forma_pagamento"]) if registro and registro.get("forma_pagamento")
            else FormaPagamento.DINHEIRO
        )
        self.payment = PaymentSelector(form, valor_inicial=forma_ini)
        self.payment.grid(row=7, column=0, sticky="w", pady=(0, theme.PAD_MD))

        # Data
        ctk.CTkLabel(form, text="Data (DD/MM/AAAA — hoje se vazio)", text_color=theme.FG_SECONDARY, font=theme.FONT_BODY)\
            .grid(row=8, column=0, sticky="w", pady=(0, theme.PAD_XS))
        self.entry_data = ctk.CTkEntry(
            form, width=140,
            fg_color=theme.BG_SURFACE_ALT, border_color=theme.BORDER,
            text_color=theme.FG_PRIMARY, font=theme.FONT_BODY,
        )
        if registro and registro.get("data"):
            try:
                d = date.fromisoformat(registro["data"])
                self.entry_data.insert(0, d.strftime("%d/%m/%Y"))
            except ValueError:
                pass
        self.entry_data.grid(row=9, column=0, sticky="w", pady=(0, theme.PAD_SM))

        # Erro
        self.lbl_erro = ctk.CTkLabel(self, text="", text_color=theme.ERR, font=theme.FONT_SMALL)
        self.lbl_erro.pack(pady=(theme.PAD_SM, 0))

        # Botões
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(pady=theme.PAD_MD)
        ctk.CTkButton(
            btns, text="Cancelar", width=110,
            fg_color=theme.BG_SURFACE_ALT, hover_color=theme.BG_HOVER,
            text_color=theme.FG_SECONDARY, command=self.destroy,
        ).grid(row=0, column=0, padx=theme.PAD_XS)
        ctk.CTkButton(
            btns, text="Salvar", width=110,
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
            text_color=theme.ACCENT_FG, font=theme.FONT_BODY_BOLD,
            command=self._salvar,
        ).grid(row=0, column=1, padx=theme.PAD_XS)

        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Return>", lambda e: self._salvar())

        if desc:
            self.entry_valor.focus_set()
        else:
            self.entry_descricao.focus_set()

    # ------------------------------------------------------------------

    def _salvar(self) -> None:
        self.lbl_erro.configure(text="")
        try:
            cat_nome = self.combo_categoria.get()
            categoria_id = self._mapa_nome_id[cat_nome]
            descricao = self.entry_descricao.get().strip()
            valor = self.entry_valor.centavos
            forma = self.payment.get()

            data_txt = self.entry_data.get().strip()
            data_ref: Optional[date] = _parse_br(data_txt) if data_txt else None

            if self._registro:
                despesa_service.editar_despesa(
                    self._conn,
                    self._registro["id"],
                    categoria_id=categoria_id,
                    descricao=descricao,
                    valor_centavos=valor,
                    forma_pagamento=forma,
                    data_despesa=data_ref,
                )
            else:
                despesa_service.registrar_despesa(
                    self._conn,
                    categoria_id=categoria_id,
                    descricao=descricao,
                    valor_centavos=valor,
                    forma_pagamento=forma,
                    data_despesa=data_ref,
                )
            self._on_ok()
            self.destroy()
        except (ValidacaoError, ValueError, KeyError) as e:
            self.lbl_erro.configure(text=str(e))


def _parse_br(s: str) -> date:
    s = s.strip()
    if "/" in s:
        d, m, a = s.split("/")
        return date(int(a), int(m), int(d))
    return date.fromisoformat(s)
