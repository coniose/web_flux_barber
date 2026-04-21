"""Tela Lançar — entrada rápida de atendimentos e despesas.

Organizada em duas abas:
  1. Atendimento: grid de 37 serviços; 1 clique abre modal pré-preenchido.
  2. Despesa: grid de itens frequentes + botão "Outra despesa" (genérica).

O painel lateral direito mostra o resumo do dia em tempo real:
  Receita, Despesas, Saldo, Nº de atendimentos.

Atalhos:
  Ctrl+1 → aba Atendimento     Ctrl+2 → aba Despesa
  Esc    → fechar modal aberto (tratado no modal)
"""

from __future__ import annotations

from datetime import date
from typing import Optional

import customtkinter as ctk

from app.domain.enums import FormaPagamento
from app.repositories import item_frequente_repo, servico_repo
from app.services import despesa_service, receita_service
from app.ui import theme
from app.ui.widgets.modal_atendimento import ModalAtendimento
from app.ui.widgets.modal_despesa import ModalDespesa
from app.ui.widgets.service_button import FrequentExpenseButton, ServiceButton
from app.utils.formato import formatar_moeda


class LancarScreen(ctk.CTkFrame):
    """Tela principal de lançamento rápido."""

    def __init__(self, master, app_window) -> None:
        super().__init__(master, fg_color=theme.BG_APP, corner_radius=0)
        self.app = app_window
        self.conn = app_window.conn

        # Grid raiz: coluna 0 = conteúdo, coluna 1 = painel lateral
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(0, weight=0)  # cabeçalho
        self.grid_rowconfigure(1, weight=1)  # conteúdo

        self._construir_cabecalho()
        self._construir_conteudo()
        self._construir_painel_resumo()

        # Atalhos de teclado (registrados no toplevel)
        self.app.bind("<Control-Key-1>", lambda e: self._trocar_aba("atendimento"))
        self.app.bind("<Control-Key-2>", lambda e: self._trocar_aba("despesa"))

    # ------------------------------------------------------------------
    # Cabeçalho
    # ------------------------------------------------------------------

    def _construir_cabecalho(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="we",
                    padx=theme.PAD_LG, pady=(theme.PAD_LG, theme.PAD_SM))

        ctk.CTkLabel(
            header, text="Lançar",
            font=theme.FONT_H1, text_color=theme.FG_PRIMARY,
        ).pack(side="left")

        ctk.CTkLabel(
            header, text=date.today().strftime("%d/%m/%Y"),
            font=theme.FONT_BODY, text_color=theme.FG_SECONDARY,
        ).pack(side="right")

    # ------------------------------------------------------------------
    # Conteúdo (abas)
    # ------------------------------------------------------------------

    def _construir_conteudo(self) -> None:
        self.tabs = ctk.CTkTabview(
            self,
            fg_color=theme.BG_SURFACE,
            segmented_button_fg_color=theme.BG_SURFACE_ALT,
            segmented_button_selected_color=theme.ACCENT,
            segmented_button_selected_hover_color=theme.ACCENT_HOVER,
            segmented_button_unselected_color=theme.BG_SURFACE_ALT,
            segmented_button_unselected_hover_color=theme.BG_HOVER,
            text_color=theme.FG_PRIMARY,
            corner_radius=theme.RADIUS_MD,
        )
        self.tabs.grid(row=1, column=0, sticky="nswe",
                       padx=(theme.PAD_LG, theme.PAD_SM),
                       pady=(0, theme.PAD_LG))

        self.tabs.add("Atendimento")
        self.tabs.add("Despesa")
        self._preencher_aba_atendimento(self.tabs.tab("Atendimento"))
        self._preencher_aba_despesa(self.tabs.tab("Despesa"))

    def _trocar_aba(self, chave: str) -> None:
        try:
            if chave == "atendimento":
                self.tabs.set("Atendimento")
            else:
                self.tabs.set("Despesa")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Aba Atendimento
    # ------------------------------------------------------------------

    def _preencher_aba_atendimento(self, parent) -> None:
        # Scroll para acomodar 37 serviços.
        scroll = ctk.CTkScrollableFrame(
            parent, fg_color="transparent",
            scrollbar_fg_color=theme.BG_SURFACE,
            scrollbar_button_color=theme.BG_HOVER,
        )
        scroll.pack(fill="both", expand=True, padx=theme.PAD_SM, pady=theme.PAD_SM)

        servicos = servico_repo.listar_ativos(self.conn)
        cols = 4
        for i, s in enumerate(servicos):
            ServiceButton(
                scroll,
                servico_id=s["id"],
                nome=s["nome"],
                preco_centavos=s["preco_padrao"],
                on_click=self._abrir_modal_atendimento,
            ).grid(
                row=i // cols, column=i % cols,
                padx=theme.PAD_XS, pady=theme.PAD_XS, sticky="we",
            )
        for c in range(cols):
            scroll.grid_columnconfigure(c, weight=1)

    def _abrir_modal_atendimento(self, servico_id: int, preco: int) -> None:
        # Atalho: registra direto com preço sugerido e PIX, sem modal.
        # Estratégia: sempre abrir o modal para que o atendente possa ajustar
        # valor/forma se necessário. Mantém consistência com "Outra despesa".
        modal = ModalAtendimento(
            self.winfo_toplevel(), self.conn,
            registro=None,
            on_ok=self._atualizar_resumo,
        )
        # Pré-seleciona o serviço clicado.
        nome = next(
            (s["nome"] for s in servico_repo.listar_ativos(self.conn) if s["id"] == servico_id),
            None,
        )
        if nome:
            modal.combo_servico.set(nome)
            modal.entry_valor.set_centavos(preco)

    # ------------------------------------------------------------------
    # Aba Despesa
    # ------------------------------------------------------------------

    def _preencher_aba_despesa(self, parent) -> None:
        # Scroll principal
        scroll = ctk.CTkScrollableFrame(
            parent, fg_color="transparent",
            scrollbar_fg_color=theme.BG_SURFACE,
            scrollbar_button_color=theme.BG_HOVER,
        )
        scroll.pack(fill="both", expand=True, padx=theme.PAD_SM, pady=theme.PAD_SM)

        # Legenda
        ctk.CTkLabel(
            scroll, text="Itens frequentes (1 clique registra com valor sugerido)",
            font=theme.FONT_H3, text_color=theme.FG_SECONDARY,
        ).pack(anchor="w", padx=theme.PAD_SM, pady=(theme.PAD_XS, theme.PAD_SM))

        self._frame_itens = ctk.CTkFrame(scroll, fg_color="transparent")
        self._frame_itens.pack(fill="x")
        self._render_itens_frequentes()

        # Separador
        ctk.CTkFrame(scroll, height=1, fg_color=theme.BORDER).pack(
            fill="x", pady=theme.PAD_MD, padx=theme.PAD_SM
        )

        # Botão despesa genérica
        ctk.CTkButton(
            scroll,
            text="Outra despesa (genérica)",
            fg_color=theme.ERR,
            hover_color=theme.ERR_DARK,
            text_color="#FFFFFF",
            font=theme.FONT_BODY_BOLD,
            height=theme.BTN_HEIGHT_LG,
            corner_radius=theme.RADIUS_MD,
            command=self._abrir_modal_despesa_generica,
        ).pack(fill="x", padx=theme.PAD_SM, pady=theme.PAD_XS)

    def _render_itens_frequentes(self) -> None:
        # Limpa filhos anteriores
        for w in self._frame_itens.winfo_children():
            w.destroy()

        itens = item_frequente_repo.listar_ativos_ordenado_por_uso(self.conn)
        cols = 4
        for i, it in enumerate(itens):
            FrequentExpenseButton(
                self._frame_itens,
                item_id=it["id"],
                descricao=it["descricao"],
                valor_sugerido_centavos=it["valor_sugerido"] or 0,
                on_click=self._registrar_item_frequente,
            ).grid(
                row=i // cols, column=i % cols,
                padx=theme.PAD_XS, pady=theme.PAD_XS, sticky="we",
            )
        for c in range(cols):
            self._frame_itens.grid_columnconfigure(c, weight=1)

    def _registrar_item_frequente(self, item_id: int, valor_sugerido: int) -> None:
        # 1 clique: registra direto com valor sugerido e DINHEIRO.
        try:
            despesa_service.registrar_item_frequente(
                self.conn, item_id, forma_pagamento=FormaPagamento.DINHEIRO
            )
            self._render_itens_frequentes()  # re-ordena por uso
            self._atualizar_resumo()
            self._flash_sucesso("Despesa registrada")
        except Exception as e:
            self._flash_erro(str(e))

    def _abrir_modal_despesa_generica(self) -> None:
        ModalDespesa(
            self.winfo_toplevel(), self.conn,
            registro=None,
            on_ok=self._atualizar_resumo,
        )

    # ------------------------------------------------------------------
    # Painel lateral: resumo do dia
    # ------------------------------------------------------------------

    def _construir_painel_resumo(self) -> None:
        painel = ctk.CTkFrame(
            self, fg_color=theme.BG_SURFACE,
            corner_radius=theme.RADIUS_MD, width=260,
        )
        painel.grid(row=1, column=1, sticky="nswe",
                    padx=(0, theme.PAD_LG), pady=(0, theme.PAD_LG))
        painel.grid_propagate(False)

        ctk.CTkLabel(
            painel, text="Resumo do dia",
            font=theme.FONT_H3, text_color=theme.FG_SECONDARY,
        ).pack(pady=(theme.PAD_MD, theme.PAD_SM), padx=theme.PAD_MD, anchor="w")

        # Receita
        ctk.CTkLabel(painel, text="Receita", font=theme.FONT_SMALL,
                     text_color=theme.FG_MUTED).pack(anchor="w", padx=theme.PAD_MD)
        self.lbl_receita = ctk.CTkLabel(
            painel, text="R$ 0,00",
            font=theme.FONT_MONEY_BIG, text_color=theme.OK,
        )
        self.lbl_receita.pack(anchor="w", padx=theme.PAD_MD, pady=(0, theme.PAD_SM))

        # Despesas
        ctk.CTkLabel(painel, text="Despesas", font=theme.FONT_SMALL,
                     text_color=theme.FG_MUTED).pack(anchor="w", padx=theme.PAD_MD)
        self.lbl_despesas = ctk.CTkLabel(
            painel, text="R$ 0,00",
            font=theme.FONT_MONEY_BIG, text_color=theme.ERR,
        )
        self.lbl_despesas.pack(anchor="w", padx=theme.PAD_MD, pady=(0, theme.PAD_SM))

        # Saldo
        ctk.CTkFrame(painel, height=1, fg_color=theme.BORDER).pack(
            fill="x", padx=theme.PAD_MD, pady=theme.PAD_SM
        )
        ctk.CTkLabel(painel, text="Saldo", font=theme.FONT_SMALL,
                     text_color=theme.FG_MUTED).pack(anchor="w", padx=theme.PAD_MD)
        self.lbl_saldo = ctk.CTkLabel(
            painel, text="R$ 0,00",
            font=theme.FONT_MONEY_BIG, text_color=theme.FG_PRIMARY,
        )
        self.lbl_saldo.pack(anchor="w", padx=theme.PAD_MD, pady=(0, theme.PAD_MD))

        ctk.CTkFrame(painel, height=1, fg_color=theme.BORDER).pack(
            fill="x", padx=theme.PAD_MD, pady=theme.PAD_SM
        )

        # Contagens
        self.lbl_qtd_atend = ctk.CTkLabel(
            painel, text="0 atendimentos",
            font=theme.FONT_BODY, text_color=theme.FG_SECONDARY,
        )
        self.lbl_qtd_atend.pack(anchor="w", padx=theme.PAD_MD, pady=2)
        self.lbl_qtd_desp = ctk.CTkLabel(
            painel, text="0 despesas",
            font=theme.FONT_BODY, text_color=theme.FG_SECONDARY,
        )
        self.lbl_qtd_desp.pack(anchor="w", padx=theme.PAD_MD, pady=2)

        # Feedback de ação
        self.lbl_flash = ctk.CTkLabel(
            painel, text="", font=theme.FONT_SMALL, text_color=theme.OK,
        )
        self.lbl_flash.pack(anchor="w", padx=theme.PAD_MD, pady=(theme.PAD_MD, 0))

    def _atualizar_resumo(self) -> None:
        hoje = date.today()
        rec = receita_service.totais_periodo(self.conn, hoje, hoje)
        desp = despesa_service.totais_periodo(self.conn, hoje, hoje)
        saldo = rec["total_centavos"] - desp["total_centavos"]

        self.lbl_receita.configure(text=formatar_moeda(rec["total_centavos"]))
        self.lbl_despesas.configure(text=formatar_moeda(desp["total_centavos"]))
        self.lbl_saldo.configure(
            text=formatar_moeda(saldo),
            text_color=theme.OK if saldo >= 0 else theme.ERR,
        )
        self.lbl_qtd_atend.configure(text=f"{rec['qtd_atendimentos']} atendimentos")
        self.lbl_qtd_desp.configure(text=f"{desp['qtd_despesas']} despesas")

    def _flash_sucesso(self, msg: str) -> None:
        self.lbl_flash.configure(text=f"✓ {msg}", text_color=theme.OK)
        self.after(2500, lambda: self.lbl_flash.configure(text=""))

    def _flash_erro(self, msg: str) -> None:
        self.lbl_flash.configure(text=f"✗ {msg}", text_color=theme.ERR)
        self.after(4000, lambda: self.lbl_flash.configure(text=""))

    # ------------------------------------------------------------------

    def ao_mostrar(self) -> None:
        """Chamado pelo app_window quando a tela fica visível."""
        self._atualizar_resumo