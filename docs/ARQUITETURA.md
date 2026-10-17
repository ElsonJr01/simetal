# Arquitetura

```
Navegador ─▶ Vercel ─▶ api/index.py (FastAPI)
                         ├─ routers/web.py   páginas HTML (Jinja2 + HTMX)
                         ├─ routers/api.py   API REST /api/v1 (JSON, /docs)
                         ├─ services.py      casos de uso (orquestra core + banco)
                         ├─ core/            cálculo puro (NumPy), sem web nem banco
                         └─ models.py/db.py  SQLAlchemy ─▶ PostgreSQL (Neon) | SQLite (dev/teste)
```

Regras de dependência: `routers → services → core` e `services → models`. O `core` não importa nada do restante do app.

## Mapa dos casos de uso (documento de projeto)
| UC | Onde está |
|---|---|
| UC01 Autenticar | `security.py`, `deps.py`, rotas `/login`, `/api/v1/auth/*` |
| UC02 Cadastrar usina | `routers/web.py::criar_usina`, `POST /api/v1/usinas` |
| UC03/UC04 Fluxograma e validação | `core/flowsheet.py`, `services.save_flowsheet` |
| UC05/UC07 Medidas e não amostrado | `services.save_measures` |
| UC06 Média e desvio de amostras | `core/statistics.py`, `POST /api/v1/estatistica/resumo` |
| UC08/UC09 Balanço de massas / metalúrgico | `core/reconcile.py`, `services.run_adjustment` |
| UC10/UC11 Iteração e convergência | `core/iteration.py`, `POST /campanhas/{id}/iterar` |
| UC12 Diagnóstico | `core/diagnostics.py` |
| UC13 Comparar campanhas, UC14 Exportar, UC15 Importar, UC16 Admin | **não implementados na v0.1** (ver roadmap) |

## Integrações com dados públicos (`app/integrations/`)
`http.py` (timeout, cache em memória, `IntegrationError`), `ibge.py`, `openmeteo.py`, `anm.py` (catálogo estático).
Regra: falha externa nunca derruba cálculo; é tratada nas rotas com mensagem amigável. Em testes a rede é substituída
(`http._request`), então a suíte roda offline.

## Decisões
- **Pesos 1/σ²** e solução do sistema KKT por Gauss próprio com pivoteamento; a forma fechada `x − ΣMᵀ(MΣMᵀ)⁻¹Mx` serve de verificação cruzada nos testes.
- **Balanço metalúrgico** usa as vazões ajustadas mais recentes como constantes e reconcilia c = W·X.
- **Ação "usar ajustado"** troca o valor mas mantém o σ anterior (é o que a Tabela 1 da monografia mostra; o código Pascal original zerava o σ para o valor).
- **Histórico imutável:** cada iteração é um registro `Ajuste` com seus `ResultadoFluxo`.
- **Frontend sem build:** Jinja2 + HTMX + Plotly via CDN (versões fixadas em `base.html`).
