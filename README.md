# Fluxo Barber

Aplicação desktop local (offline) para gestão financeira da barbearia **brodz** — substitui a planilha `fluxo_caixa.xlsx` por um `.exe` com entrada de dados rápida, governança e dashboards visuais.

Planejamento completo e decisões registradas em [`PLANO_FLUXO_BARBER.md`](PLANO_FLUXO_BARBER.md).

## Stack

- Python 3.10+
- CustomTkinter (UI)
- SQLite (persistência)
- matplotlib (gráficos)
- PyInstaller (empacotamento)

## Setup (desenvolvimento)

A raiz do repositório já é um virtualenv. No Windows (PowerShell):

```powershell
.\Scripts\Activate.ps1
pip install -r requirements.txt
```

Linux/macOS:

```bash
source bin/activate     # se usar venv tradicional
pip install -r requirements.txt
```

## Comandos úteis

```bash
# Inicializar um DB local e popular com o seed (Fase 0)
python -m app.repositories.db --init data/fluxo_barber.db

# Rodar testes
pytest

# Rodar testes com relatório de cobertura
pytest --cov=app --cov-report=term-missing
```

## Estrutura

```
fluxo_barber/
├── app/
│   ├── domain/          # dataclasses e enums
│   ├── repositories/    # SQLite + schema + seed
│   ├── services/        # regras de negócio (sem UI, sem SQL)
│   ├── ui/              # CustomTkinter (Fase 1+)
│   └── utils/           # formato, validadores, backup
├── data/                # DB local (gitignored)
├── tests/
├── resources/
└── PLANO_FLUXO_BARBER.md
```

## Status

- ✅ Fase 0 — Fundação (schema, seed, testes)
- ⏳ Fase 1 — MVP Lançamento
- ⏳ Fase 2 — Módulo de Assinaturas
- ⏳ Fase 3 — Dashboard & Relatórios
- ⏳ Fase 4 — Empacotamento e piloto
