"""ANM - Dados Abertos. CATÁLOGO de conjuntos de dados (links verificados na página
https://www.gov.br/anm/pt-br/acesso-a-informacao/dados-abertos/bases-de-dados).

Atenção: a ANM publica estes dados como arquivos (CSV/shapefile) via dados.gov.br. Não foi
confirmada uma API de consulta; por isso o SIMETAL só lista e linka as fontes, sem inventar endpoints.
"""

from __future__ import annotations

CATALOG_PAGE = "https://www.gov.br/anm/pt-br/acesso-a-informacao/dados-abertos/bases-de-dados"
_D = "https://dados.gov.br/dados/conjuntos-dados/"

DATASETS: list[dict[str, str]] = [
    {"id": "amb", "nome": "Anuário Mineral Brasileiro (AMB)",
     "descricao": "Produção bruta e beneficiada e destinações, desde 2010, a partir do Relatório Anual de Lavra.",
     "url": _D + "anuario-mineral-brasileiro-amb", "relevancia": "Compare a produção beneficiada da sua usina com o setor."},
    {"id": "cadastro-mineiro", "nome": "Cadastro Mineiro",
     "descricao": "Requerimentos, títulos e atributos dos processos minerários (microdados diários).",
     "url": _D + "sistema-de-cadastro-mineiro", "relevancia": "Situação dos títulos minerários."},
    {"id": "cfem", "nome": "CFEM (Compensação Financeira)",
     "descricao": "Dados de arrecadação da CFEM.", "url": _D + "sistema-arrecadacao", "relevancia": "Royalties por substância e município."},
    {"id": "sicop", "nome": "Controle de Processos (SICOP)",
     "descricao": "Processos minerários e administrativos.", "url": _D + "controle-de-processos-sicop", "relevancia": ""},
    {"id": "tah", "nome": "Taxa Anual por Hectare (TAH)",
     "descricao": "Processo, ano, titular, hectares e valores pagos e cobrados.", "url": _D + "taxa-anual-por-hectare-tah", "relevancia": ""},
    {"id": "sigmine", "nome": "SIGMINE (poligonais)",
     "descricao": "Poligonais dos processos minerários em shapefile e KML, geradas diariamente.",
     "url": _D + "sistema-de-informacoes-geograficas-da-mineracao-sigmine", "relevancia": "Localize a área da mina no mapa."},
    {"id": "sigbm", "nome": "Barragens de Mineração (SIGBM)",
     "descricao": "Características, tipo de rejeito, dano potencial e DCE das barragens.",
     "url": _D + "barragens-de-mineracao", "relevancia": "Contexto de rejeitos e segurança."},
    {"id": "divida-ativa", "nome": "Sistema de Dívida Ativa",
     "descricao": "Créditos inscritos em dívida ativa.", "url": _D + "sistema-de-divida-ativa", "relevancia": ""},
    {"id": "sople", "nome": "Oferta Pública e Leilão de Áreas (SOPLE)",
     "descricao": "Estoque de áreas e resultados das rodadas de disponibilidade.", "url": _D + "oferta-publica-e-leilao-de-areas-sople", "relevancia": ""},
    {"id": "dipem", "nome": "Investimentos em Pesquisa Mineral (DIPEM)",
     "descricao": "Valor investido em pesquisa mineral por município, UF, substância e ano.", "url": _D + "dipem", "relevancia": ""},
    {"id": "repem", "nome": "Requerimento Eletrônico de Pesquisa Mineral (REPEM)",
     "descricao": "Requerimentos de autorização de pesquisa feitos online.", "url": _D + "requerimento-eletronico-de-pesquisa-mineral-repem", "relevancia": ""},
]

VIEWERS = [
    {"nome": "SIGMINE (mapa interativo)", "url": "https://geo.anm.gov.br/portal/apps/webappviewer/index.html?id=6a8f5ccc4b6a4c2bba79759aa952d908"},
    {"nome": "Geoinformação mineral", "url": "https://geo.anm.gov.br/portal/home/"},
]


def catalog() -> dict:
    return {"fonte": "Agência Nacional de Mineração", "pagina": CATALOG_PAGE, "conjuntos": DATASETS, "mapas": VIEWERS}
