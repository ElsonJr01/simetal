 .env.example                             |  18 [32m+[m[31m--[m
 .gitignore                               |   2 [31m-[m
 Makefile                                 |   6 [32m+[m[31m-[m
 README.md                                | 119 [32m+++++++[m[31m-----------[m
 alembic.ini                              |   1 [31m-[m
 app/__init__.py                          |   6 [32m+[m[31m-[m
 app/admin_service.py                     | 197 [31m------------------------------[m
 app/auth_service.py                      | 122 [31m-------------------[m
 app/brand.py                             |  86 [31m-------------[m
 app/cli.py                               |  57 [31m---------[m
 app/config.py                            |  68 [32m++++[m[31m-------[m
 app/csrf.py                              |  37 [31m------[m
 app/db.py                                |  48 [32m+[m[31m-------[m
 app/deps.py                              |  20 [32m+[m[31m--[m
 app/main.py                              |  43 [32m+[m[31m------[m
 app/middleware.py                        |  36 [31m------[m
 app/models.py                            |  33 [32m+[m[31m----[m
 app/routers/admin.py                     | 131 [31m--------------------[m
 app/routers/api.py                       |  31 [32m++[m[31m---[m
 app/routers/web.py                       |  46 [32m+++[m[31m----[m
 app/services.py                          |  25 [32m+[m[31m---[m
 app/static/brand/README.md               |   9 [32m+[m[31m-[m
 app/static/brand/empty-state.png         | Bin [31m10084[m -> [32m0[m bytes
 app/static/brand/favicon.png             | Bin [31m1933[m -> [32m0[m bytes
 app/static/brand/hero.png                | Bin [31m19776[m -> [32m0[m bytes
 app/static/brand/institution-logo.png    | Bin [31m4444[m -> [32m0[m bytes
 app/static/brand/logo-dark.png           | Bin [31m4066[m -> [32m0[m bytes
 app/static/brand/logo-mark.png           | Bin [31m3232[m -> [32m0[m bytes
 app/static/brand/logo.png                | Bin [31m3102[m -> [32m0[m bytes
 app/static/brand/mascot.png              | Bin [31m3343[m -> [32m0[m bytes
 app/static/brand/og-image.png            | Bin [31m19735[m -> [32m0[m bytes
 app/static/css/main.css                  |  15 [31m---[m
 app/static/js/app.js                     |   6 [31m-[m
 app/templates/admin/_fontes.html         |   5 [31m-[m
 app/templates/admin/_nav.html            |   7 [31m--[m
 app/templates/admin/_paginacao.html      |   7 [31m--[m
 app/templates/admin/auditoria.html       |  18 [31m---[m
 app/templates/admin/identidade.html      |  28 [31m-----[m
 app/templates/admin/painel.html          |  29 [31m-----[m
 app/templates/admin/usinas.html          |  24 [31m----[m
 app/templates/admin/usuarios.html        |  44 [31m-------[m
 app/templates/base.html                  |   9 [32m+[m[31m-[m
 app/templates/campanha.html              |   1 [31m-[m
 app/templates/error.html                 |  10 [31m--[m
 app/templates/login.html                 |   3 [32m+[m[31m-[m
 app/templates/partials/_logo.html        |   2 [32m+[m[31m-[m
 app/templates/partials/_mascote.html     |   2 [32m+[m[31m-[m
 app/templates/usina.html                 |   4 [31m-[m
 app/templates/usinas.html                |  53 [32m+++++[m[31m---[m
 docs/ARQUITETURA.md                      |   4 [31m-[m
 docs/IDENTIDADE_VISUAL.md                |  50 [32m++++[m[31m----[m
 migrations/versions/0001_inicial.py      | 179 [31m---------------------------[m
 scripts/gerar_placeholders.py            |  51 [31m--------[m
 tests/conftest.py                        |  19 [32m+[m[31m--[m
 tests/integration/test_admin_security.py | 201 [31m-------------------------------[m
 tests/integration/test_app.py            |  10 [32m+[m[31m-[m
 56 files changed, 188 insertions(+), 1734 deletions(-)
