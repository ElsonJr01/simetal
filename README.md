# SIMETAL

Sistema de ajuste e fechamento de balanço de massas e metalúrgico para usinas de beneficiamento mineral.
Reimplementação em Python do BALMAS (Damasceno & Nunes, EPUSP, 1992): mínimos quadrados ponderados com
restrições (multiplicadores de Lagrange) resolvidos por eliminação de Gauss, com iteração assistida pelo engenheiro.

Stack: Python 3.12 · FastAPI · SQLAlchemy 2 · PostgreSQL (Neon) · Jinja2 + HTMX + Plotly · NumPy.

## Rodar localmente

**Windows (PowerShell)**, dentro da pasta do projeto (onde está o `requirements.txt`):
```powershell
py -3.12 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
python -m uvicorn app.main:app --reload
```
**Linux/macOS:** `python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements-dev.txt && cp .env.example .env && python -m uvicorn app.main:app --reload`

Abra http://127.0.0.1:8000 (API em `/docs`). Sem configuração usa SQLite local (`simetal.db`).
Crie uma conta e use **Criar usina de exemplo** (circuito Cambuí da monografia).

### Criar o administrador
Opção 1: no `.env`, defina `SIMETAL_ADMIN_EMAIL` e `SIMETAL_ADMIN_PASSWORD` e reinicie: o admin é criado na partida.
Opção 2: `python -m app.cli create-admin --email voce@exemplo.com` (pede a senha no terminal; promove o e-mail se já existir).
Depois entre normalmente em **/login**; o link **Administração** aparece no topo.

### Testes
```powershell
python -m pytest --cov=app
```
Inclui a reprodução da iteração 1 das Tabelas 1 (massas) e 2 (cinzas) da monografia. A rede externa é simulada, então os testes rodam offline.

## Área administrativa (/admin)
Só para o perfil `admin`.
- **Painel:** usuários, usinas, ajustes, falhas de login (7 dias), estado do banco, abrir/fechar o cadastro público, teste ao vivo de IBGE e Open-Meteo.
- **Usuários:** buscar, mudar perfil (admin, engenheiro, visitante), ativar/desativar, desbloquear, redefinir senha (senha temporária mostrada uma vez), excluir (com as usinas). Não permite remover/desativar a si mesmo nem o último administrador.
- **Usinas:** todas as usinas de todos os usuários; abrir e excluir.
- **Auditoria:** trilha de ações administrativas e eventos de segurança (login falho, bloqueio, cadastro).
- **Identidade visual:** estado de cada arquivo de marca.
Perfil **visitante** é somente leitura.

## Segurança e robustez
- Senhas com argon2; sessão em cookie HTTP-only (`Secure` em produção) ou `Authorization: Bearer`.
- **CSRF** em todos os formulários e chamadas HTMX; cabeçalhos de segurança; ID de requisição (`X-Request-ID`) nos logs.
- **Bloqueio de conta** após 5 falhas (15 min, configurável), registrado na auditoria; conta desativada perde a sessão imediatamente.
- Em produção o app **se recusa a iniciar** sem `SIMETAL_SECRET_KEY` forte (32+ caracteres).
- Páginas de erro amigáveis (403/404/500) sem expor detalhes internos; `GET /api/v1/health` e `/api/v1/health/ready` (confere o banco).
- Atualização de colunas em bancos antigos na partida (desenvolvimento) e migração Alembic inicial (`migrations/versions/0001_inicial.py`).
- Redefinir o fluxograma preserva as medidas dos fluxos que continuam existindo.
- Limites de tamanho (100 fluxos, 100 operações) e validação de dados em todas as entradas.

## Dados públicos integrados
| Fonte | Uso | Observações |
|---|---|---|
| **IBGE** (Localidades) | Estado e município da usina | Aberta, sem chave. Cache de 24 h. |
| **Open-Meteo** | Temperatura e chuva no local da usina | Sem chave; **gratuito só para uso não comercial**, com atribuição (já exibida). |
| **ANM** (dados abertos) | Catálogo de conjuntos com links oficiais | A ANM publica **arquivos**; não há chamada automática. |

Falha de uma fonte nunca quebra o cálculo. Desligue com `SIMETAL_INTEGRATIONS_ENABLED=false`.

## Acessibilidade e ajuda
**VLibras** em todas as páginas (`SIMETAL_VLIBRAS_ENABLED`) e **mascote de dicas** (`SIMETAL_MASCOT_ENABLED`). API aberta de dicas: `GET /api/v1/dicas`.

## Identidade visual
Logos e imagens têm **locais e nomes fixos em PNG** em `app/static/brand/`: `logo.png`, `logo-dark.png`, `logo-mark.png`, `favicon.png`,
`hero.png`, `empty-state.png`, `og-image.png`, `mascot.png`, `institution-logo.png`. Tamanhos e usos em **docs/IDENTIDADE_VISUAL.md**; cores e fontes em `app/static/css/brand.css`.

## Deploy de teste no Vercel
1. Crie um banco PostgreSQL no Neon e copie a connection string.
2. Importe o repositório no Vercel e defina as variáveis:
   - `SIMETAL_ENV=production`
   - `SIMETAL_SECRET_KEY=<32+ caracteres aleatórios>`
   - `SIMETAL_DATABASE_URL=<connection string do Neon>`
   - `SIMETAL_ADMIN_EMAIL` e `SIMETAL_ADMIN_PASSWORD` (cria o primeiro admin; depois remova a senha do ambiente)
   - `SIMETAL_AUTO_CREATE_TABLES=true` só no teste. Para um banco de verdade: `alembic upgrade head` apontando para o Neon.
3. Deploy. O `vercel.json` encaminha tudo para `api/index.py`. Confira na documentação atual do Vercel o suporte a FastAPI/ASGI e `includeFiles`.
Atenção: o disco do Vercel não guarda arquivos enviados; as imagens de marca entram pelo repositório.

## Estrutura
```
api/index.py            entrypoint do Vercel
app/core/               núcleo de cálculo (puro, testado)
app/models.py, db.py    tabelas, engine, atualização de colunas
app/services.py         casos de uso do balanço
app/auth_service.py     login, bloqueio, auditoria, admin inicial
app/admin_service.py    regras da área /admin
app/routers/            api.py (REST), web.py (HTML), admin.py (/admin)
app/integrations/       IBGE, Open-Meteo, catálogo ANM
app/brand.py            locais fixos dos arquivos de marca
app/templates, static/  interface e identidade visual
migrations/             Alembic (0001_inicial)
scripts/                gerar_placeholders.py
tests/                  unit (core, integrações) e integration (API, web, admin)
docs/                   arquitetura e identidade visual
```

## Limitações conhecidas
- O ajuste linear não impõe valores não negativos (apenas avisa).
- Sem importação/exportação nem comparação de campanhas (UC13 a UC15).
- Sem recuperação de senha por e-mail (o admin gera senha temporária).
- Sem CSP; o cabeçalho de segurança cobre o básico.
