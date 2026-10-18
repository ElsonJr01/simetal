"""Banco de dicas do mascote (conteúdo estático, sem IA, revisável por especialistas).

contexto: geral | usinas | fluxograma | medidas | resultado
nivel: basico (ensina o essencial) | curiosidade
"""

from __future__ import annotations

from typing import TypedDict


class Tip(TypedDict):
    id: str
    contexto: str
    nivel: str
    titulo: str
    texto: str


TIPS: list[Tip] = [
    {"id": "g-conservacao", "contexto": "geral", "nivel": "basico", "titulo": "Tudo que entra, sai",
     "texto": "Em cada operação da usina, a massa que entra deve ser igual à massa que sai. Isso se chama conservação de massa e é a base do SIMETAL."},
    {"id": "g-nao-fecha", "contexto": "geral", "nivel": "basico", "titulo": "Por que o balanço não fecha?",
     "texto": "Toda medida tem erro: amostragem, análise de laboratório, vazão que varia no tempo. Por isso os números medidos raramente fecham o balanço sozinhos."},
    {"id": "g-ajuste", "contexto": "geral", "nivel": "basico", "titulo": "O que o SIMETAL faz",
     "texto": "Ele corrige cada medida o mínimo necessário para que todas as equações de balanço fechem. Quanto menos confiável a medida, mais ela é corrigida."},
    {"id": "g-julgamento", "contexto": "geral", "nivel": "curiosidade", "titulo": "Matemática certa, resultado errado",
     "texto": "Um resultado pode estar correto matematicamente e ser impossível na usina. O método ajuda, mas o seu conhecimento do processo continua sendo essencial."},
    {"id": "g-origem", "contexto": "geral", "nivel": "curiosidade", "titulo": "Uma ideia de 1992",
     "texto": "O SIMETAL é uma versão moderna do BALMAS, programa escrito em Turbo Pascal em 1992 num trabalho de formatura da Escola Politécnica da USP."},
    {"id": "u-usina", "contexto": "usinas", "nivel": "basico", "titulo": "O que é uma usina aqui?",
     "texto": "É o circuito de beneficiamento que você quer estudar: um conjunto de operações (ciclone, espiral, moinho...) ligadas por fluxos de material."},
    {"id": "u-exemplo", "contexto": "usinas", "nivel": "basico", "titulo": "Comece pelo exemplo",
     "texto": "Use 'Criar usina de exemplo' para ver o circuito de finos da Carbonífera Cambuí, com os dados da monografia, e conhecer todas as telas."},
    {"id": "f-fluxo", "contexto": "fluxograma", "nivel": "basico", "titulo": "Fluxo e operação",
     "texto": "Fluxo é o material que viaja entre equipamentos (ex.: a alimentação do ciclone). Operação é o equipamento onde ele entra e sai."},
    {"id": "f-matriz", "contexto": "fluxograma", "nivel": "basico", "titulo": "A matriz M",
     "texto": "O fluxograma vira uma tabela de números: +1 se o fluxo entra na operação, −1 se sai e 0 se não se liga. O balanço fecha quando M multiplicada pelas vazões dá zero."},
    {"id": "f-ciclone", "contexto": "fluxograma", "nivel": "curiosidade", "titulo": "Ciclone: o que sai por onde?",
     "texto": "No hidrociclone, o overflow (saída de cima) leva as partículas mais finas e o underflow (saída de baixo) leva as mais grossas."},
    {"id": "f-espiral", "contexto": "fluxograma", "nivel": "curiosidade", "titulo": "Espiral concentradora",
     "texto": "A espiral separa partículas principalmente pela densidade: o material mais denso (concentrado) fica de um lado e o mais leve (rejeito) de outro. Os midlings são o meio-termo."},
    {"id": "f-clima", "contexto": "fluxograma", "nivel": "curiosidade", "titulo": "Por que mostrar o clima?",
     "texto": "Chuva forte pode mudar a umidade do minério e as vazões do circuito. Saber se choveu no período ajuda a interpretar medidas que fogem do esperado."},
    {"id": "f-ibge", "contexto": "fluxograma", "nivel": "basico", "titulo": "De onde vêm estados e municípios",
     "texto": "As listas vêm da API de Localidades do IBGE, que é pública e gratuita. Se ela estiver fora do ar, o resto do SIMETAL continua funcionando normalmente."},
    {"id": "f-anm", "contexto": "fluxograma", "nivel": "curiosidade", "titulo": "Dados abertos da ANM",
     "texto": "A Agência Nacional de Mineração publica dados abertos sobre produção beneficiada, processos, barragens e CFEM. Os links estão no fim da página da usina."},
    {"id": "m-unidades", "contexto": "medidas", "nivel": "basico", "titulo": "Mesma unidade em tudo",
     "texto": "Use a mesma unidade em todos os fluxos (por exemplo, t/h para vazões e % para teores). O SIMETAL só mostra o rótulo que você define; ele não converte unidades."},
    {"id": "m-planilha", "contexto": "medidas", "nivel": "basico", "titulo": "Dados numa planilha?",
     "texto": "Copie as colunas de valor e desvio no Excel e use 'Colar da planilha'. Vírgula e ponto decimal funcionam."},
    {"id": "m-redundancia", "contexto": "medidas", "nivel": "curiosidade", "titulo": "Medir mais para corrigir melhor",
     "texto": "Medir mais fluxos do que o estritamente necessário é o que dá ao ajuste poder de correção. Veja a análise de redundância acima do botão de ajuste."},
    {"id": "m-amostragem", "contexto": "medidas", "nivel": "curiosidade", "titulo": "Amostra representativa",
     "texto": "Uma boa amostra corta a corrente inteira durante um tempo, com vários incrementos. Pegar só um punhado costuma enviesar o resultado, e nenhum ajuste corrige viés."},
    {"id": "r-indicadores", "contexto": "resultado", "nivel": "basico", "titulo": "Recuperação metalúrgica",
     "texto": "Depois de fechar massa e um teor, calcule a recuperação: que percentual do componente da alimentação foi parar no concentrado. Os indicadores aparecem abaixo da tabela."},
    {"id": "r-csv", "contexto": "resultado", "nivel": "basico", "titulo": "Levar para o Excel",
     "texto": "O botão 'Baixar CSV' gera um arquivo com ponto e vírgula e vírgula decimal, que o Excel em português abre direto."},
    {"id": "g-ajuda", "contexto": "geral", "nivel": "basico", "titulo": "Ficou com dúvida?",
     "texto": "O menu 'Como usar' tem o passo a passo, o glossário, a explicação do método com um exemplo numérico e as perguntas frequentes."},
    {"id": "m-sigma", "contexto": "medidas", "nivel": "basico", "titulo": "Desvio-padrão é confiança",
     "texto": "O desvio-padrão (σ) diz o quanto você confia na medida. Medida precisa tem σ pequeno e quase não muda; medida duvidosa tem σ grande e absorve a correção."},
    {"id": "m-nao-amostrado", "contexto": "medidas", "nivel": "basico", "titulo": "Fluxo que não deu para medir",
     "texto": "Marque 'não amostrado' e dê uma estimativa. O desvio-padrão passa a ser igual ao valor, ou seja, confiança mínima, e o ajuste calcula o resto a partir dos outros fluxos."},
    {"id": "m-componente", "contexto": "medidas", "nivel": "basico", "titulo": "Massa primeiro, teor depois",
     "texto": "Feche primeiro o balanço de massas (vazões). Depois, com as vazões ajustadas, feche o balanço metalúrgico de cada componente, como cinzas ou um teor de interesse."},
    {"id": "m-amostras", "contexto": "medidas", "nivel": "curiosidade", "titulo": "Mais amostras, menos incerteza",
     "texto": "Com várias amostras do mesmo ponto você obtém média e desvio-padrão reais. Na usina as condições mudam com o tempo, então a incerteza de uma medida nunca é zero."},
    {"id": "r-z", "contexto": "resultado", "nivel": "basico", "titulo": "Como ler o z",
     "texto": "O z (resíduo normalizado) mede quanto uma medida foi corrigida em relação à sua incerteza. Acima de 1,96 em módulo, vale desconfiar daquela medida."},
    {"id": "r-chi2", "contexto": "resultado", "nivel": "basico", "titulo": "Teste global (χ²)",
     "texto": "Se o χ² passa do limite, os dados são incompatíveis com os desvios informados: ou há erro grosseiro em alguma medida, ou os σ estão pequenos demais."},
    {"id": "r-iterar", "contexto": "resultado", "nivel": "basico", "titulo": "Iterar é decidir",
     "texto": "A cada rodada você escolhe, fluxo a fluxo: manter a entrada, usar o valor ajustado ou informar um valor novo. Repita até os valores quase pararem de mudar."},
    {"id": "r-suspeita", "contexto": "resultado", "nivel": "basico", "titulo": "Medida muito corrigida",
     "texto": "Se um fluxo foi corrigido em mais de 30%, revise a amostragem ou a análise dele antes de aceitar o resultado."},
    {"id": "r-negativo", "contexto": "resultado", "nivel": "basico", "titulo": "Vazão negativa?",
     "texto": "Não existe vazão negativa. Se aparecer, algum dado de entrada está inconsistente: revise os valores e os desvios."},
    {"id": "r-lagrange", "contexto": "resultado", "nivel": "curiosidade", "titulo": "Lagrange e Gauss",
     "texto": "O método usa multiplicadores de Lagrange para impor as restrições e a eliminação de Gauss para resolver o sistema de equações. Os multiplicadores são só um artifício matemático, sem significado de processo."},
]


def get_tips(contexts: list[str] | None = None, nivel: str | None = None) -> list[Tip]:
    """Dicas filtradas por contexto(s) e nível; ordem do banco (a ordem de leitura sugerida)."""
    wanted = {c.strip() for c in contexts or [] if c.strip()}
    return [t for t in TIPS if (not wanted or t["contexto"] in wanted) and (nivel is None or t["nivel"] == nivel)]
