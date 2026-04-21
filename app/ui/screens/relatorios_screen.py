"""Relatórios — exportação de fechamentos em XLSX.

Tela simples: o usuário escolhe o período (ou usa um atalho como
"Este mês" / "Hoje" / "Últimos 30 dias"), clica em **Exportar XLSX** e o
app gera um arquivo com várias abas prontas (Resumo, Receitas, Despesas,
Série diária, Ranking, Mix de pagamento, Despesas por categoria).

A geração usa :mod:`app.services.export_service` — mesma fonte de dados
do Dashboard, então os números batem com o que o dono vê na tela.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from app.services import export_service
from app.ui import theme
from app.ui.widgets.date_range import DateRangeSelector
from app.utils.formato import formatar_data
from app.utils.validators import ValidacaoError


class RelatoriosScreen(ctk.CTkFrame):
    def __init__(self, master, app_window) -> None:
        super().__init__(master, fg_color=theme.BG_APP, corner_radius=0)
        self.app = app_window
        self.conn = app_window.conn

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._construir_cabecalho()
        self._construir_card_export()

    # ------------------------------------------------------------------

    def _construir_cabecalho(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="we",
                    padx=theme.PAD_LG, pady=(theme.PAD_LG, theme.PAD_MD))
        ctk.CTkLabel(
            header, text="Relatórios",
            font=theme.FONT_H1, text_color=theme.FG_PRIMARY,
        ).pack(side="left")

    def _construir_card_export(self) -> None:
        container = ctk.CTkFrame(
            self, fg_color=theme.BG_SURFACE, corner_radius=theme.RADIUS_MD,
        )
        container.grid(row=1, column=0, sticky="nswe",
                       padx=theme.PAD_LG, pady=(0, theme.PAD_LG))
        container.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            container,
            text="Exportar fechamento em Excel (.xlsx)",
            font=theme.FONT_H2, text_color=theme.FG_PRIMARY,
            anchor="w",
        ).grid(row=0, column=0, sticky="we",
               padx=theme.PAD_LG, pady=(theme.PAD_LG, theme.PAD_SM))

        ctk.CTkLabel(
            container,
            text=(
                "Gera um arquivo com 7 abas:\n"
                "  •  Resumo — KPIs do período + progresso da meta mensal\n"
                "  •  Receitas — detalhe de todos os atendimentos\n"
                "  •  Despesas — detalhe com categoria e forma de pagamento\n"
                "  •  Série diária — receita, despesa e saldo por dia\n"
                "  •  Ranking de serviços — top serviços por faturamento\n"
                "  •  Mix de pagamento — composição da receita por forma\n"
                "  •  Despesas por categoria — agregado + % do período"
            ),
            font=theme.FONT_BODY, text_color=theme.FG_SECONDARY,
            justify="left", anchor="w",
        ).grid(row=1, column=0, sticky="we",
               padx=theme.PAD_LG, pady=(0, theme.PAD_MD))

        # Seletor de período
        periodo = ctk.CTkFrame(container, fg_color="transparent")
        periodo.grid(row=2, column=0, sticky="we",
                     padx=theme.PAD_LG, pady=(0, theme.PAD_MD))
        ctk.CTkLabel(
            periodo, text="Período:",
            font=theme.FONT_BODY_BOLD, text_color=theme.FG_PRIMARY,
        ).pack(side="left", padx=(0, theme.PAD_SM))
        self.date_range = DateRangeSelector(periodo, inicial="mes_atual")
        self.date_range.pack(side="left")

        # Ações
        acoes = ctk.CTkFrame(container, fg_color="transparent")
        acoes.grid(row=3, column=0, sticky="we",
                   padx=theme.PAD_LG, pady=(0, theme.PAD_LG))
        self.btn_exportar = ctk.CTkButton(
            acoes, text="Exportar XLSX",
            command=self._ao_exportar,
            font=theme.FONT_BODY_BOLD,
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
            text_color=theme.ACCENT_FG,
            height=theme.BTN_HEIGHT_LG, width=180, corner_radius=theme.RADIUS_MD,
        )
        self.btn_exportar.pack(side="left", padx=(0, theme.PAD_SM))

        self.lbl_status = ctk.CTkLabel(
            acoes, text="",
            font=theme.FONT_SMALL, text_color=theme.FG_SECONDARY,
        )
        self.lbl_status.pack(side="left", padx=theme.PAD_SM)

    # ------------------------------------------------------------------

    def _ao_exportar(self) -> None:
        try:
            de, ate = self.date_range.get_range()
        except Exception as e:
            messagebox.showwarning("Período inválido", str(e), parent=self)
            return

        nome_default = f"fluxo_barber_{de.isoformat()}_a_{ate.isoformat()}.xlsx"
        # Tenta abrir direto em ~/Documents (padrão Windows). Se não existir, deixa o Tk escolher.
        home_docs = Path.home() / "Documents"
        initial_dir = str(home_docs) if home_docs.exists() else str(Path.home())

        caminho = filedialog.asksaveasfilename(
            parent=self,
            title="Salvar relatório como",
            defaultextension=".xlsx",
            initialdir=initial_dir,
            initialfile=nome_default,
            filetypes=[("Excel 2007+", "*.xlsx")],
        )
        if not caminho:
            return  # usuário cancelou

        self.btn_exportar.configure(state="disabled")
        self.lbl_status.configure(text="Gerando arquivo…", text_color=theme.FG_SECONDARY)
        self.update_idletasks()

        try:
            arquivo = export_service.exportar_periodo_xlsx(
                self.conn, de, ate, Path(caminho),
            )
        except ValidacaoError as e:
            self.lbl_status.configure(text=f"Erro: {e}", text_color=theme.ERR)
            self.btn_exportar.configure(state="normal")
            messagebox.showwarning("Não foi possível exportar", str(e), parent=self)
            return
        except Exception as e:  # noqa: BLE001 — queremos capturar tudo para mostrar na UI
            self.lbl_status.configure(text="Falha inesperada", text_color=theme.ERR)
            self.btn_exportar.configure(state="normal")
            messagebox.showerror(
                "Erro ao exportar",
                f"Não foi possível gerar o arquivo:\n{e}",
                parent=self,
            )
            return

        # Sucesso
        self.btn_exportar.configure(state="normal")
        self.lbl_status.configure(
            text=f"Salvo: {arquivo.name}  ·  período {formatar_data(de)} → {formatar_data(ate)}",
            text_color=theme.OK,
        )
        # Pergunta se quer abrir o arquivo
        if messagebox.askyesno(
            "Exportação concluída",
            f"Arquivo salvo em:\n{arquivo}\n\nDeseja abrir agora?",
            parent=self,
        ):
            _abrir_arquivo(arquivo)


def _abrir_arquivo(caminho: Path) -> None:
    """Abre o arquivo no aplicativo default do OS (Excel / LibreOffice / etc)."""
    try:
        if sys.platform == "win32":
            os.startfile(str(caminho))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(caminho)])
        else:
            subprocess.Popen(["xdg-open", str(caminho)])
    except Exception:
        # Silenciosamente falha — o status já mostrou o caminho; o usuário abre manual.
        pass
