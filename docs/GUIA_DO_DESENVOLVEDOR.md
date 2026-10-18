# Guia do desenvolvedor

Para quem vai mexer no código. Se você só quer **usar** o sistema, abra `/ajuda` no próprio SIMETAL.

## 1. A ideia em três camadas

```
Navegador ──▶ routers/ (HTTP) ──▶ services.py (casos de uso) ──▶ core/ (cálculo puro)
                  │                      │
                  │                      └──▶ models.py / db.py (banco)
                  └──▶ templates/ (HTML)   └──▶ integrations/ (IBGE, Open-Meteo)
```

Regra de ouro: **`core/` não importa nada do resto do app** (só NumPy). É onde mora a matemática, e é testado sem web nem banco.

## 2. Mapa das pastas

| Pasta/arquivo | O que tem | Mexa aqui quando... |
|---|---|---|
| `app/core/` | `reconcile.py` (ajuste), `solver.py` (Gauss), `flowsheet.py` (matriz M), `diagnostics.py` (alertas), `indicators.py` (recuperação etc.), `observability.py` (redundância), `statistics.py`, `iteration.py` | mudar ou criar cálculo |
| `app/services.py` | casos de uso que ligam core + banco (ajustar, iterar, importar, exportar...) | mudar uma regra de negócio |
| `app/routers/` | `api.py` (JSON), `web.py` (páginas), `admin.py` (/admin), `help.py` (ajuda pública) | criar ou alterar rotas |
| `app/content/` | `glossary.py`, `faq.py`, `tips.py` (dicas do mascote) | editar **textos** sem tocar em código de lógica |
| `app/templates/` | HTML (Jinja2): `base.html` tem cabeçalho e rodapé; `ajuda/`, `admin/`, `partials/` | mudar a aparência/texto de uma tela |
| `app/static/` | `css/brand.css` (cores/fontes), `css/main.css`, `js/`, `brand/` (logos e imagens) | identidade visual |
| `app/models.py`, `db.py`, `migrations/` | tabelas, conexão, Alembic | mudar o banco |
| `app/auth_service.py`, `csrf.py`, `middleware.py`, `deps.py` | segurança | mudar login, bloqueio, CSRF, perfis |
| `tests/` | `unit/` (core, domínio, integrações) e `integration/` (API, web, admin, ajuda) | sempre que mudar algo |

## 3. Acompanhando uma requisição: "Fechar balanço de massa"

1. O botão da página da campanha (`templates/campanha.html`) faz `hx-post` para `/campanhas/{id}/ajustar`.
2. `routers/web.py::ajustar` confere o login (`deps.current_user`) e a posse da campanha (`get_owned_campanha`).
3. Chama `services.run_adjustment`, que monta a matriz M (`build_flowsheet`), lê as medidas e chama `core.reconcile`.
4. `core/reconcile.py` monta o sistema KKT, resolve com `core/solver.py` (Gauss) e devolve ajustados, χ² e z.
5. O serviço grava um `Ajuste` com seus `ResultadoFluxo` (histórico imutável) e calcula os alertas (`core/diagnostics.py`).
6. A rota renderiza `partials/_resultado.html` e o HTMX troca só a tabela na página.

## 4. Receitas

**Adicionar um termo ao glossário / uma pergunta ao FAQ / uma dica do mascote:** edite `app/content/glossary.py`, `faq.py` ou `tips.py`. Os testes (`tests/unit/test_domain.py`) garantem termos únicos e referências "ver também" válidas.

**Criar uma página de ajuda:** acrescente a rota em `routers/help.py`, crie `templates/ajuda/<nome>.html` (estenda `base.html` e inclua `ajuda/_nav.html`) e um item na lista de `ajuda/_nav.html` e no rodapé (`base.html`).

**Adicionar um cálculo:** escreva a função pura em `app/core/`, exporte em `core/__init__.py`, teste em `tests/unit/`; só depois ligue em `services.py` e na rota.

**Adicionar uma coluna ao banco:** edite `models.py`; gere a migração (`alembic revision --autogenerate -m "descrição" --rev-id 000N`), revise o arquivo (cuidado com `server_default` de booleanos: use `sa.true()`/`sa.false()`) e rode `alembic upgrade head`. Em desenvolvimento, `init_db()` também adiciona colunas simples sozinho.

**Adicionar uma tela de administração:** rota em `routers/admin.py` (já exige `require_admin` e CSRF), regra em `admin_service.py`, template em `templates/admin/` e item em `admin/_nav.html`. Registre ações relevantes com `auth_service.audit`.

**Trocar logos e imagens:** substitua os PNGs de `app/static/brand/` mantendo os nomes (`docs/IDENTIDADE_VISUAL.md`). `/admin/identidade` mostra o estado de cada um.

## 5. Convenções

- Interface e mensagens em **português do Brasil**; números formatados com o filtro `|num` (`3.750,82`).
- Formulários `method="post"` levam `<input type="hidden" name="csrf_token" value="{{ csrf_token }}">`; chamadas HTMX enviam o token por cabeçalho (já configurado em `app.js`).
- Erros esperados viram `ServiceError`/`AdminError` com mensagem pronta para o usuário; falhas de fontes externas viram `IntegrationError` e nunca derrubam o cálculo.
- Todo texto vindo do usuário é escapado pelo Jinja (autoescape); não use `|safe` em dados do usuário.
- Teste o que mudar: `python -m pytest`. O teste de aceitação do cálculo reproduz as Tabelas 1 e 2 da monografia (iteração 1).

## 6. Checklist antes de usar com dados reais

- [ ] `SIMETAL_ENV=production` e `SIMETAL_SECRET_KEY` com 32+ caracteres aleatórios.
- [ ] Banco PostgreSQL e migrações aplicadas (`alembic upgrade head`); `SIMETAL_AUTO_CREATE_TABLES=false`.
- [ ] Administrador criado; `SIMETAL_ADMIN_PASSWORD` removida do ambiente depois do primeiro acesso.
- [ ] Cadastro público fechado em `/admin` (ou convite controlado).
- [ ] **Revisão dos textos de privacidade e termos** (`templates/ajuda/sobre.html`) pela instituição responsável (LGPD).
- [ ] **Licença do código** definida (não há arquivo `LICENSE`; escolha com a sua instituição).
- [ ] Open-Meteo: o uso gratuito é só **não comercial**; para uso comercial, contrate o plano deles.
- [ ] Rotina de backup do banco (use os recursos do provedor e teste a restauração).
- [ ] Imagens de marca definitivas (sem placeholders em `/admin/identidade`).
- [ ] Revisão técnica do conteúdo de `app/content/` por um engenheiro de processo.
- [ ] Ajustes de segurança adicionais se a exposição for pública: política CSP, limitação de taxa em borda, recuperação de senha por e-mail.

## 7. Problemas comuns no Windows

- `python` abre o do LibreOffice: use `py -3.12 -m venv .venv`.
- Ativar o ambiente: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` e `.\.venv\Scripts\Activate.ps1`.
- Não use `echo texto >> arquivo` no PowerShell 5.1 (grava UTF-16): edite no VS Code, em UTF-8.
- `Copy-Item .env.example .env` só na **primeira** vez: ele sobrescreve o seu `.env`.
- O `--reload` não observa o `.env`: reinicie o servidor ao mudá-lo.
