# Como contribuir

1. Crie um ambiente virtual e instale `requirements-dev.txt` (veja o README).
2. Crie uma branch por mudança: `git checkout -b minha-mudanca`.
3. Rode `python -m pytest` antes de enviar; adicione testes para o que mudou.
4. Textos para o usuário em português do Brasil, claros e sem jargão desnecessário (o glossário existe para isso).
5. Mudou o banco? Inclua a migração Alembic.
6. Descreva a mudança no `CHANGELOG.md`.

Guia completo do código: `docs/GUIA_DO_DESENVOLVEDOR.md`.
