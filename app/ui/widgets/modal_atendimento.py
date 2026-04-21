"""Modal para editar ou criar atendimento avulso."""

from __future__ import annotations

import sqlite3
from datetime import date
from typing import Callable, Dict, Optional

import customtkinter as ctk

from app.domain.enums import FormaPagamento
from app.repositories import servico_repo
from app.services import receita_service
from app.ui import theme
from app.ui.widgets.currency_entry import CurrencyEntry
from app.ui.widgets.payment_selector import PaymentSelector
from app.utils.validators import ValidacaoError


class ModalAtendimento(ctk.CTkToplevel):
    """Modal para criar ou editar uma receita (atendimento)."""

    def __init__(
        self,
        master,
        conn: sqlite3.Connection,
        *,
        registro: Optional[Dict] = None,
        on_ok: Callable[[], None],
    ) -> None:
        super().__init__(master)
        self._conn = conn
        self._registro = registro
        self._on_ok = on_ok

        titulo = "Editar atendimento" if registro else "Novo atendimento"
        self.title(titulo)
        self.configure(fg_color=theme.BG_APP)
        self.geometry("480x500")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        # Serviços para o dropdown
        self._servicos = servico_repo.listar_ativos(conn)
        self._mapa_nome_id = {s["nome"]: s["id"] for s in self._servicos}

        ctk.CTkLabel(
            self, text=titulo,
            font=theme.FONT_H2, text_color=theme.FG_PRIMARY,
        ).pack(pady=(theme.PAD_LG, theme.PAD_MD))

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(padx=theme.PAD_LG, pady=theme.PAD_SM, fill="x")

        # Serviço
        ctk.CTkLabel(form, text="Serviço", text_color=theme.FG_SECONDARY, font=theme.FONT_BODY)\
            .grid(row=0, column=0, sticky="w", pady=(0, theme.PAD_XS))
        nomes = [s["nome"] for s in self._servicos]
        nome_inicial = registro["servico_nome"] if registro else nomes[0]
        self.combo_servico = ctk.CTkComboBox(
            form, values=nomes, width=380,
            fg_color=theme.BG_SURFACE_ALT, border_color=theme.BORDER,
            button_color=theme.BG_HOVER, text_color=theme.FG_PRIMARY,
            dropdown_fg_color=theme.BG_SURFACE,
            command=self._on_servico_change,
        )
        self.combo_servico.set(nome_inicial)
        self.combo_servico.grid(row=1, column=0, sticky="w", pady=(0, theme.PAD_MD))

        # Valor
        ctk.CTkLabel(form, text="Valor", text_color=theme.FG_SECONDARY, font=theme.FONT_BODY)\
            .grid(row=2, column=0, sticky="w", pady=(0, theme.PAD_XS))
        val_inicial = registro["valor"] if registro else self._preco_sugerido(nome_inicial)
        self.entry_valor = CurrencyEntry(form, valor_inicial_centavos=val_inicial, width=200)
        self.entry_valor.grid(row=3, column=0, sticky="w", pady=(0, theme.PAD_MD))

        # Forma de pagamento
        ctk.CTkLabel(form, text="Forma de pagamento", text_color=theme.FG_SECONDARY, font=theme.FONT_BODY)\
            .grid(row=4, column=0, sticky="w", pady=(0, theme.PAD_XS))
        forma_inicial = (
            FormaPagamento(registro["forma_pagamento"]) if registro and registro.get("forma_pagamento")
            else FormaPagamento.PIX
        )
        self.payment = PaymentSelector(form, valor_inicial=forma_inicial)
        self.payment.grid(row=5, column=0, sticky="w", pady=(0, theme.PAD_MD))

        # Data
        ctk.CTkLabel(form, text="Data (DD/MM/AAAA — hoje se vazio)", text_color=theme.FG_SECONDARY, font=theme.FONT_BODY)\
            .grid(row=6, column=0, sticky="w", pady=(0, theme.PAD_XS))
        self.entry_data = ctk.CTkEntry(
            form, width=140,
            fg_color=theme.BG_SURFACE_ALT, border_color=theme.BORDER,
            text_color=theme.FG_PRIMARY, font=theme.FONT_BODY,
        )
        data_str = registro["data"] if registro else ""
        if data_str:
            try:
                d = date.fromisoformat(data_str)
                self.entry_data.insert(0, d.strftime("%d/%m/%Y"))
            except ValueError:
                self.entry_data.insert(0, data_str)
        self.entry_data.grid(row=7, column=0, sticky="w", pady=(0, theme.PAD_SM))

        # Erro
        self.lbl_erro = ctk.CTkLabel(self, text="", text_color=theme.ERR, font=theme.FONT_SMALL)
        self.lbl_erro.pack(side="bottom", fill="x", padx=theme.PAD_LG, pady=(0, theme.PAD_SM))

        # Botões
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(side="bottom", fill="x", padx=theme.PAD_LG, pady=theme.PAD_MD)
        ctk.CTkButton(
            btns, text="Cancelar", width=110,
            fg_color=theme.BG_SURFACE_ALT, hover_color=theme.BG_HOVER,
            text_color=theme.FG_SECONDARY, command=self.destroy,
        ).pack(side="right", padx=(theme.PAD_XS, 0))
        ctk.CTkButton(
            btns, text="Confirmar Lançamento",
            height=theme.BTN_HEIGHT,
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
            text_color=theme.ACCENT_FG, font=theme.FONT_BODY_BOLD,
            command=self._salvar,
        ).pack(side="right", padx=(0, theme.PAD_XS))

        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Return>", lambda e: self._salvar())
        self.entry_valor.focus_set()

    # ------------------------------------------------------------------

    def _preco_sugerido(self, nome: str) -> int:
        for s in self._servicos:
            if s["nome"] == nome:
                return s["preco_padrao"]
        return 0

    def _on_servico_change(self, nome: str) -> None:
        # Quando muda o serviço, só atualiza o preço se for criação.
        if self._registro is None:
            self.entry_valor.set_centavos(self._preco_sugerido(nome))

    def _salvar(self) -> None:
        self.lbl_erro.configure(text="")
        try:
            servico_id = self._mapa_nome_id[self.combo_servico.get()]
            valor = self.entry_valor.centavos
            forma = self.payment.get()

            data_txt = self.entry_data.get().strip()
            data_ref: Optional[date] = None
            permitir_futuro = False
            if data_txt:
                data_ref = _parse_br(data_txt)
                if data_ref > date.today():
                    permitir_futuro = True  # UX: se o usuário digitou, ele sabe.

            if self._registro:
                receita_service.editar_atendimento(
                    self._conn,
                    self._registro["id"],
                    servico_id=servico_id,
                    valor_centavos=valor,
                    forma_pagamento=forma,
                    data_atendimento=data_ref,
                )
            else:
                receita_service.registrar_atendimento_avulso(
                    self._conn,
                    servico_id=servico_id,
                    valor_centavos=valor,
                    forma_pagamento=forma,
                    data_atendimento=data_ref,
                    permitir_data_futura=permitir_futuro,
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
