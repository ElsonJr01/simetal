# Identidade visual: onde colocar logos e imagens

Todos os arquivos ficam em **`app/static/brand/`**, com **nomes e formato fixos (PNG)**.
Para aplicar a marca, **substitua o arquivo com o mesmo nome** e faça um novo deploy. Nenhum código muda.

| Arquivo | Tamanho recomendado | Onde aparece |
|---|---|---|
| `logo.png` | 480×96 px, fundo transparente | Cabeçalho de todas as páginas (exibido com 32 px de altura; o cabeçalho é escuro) |
| `logo-dark.png` | 480×96 px | Reservado: fundos escuros, rodapé, relatórios |
| `logo-mark.png` | 256×256 px, transparente | Reservado: símbolo isolado (PDF, app) |
| `favicon.png` | 64×64 px | Aba do navegador |
| `hero.png` | 900×1200 px (retrato) | Imagem de destaque das telas de login e cadastro |
| `empty-state.png` | 640×400 px | Lista vazia (ex.: nenhuma usina), exibida com 240 px de largura |
| `og-image.png` | 1200×630 px | Pré-visualização ao compartilhar links |
| `mascot.png` | 256×256 px, transparente | Mascote do bot de dicas (exibido com 64 px) |
| `institution-logo.png` | 400×112 px | Rodapé; só aparece se `Brand.institution_name` estiver preenchido |

Os caminhos estão definidos **uma única vez** em `app/brand.py` (lista `SLOTS`) e usados por `app/config.py`.
Os arquivos atuais são **placeholders** (moldura tracejada com o nome do arquivo).

## Conferir o que falta
Entre como administrador em **/admin/identidade**: a tabela mostra a prévia de cada arquivo, o tamanho real,
e se ele ainda é provisório, ausente ou inválido.

Para recriar placeholders que faltarem: `python scripts/gerar_placeholders.py` (requer `pip install pillow`; use `--force` para sobrescrever todos).

## Cores, fontes, nome
- Cores e fontes: **`app/static/css/brand.css`** (variáveis `--brand-*`, `--state-*`, `--font-*`). Se usar outra fonte, troque também o `<link>` de fontes em `templates/base.html`.
- Nome, slogan, nome do mascote e instituição: `app/config.py` (classe `Brand`) ou, para o nome da instituição, defina o valor padrão ali.
- Falas do mascote: `app/content/tips.py`.
