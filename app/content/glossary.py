"""Glossário da área (processo mineral, estatística de medidas e método do SIMETAL).

Conteúdo estático e revisável: um termo = um dicionário. `ver` lista termos relacionados.
"""

from __future__ import annotations

import re
import unicodedata
from typing import TypedDict


class Term(TypedDict):
    termo: str
    categoria: str
    definicao: str
    ver: list[str]


CATEGORIES = ("Processo mineral", "Medidas e estatística", "Método do SIMETAL", "Indicadores metalúrgicos", "Dados públicos e acessibilidade")


def slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def _t(termo: str, categoria: str, definicao: str, ver: list[str] | None = None) -> Term:
    return {"termo": termo, "categoria": categoria, "definicao": definicao, "ver": ver or []}


P, M, S, I, D = CATEGORIES
TERMS: list[Term] = [
    _t("Beneficiamento", P, "Conjunto de operações que separam o minério de interesse do material sem valor, sem alterar a natureza química dos minerais (britagem, moagem, classificação, concentração, desaguamento...). Também chamado de tratamento de minérios.", ["Usina", "Circuito"]),
    _t("Usina", P, "A instalação de beneficiamento. No SIMETAL, 'usina' é o circuito que você quer estudar, descrito por fluxos e operações.", ["Circuito", "Fluxograma"]),
    _t("Circuito", P, "Conjunto de operações ligadas por fluxos. Pode ser a usina inteira ou só uma parte (ex.: ciclone + espiral).", ["Fluxograma"]),
    _t("Fluxograma", P, "Desenho do circuito: quais equipamentos existem e por quais fluxos o material passa entre eles. No SIMETAL ele vira a matriz M.", ["Matriz M", "Fluxo (corrente)", "Operação (unitária)"]),
    _t("Fluxo (corrente)", P, "Material que se move entre equipamentos: a alimentação de um ciclone, o rejeito de uma espiral etc. Cada fluxo tem uma vazão e, se medido, teores.", ["Operação (unitária)", "Vazão"]),
    _t("Operação (unitária)", P, "Equipamento ou etapa onde fluxos entram e saem: ciclone, espiral, moinho, peneira, flotação... Em toda operação, o que entra deve ser igual ao que sai.", ["Fluxo (corrente)", "Balanço de massas"]),
    _t("Alimentação", P, "Fluxo que entra numa operação ou no circuito. Por convenção do SIMETAL, o fluxo 1 deve ser a alimentação do circuito (as colunas '% da alimentação' e '% de distribuição' usam o fluxo 1 como base).", ["Produto"]),
    _t("Produto", P, "Fluxo que sai de uma operação (concentrado, rejeito, mistos, overflow, underflow...).", ["Alimentação"]),
    _t("Hidrociclone", P, "Equipamento que separa partículas por tamanho usando força centrífuga: as mais finas saem pelo overflow (saída superior) e as mais grossas pelo underflow (saída inferior).", ["Overflow e underflow"]),
    _t("Overflow e underflow", P, "Saídas do hidrociclone. Overflow: fração fina, sai por cima. Underflow: fração grossa, sai por baixo (o apex é o bocal de descarga do underflow).", ["Hidrociclone"]),
    _t("Espiral concentradora", P, "Equipamento gravimétrico que separa partículas principalmente pela diferença de densidade, em uma calha helicoidal. Gera concentrado, mistos e rejeito.", ["Concentrado, rejeito e mistos"]),
    _t("Concentrado, rejeito e mistos", P, "Concentrado: produto enriquecido no componente de interesse. Rejeito: material descartado. Mistos (midlings): produto intermediário, normalmente reprocessado.", ["Espiral concentradora"]),
    _t("Carga circulante", P, "Em circuito fechado, a parcela de material que retorna a um equipamento. Costuma ser expressa como razão entre a vazão que retorna e a alimentação nova do circuito.", ["Circuito"]),
    _t("Polpa e % de sólidos", P, "Polpa é a mistura de sólidos e água. % de sólidos = massa de sólidos ÷ massa de polpa × 100. Para o balanço de massas use a vazão de sólidos secos, para que ela seja coerente com os teores.", ["Vazão"]),
    _t("Granulometria", P, "Distribuição dos tamanhos de partícula. Cada faixa de tamanho pode ser tratada como um 'componente' no balanço (a massa da faixa é vazão × % da faixa).", ["Componente"]),
    _t("Amostragem", M, "Retirada de uma parte do material para medir suas propriedades. É representativa quando todas as partículas têm a mesma chance de entrar na amostra; a teoria de Pierre Gy é a referência clássica do assunto.", ["Amostra"]),
    _t("Amostra", M, "A porção retirada numa amostragem. Várias amostras do mesmo ponto permitem calcular média e desvio-padrão.", ["Amostragem", "Média e desvio-padrão"]),
    _t("Vazão", M, "Quantidade de material por unidade de tempo (ex.: t/h). No SIMETAL, informe vazões na mesma unidade em todos os fluxos.", ["Fluxo (corrente)"]),
    _t("Teor", M, "Proporção de um componente em um fluxo, em % (ou g/t, ppm...). Exemplos: teor de ferro, teor de cinzas. A massa do componente que passa por unidade de tempo é vazão × teor.", ["Componente"]),
    _t("Componente", M, "Qualquer grandeza cuja 'massa' seja vazão × proporção: um teor, uma faixa granulométrica, a % de sólidos. No SIMETAL, 'massa' fecha as vazões e os demais componentes fecham os teores.", ["Teor", "Balanço metalúrgico"]),
    _t("Média e desvio-padrão", M, "Média: valor central das amostras. Desvio-padrão amostral (s): dispersão entre elas, calculado com n−1 no denominador. O desvio-padrão da média é s/√n e é menor que s.", ["Amostra", "Desvio-padrão (σ)"]),
    _t("Desvio-padrão (σ)", M, "Quanto você confia numa medida: σ pequeno = medida precisa; σ grande = medida duvidosa. O SIMETAL usa σ para decidir o quanto cada medida pode ser corrigida.", ["Variância", "Peso"]),
    _t("Variância", M, "É o desvio-padrão ao quadrado (σ²). O peso de cada medida no ajuste é 1/σ².", ["Peso"]),
    _t("Incerteza relativa", M, "σ expresso como % do valor (σ ÷ valor × 100). No SIMETAL aparece como 'grau de incerteza' (σ = incerteza × valor) ou 'grau de certeza' (σ = (1 − certeza) × valor).", ["Desvio-padrão (σ)"]),
    _t("Erro aleatório e erro grosseiro", M, "Erro aleatório: variação normal de qualquer medida. Erro grosseiro: falha pontual (amostra contaminada, equipamento descalibrado, anotação errada) que deixa uma medida muito fora do esperado. O teste do resíduo normalizado ajuda a suspeitar de erros grosseiros.", ["Resíduo normalizado (z)"]),
    _t("Valor experimental, ajustado e real", M, "Experimental: o que foi medido (tem erro e não fecha o balanço). Ajustado: o valor corrigido pelo SIMETAL, que fecha o balanço. Real: o valor verdadeiro, que nunca se conhece (é só o alvo do ajuste).", ["Balanço de massas"]),
    _t("Balanço de massas", S, "Verificação de que, em cada operação, a soma das vazões que entram é igual à soma das que saem (conservação de massa).", ["Fechar o balanço", "Matriz M"]),
    _t("Balanço metalúrgico", S, "Balanço de um componente (teor, faixa granulométrica...): vazão × teor que entra deve ser igual ao que sai. No SIMETAL usa as vazões já ajustadas no balanço de massas.", ["Balanço de massas", "Componente"]),
    _t("Fechar o balanço", S, "Corrigir as medidas o mínimo necessário para que todas as equações de balanço sejam satisfeitas exatamente.", ["Resíduo de fechamento"]),
    _t("Resíduo de fechamento", S, "Quanto falta para o balanço fechar com os dados medidos (entrada − saída). Num dado perfeito seria zero; na prática nunca é.", ["Fechar o balanço"]),
    _t("Mínimos quadrados ponderados", S, "Técnica que escolhe, entre todos os conjuntos de valores que fecham o balanço, aquele que menos se afasta das medidas, ponderando o afastamento de cada uma por 1/σ².", ["Peso", "Restrição"]),
    _t("Peso", S, "Importância de uma medida no ajuste: P = 1/σ². Medida mais confiável (σ pequeno) tem peso maior e é menos corrigida.", ["Variância"]),
    _t("Restrição", S, "Equação que o resultado precisa obedecer. Aqui, cada operação gera uma: entradas − saídas = 0.", ["Matriz M"]),
    _t("Matriz M", S, "Tabela que descreve o fluxograma: uma linha por operação, uma coluna por fluxo; +1 se o fluxo entra, −1 se sai, 0 se não se liga. O balanço fecha quando M × vazões = 0.", ["Restrição", "Fluxograma"]),
    _t("Multiplicador de Lagrange", S, "Artifício matemático para impor as restrições na minimização. Não tem significado de processo; só ajuda a resolver o sistema.", ["Eliminação de Gauss"]),
    _t("Eliminação de Gauss", S, "Método de resolução de sistemas lineares: transforma o sistema em um triangular equivalente (com troca de linhas para escolher o melhor pivô) e resolve de trás para frente.", ["Multiplicador de Lagrange"]),
    _t("Fluxo não amostrado", S, "Fluxo que não foi medido. Informe uma estimativa e marque 'não amostrado': o desvio-padrão passa a ser igual ao valor (confiança mínima) e o ajuste o calcula a partir dos outros.", ["Redundância", "Calculável (observável)"]),
    _t("Redundância", S, "Número de equações que 'sobram' depois de calcular os fluxos não medidos. Só com redundância maior que zero o ajuste consegue corrigir medidas e o teste χ² faz sentido.", ["Calculável (observável)"]),
    _t("Calculável (observável)", S, "Um fluxo não medido é calculável quando as equações de balanço o determinam de forma única. Se há mais incógnitas do que equações, o balanço fica indeterminado e é preciso medir mais fluxos.", ["Redundância", "Fluxo não amostrado"]),
    _t("Iteração e convergência", S, "Iterar é rodar o ajuste de novo depois de o engenheiro decidir, fluxo a fluxo, manter a entrada, usar o valor ajustado ou informar um novo. Converge quando os valores ajustados quase não mudam entre rodadas.", ["Valor experimental, ajustado e real"]),
    _t("Teste global (χ²)", S, "Compara o resíduo total de fechamento com o que o erro aleatório esperado explicaria. Se passa do limite (95%), os dados são incompatíveis com os desvios informados: há erro grosseiro ou σ pequeno demais. Com fluxos não amostrados tratados por σ grande, o teste é aproximado.", ["Graus de liberdade"]),
    _t("Graus de liberdade", S, "No SIMETAL, número de equações de balanço (operações). É o parâmetro de comparação do teste χ².", ["Teste global (χ²)"]),
    _t("Resíduo normalizado (z)", S, "Quanto uma medida foi corrigida, em unidades da sua incerteza. |z| acima de 1,96 (95%) sugere que aquela medida merece revisão.", ["Erro aleatório e erro grosseiro"]),
    _t("Distribuição (%)", I, "Percentual do componente da alimentação que vai para cada fluxo: D = (vazão × teor do fluxo) ÷ (vazão × teor da alimentação) × 100. As distribuições das saídas de uma operação somam 100%.", ["Recuperação metalúrgica"]),
    _t("Recuperação metalúrgica", I, "Percentual do componente da alimentação que foi parar no concentrado: R = (C·c) ÷ (F·f) × 100, com F, f = vazão e teor da alimentação e C, c = vazão e teor do concentrado.", ["Distribuição (%)", "Rendimento mássico"]),
    _t("Rendimento mássico", I, "Percentual da massa da alimentação que vira concentrado: Y = C ÷ F × 100.", ["Recuperação metalúrgica"]),
    _t("Razão de enriquecimento", I, "Quantas vezes o concentrado é mais rico que a alimentação: E = c ÷ f. (Para um rejeito ou um componente indesejado, valores abaixo de 1 indicam que o produto ficou mais pobre nele.)", ["Razão de concentração"]),
    _t("Razão de concentração", I, "Quantas toneladas de alimentação são necessárias para cada tonelada de concentrado: K = F ÷ C.", ["Razão de enriquecimento"]),
    _t("IBGE e código do município", D, "O IBGE publica a lista oficial de estados e municípios; cada município tem um código de 7 dígitos (ex.: Marabá/PA = 1504208). O SIMETAL usa a API de Localidades para escolher o local da usina.", ["Open-Meteo"]),
    _t("ANM", D, "Agência Nacional de Mineração, reguladora do setor no Brasil. Publica dados abertos (produção, processos, barragens, CFEM...) como arquivos no portal dados.gov.br.", ["CFEM"]),
    _t("CFEM", D, "Compensação Financeira pela Exploração de Recursos Minerais, a contrapartida (royalties) paga pela atividade mineradora; a ANM publica dados de sua arrecadação.", ["ANM"]),
    _t("Open-Meteo", D, "Serviço aberto de dados meteorológicos, usado para mostrar temperatura e chuva no local da usina. Gratuito para uso não comercial, com atribuição.", ["IBGE e código do município"]),
    _t("VLibras", D, "Ferramenta do governo federal que traduz automaticamente o conteúdo da página para a Língua Brasileira de Sinais (Libras). Aparece como um botão de acessibilidade nas páginas.", []),
]

for _term in TERMS:
    _term["ver"] = [v for v in _term["ver"] if v]


def by_category() -> list[tuple[str, list[Term]]]:
    return [(c, sorted((t for t in TERMS if t["categoria"] == c), key=lambda t: slug(t["termo"]))) for c in CATEGORIES]
