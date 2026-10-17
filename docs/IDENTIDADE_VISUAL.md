# Identidade visual: onde colocar logos, imagens, cores e fontes

Todo o projeto usa **placeholders tracejados**. Para aplicar a marca, substitua os arquivos abaixo
(mantendo o nome) ou mude os caminhos em `app/config.py` (classe `Brand`). Nenhum template precisa mudar.

| Slot | Arquivo (em `app/static/brand/`) | Onde aparece | Sugestão de formato |
|---|---|---|---|
| Logo principal | `logo.svg` | Cabeçalho de todas as páginas (`templates/partials/_logo.html`) | SVG ou PNG transparente, exibido com 32 px de altura |
| Logo para fundo escuro | `logo-dark.svg` | Reservado (ex.: rodapé escuro, relatórios) | SVG |
| Símbolo/ícone | `logo-mark.svg` | Reservado (app mobile, PDF) | SVG quadrado |
| Favicon | `favicon.svg` | Aba do navegador (`base.html`) | SVG (ou ICO 32x32) |
| Imagem de destaque | `hero.svg` | Tela de login/cadastro (`login.html`) | 900x1200 px, retrato (JPG/WebP/SVG) |
| Imagem de lista vazia | `empty-state.svg` | Lista de usinas sem itens (`usinas.html`) | 320x200 px |
| Imagem de compartilhamento | `og-image.svg` | Pré-visualização de links (Open Graph) | 1200x630 px (PNG/JPG; algumas redes não aceitam SVG) |
| Mascote do bot de dicas | `mascot.svg` | Botão flutuante no canto inferior esquerdo (`partials/_mascote.html`) | 128x128 px, fundo transparente (SVG/PNG) |
| Logo de instituição parceira | defina `Brand.institution_logo` | Rodapé (só aparece se preenchido) | PNG/SVG, 28 px de altura |

Se trocar a extensão (ex.: `logo.png`), atualize o caminho em `Brand`.

## Cores e tipografia
Edite **somente** `app/static/css/brand.css` (variáveis `--brand-*`, `--state-*`, `--font-*`).
Se usar outra fonte, troque também o `<link>` de fontes em `templates/base.html`.
Os gráficos (Plotly) leem as mesmas variáveis, então acompanham a paleta.

## Nome e slogan
`Brand.name` e `Brand.tagline` em `app/config.py`.

## Mascote e dicas
- Nome: `Brand.mascot_name` em `app/config.py` (hoje "Pepita", provisório).
- Falas: `app/content/tips.py` (id, contexto, nível, título, texto). Adicione ou revise dicas ali; é conteúdo estático.
- Para variar a imagem por situação (feliz, pensativo...), crie mais arquivos em `static/brand/` e troque no `mascote.js`.
- Desligar: `SIMETAL_MASCOT_ENABLED=false`. O VLibras desliga com `SIMETAL_VLIBRAS_ENABLED=false`.
