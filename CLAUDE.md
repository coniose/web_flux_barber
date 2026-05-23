# flux_barber_web

App de gestão financeira para a barbearia **brodz** — substitui a planilha Excel por desktop app (CustomTkinter) + CLI + componente web. SQLite local, deploy Railway.

GitHub: coniose/web_flux_barber
Fase atual: Fase 1 em andamento (Fase 0 concluída, PRs #1/#2/#3 mergeados).

## Segundo cérebro (obsidianizer)

Contexto completo e backlog em: `obsidianizer-brain/Projetos/flux_barber_web/` no Google Drive.
Heartbeat: diário às 8am Brasília.

## Regras arquiteturais invioláveis

- UI não fala com DB direto — sempre via services
- Services não usam Tkinter — Python puro, testável
- Repositories são o único lugar com SQL
- Valores monetários em centavos (INTEGER), nunca float
