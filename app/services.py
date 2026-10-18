"""Camada de serviços: orquestra núcleo de cálculo + banco (casos de uso UC02-UC12)."""

from __future__ import annotations

import csv
import io
import re

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core import (
    Alert,
    Flowsheet,
    FlowsheetError,
    InvalidInputError,
    Operation,
    Severity,
    SingularSystemError,
    analyze,
    diagnose,
    distribution,
    has_converged,
    indicators,
    reconcile,
    reconcile_component,
)
from app.core.iteration import FlowAction, IterationAction, apply_actions
from app.integrations import ibge, openmeteo
from app.integrations.http import IntegrationError
from app.models import (
    Ajuste,
    Campanha,
    Conexao,
    Fluxo,
    Medida,
    Operacao,
    ResultadoFluxo,
    Usina,
)

MASSA = "massa"


class ServiceError(Exception):
    """Erro de regra de negócio, com mensagem pronta para o usuário."""


# ---------------------------------------------------------------- fluxograma
def parse_flowsheet_text(flows_text: str, ops_text: str) -> tuple[list[str], list[tuple[str, list[int], list[int]]]]:
    """Fluxos: um nome por linha. Operações: 'Nome | entradas | saídas' (números dos fluxos)."""
    flows = [ln.strip() for ln in flows_text.splitlines() if ln.strip()]
    ops: list[tuple[str, list[int], list[int]]] = []
    for ln in (x for x in ops_text.splitlines() if x.strip()):
        parts = [p.strip() for p in ln.split("|")]
        if len(parts) != 3:
            raise ServiceError(f"Operação mal formatada: '{ln}'. Use: Nome | entradas | saídas.")
        try:
            ins = [int(v) for v in parts[1].replace(";", ",").split(",") if v.strip()]
            outs = [int(v) for v in parts[2].replace(";", ",").split(",") if v.strip()]
        except ValueError as exc:
            raise ServiceError(f"Números de fluxo inválidos em '{ln}'.") from exc
        ops.append((parts[0], ins, outs))
    return flows, ops


def save_flowsheet(db: Session, usina: Usina, flows: list[str], ops: list[tuple[str, list[int], list[int]]]) -> list[Alert]:
    """Atualiza o fluxograma. Fluxos existentes são mantidos pelo número (e só renomeados), preservando
    as medidas; fluxos removidos perdem as suas medidas. As operações são recriadas."""
    cfg = get_settings()
    if len(flows) > cfg.max_flows or len(ops) > cfg.max_operations:
        raise ServiceError(f"Limite excedido: no máximo {cfg.max_flows} fluxos e {cfg.max_operations} operações.")
    if any(len(n) > 120 for n in flows) or any(len(n) > 120 for n, _, _ in ops):
        raise ServiceError("Nomes de fluxos e operações aceitam até 120 caracteres.")
    sheet = Flowsheet(
        flows=tuple(flows),
        operations=tuple(Operation(n, tuple(i - 1 for i in ins), tuple(o - 1 for o in outs)) for n, ins, outs in ops),
    )
    try:
        alerts = sheet.validate()
    except FlowsheetError as exc:
        raise ServiceError(str(exc)) from exc
    if any(a.severity is Severity.ERROR for a in alerts):
        return alerts  # não grava; a tela mostra os erros

    usina.operacoes.clear()
    db.flush()
    by_num = {f.numero: f for f in usina.fluxos}
    for i, name in enumerate(flows, start=1):
        if i in by_num:
            by_num[i].nome = name
        else:
            usina.fluxos.append(Fluxo(numero=i, nome=name))
    for num, fluxo in by_num.items():
        if num > len(flows):
            usina.fluxos.remove(fluxo)
    db.flush()
    flow_by_num = {f.numero: f for f in usina.fluxos}
    for name, ins, outs in ops:
        op = Operacao(nome=name)
        op.conexoes = [Conexao(fluxo_id=flow_by_num[i].id, sinal=1) for i in ins] + [
            Conexao(fluxo_id=flow_by_num[o].id, sinal=-1) for o in outs
        ]
        usina.operacoes.append(op)
    db.commit()
    return alerts


def build_flowsheet(usina: Usina) -> Flowsheet:
    index = {f.id: f.numero - 1 for f in usina.fluxos}
    ops = tuple(
        Operation(
            op.nome,
            tuple(index[c.fluxo_id] for c in op.conexoes if c.sinal == 1),
            tuple(index[c.fluxo_id] for c in op.conexoes if c.sinal == -1),
        )
        for op in usina.operacoes
    )
    return Flowsheet(tuple(f.nome for f in usina.fluxos), ops)


def flowsheet_text(usina: Usina) -> tuple[str, str]:
    sheet = build_flowsheet(usina)
    flows = "\n".join(sheet.flows)
    ops = "\n".join(
        f"{op.name} | {', '.join(str(i + 1) for i in op.inputs)} | {', '.join(str(o + 1) for o in op.outputs)}"
        for op in sheet.operations
    )
    return flows, ops


# ------------------------------------------------------------------ medidas
def save_measures(db: Session, campanha: Campanha, componente: str, rows: list[dict]) -> None:
    """rows: [{'fluxo_id', 'valor', 'desvio', 'nao_amostrado'}]. Sobrescreve o componente."""
    for row in rows:
        if row["valor"] is None:
            continue
        sigma = row["valor"] if row.get("nao_amostrado") else row["desvio"]
        if sigma is None or sigma <= 0:
            raise ServiceError("Desvio-padrão deve ser maior que zero (use 'não amostrado' para σ = valor).")
        existing = db.scalar(
            select(Medida).where(
                Medida.campanha_id == campanha.id, Medida.fluxo_id == row["fluxo_id"], Medida.componente == componente
            )
        )
        if existing:
            existing.valor, existing.desvio, existing.nao_amostrado = row["valor"], sigma, bool(row.get("nao_amostrado"))
        else:
            db.add(
                Medida(
                    campanha_id=campanha.id,
                    fluxo_id=row["fluxo_id"],
                    componente=componente,
                    valor=row["valor"],
                    desvio=sigma,
                    nao_amostrado=bool(row.get("nao_amostrado")),
                )
            )
    db.commit()


def measures_for(campanha: Campanha, componente: str) -> dict[int, Medida]:
    """fluxo_id -> Medida do componente."""
    return {m.fluxo_id: m for m in campanha.medidas if m.componente == componente}


def last_adjustment(campanha: Campanha, componente: str) -> Ajuste | None:
    items = [a for a in campanha.ajustes if a.componente == componente]
    return items[-1] if items else None


# ------------------------------------------------------------------- ajuste
def run_adjustment(
    db: Session,
    campanha: Campanha,
    componente: str = MASSA,
    actions: dict[int, FlowAction] | None = None,
) -> tuple[Ajuste, list[Alert]]:
    """Executa uma iteração. Sem `actions`, parte das medidas (iteração 1).
    Com `actions` (por número de fluxo), parte da iteração anterior (UC10)."""
    settings = get_settings()
    sheet = build_flowsheet(campanha.usina)
    problems = [a for a in sheet.validate() if a.severity is Severity.ERROR]
    if problems:
        raise ServiceError(problems[0].message)
    m_mat = sheet.matrix()
    flows = campanha.usina.fluxos
    prev = last_adjustment(campanha, componente)

    if actions is not None and prev is not None:
        if prev.iteracao >= settings.max_iterations:
            raise ServiceError(
                f"Limite de {settings.max_iterations} iterações atingido. Revise melhor os dados de entrada."
            )
        by_num = {r.fluxo_numero: r for r in prev.resultados}
        acts = [actions.get(f.numero, FlowAction()) for f in flows]
        x, sigma = apply_actions(
            np.array([by_num[f.numero].entrada for f in flows]),
            np.array([by_num[f.numero].desvio for f in flows]),
            np.array([by_num[f.numero].ajustado for f in flows]),
            acts,
        )
        used_actions = [a.action.value for a in acts]
        iteracao = prev.iteracao + 1
    else:
        measures = measures_for(campanha, componente)
        missing = [f.nome for f in flows if f.id not in measures]
        if missing:
            raise ServiceError(f"Faltam medidas de '{componente}' para: {', '.join(missing)}.")
        x = np.array([measures[f.id].valor for f in flows])
        sigma = np.array([measures[f.id].desvio for f in flows])
        used_actions = [IterationAction.KEEP.value] * len(flows)
        iteracao = (prev.iteracao + 1) if prev else 1

    try:
        if componente == MASSA:
            res = reconcile(m_mat, x, sigma)
        else:
            mass = last_adjustment(campanha, MASSA)
            if mass is None:
                raise ServiceError("Feche o balanço de massas antes do balanço metalúrgico.")
            w_by_num = {r.fluxo_numero: r.ajustado for r in mass.resultados}
            res = reconcile_component(m_mat, np.array([w_by_num[f.numero] for f in flows]), x, sigma)
    except (InvalidInputError, SingularSystemError) as exc:
        raise ServiceError(str(exc)) from exc

    ajuste = Ajuste(
        campanha_id=campanha.id,
        componente=componente,
        iteracao=iteracao,
        chi2=res.chi2,
        graus=res.dof,
        convergiu=bool(prev and has_converged(np.array([r.ajustado for r in prev.resultados]), res.adjusted, settings.convergence_tol)),
    )
    if componente == MASSA:
        feed = res.adjusted[0] if res.adjusted[0] else None
        percents = [float(100 * v / feed) if feed else None for v in res.adjusted]
    else:  # distribuição do componente (convenção: o fluxo 1 é a alimentação)
        wv = [w_by_num[f.numero] for f in flows]
        percents = [None if p is None else float(p) for p in distribution(wv, list(res.adjusted))]
    for j, f in enumerate(flows):
        ajuste.resultados.append(
            ResultadoFluxo(
                fluxo_numero=f.numero,
                fluxo_nome=f.nome,
                entrada=float(x[j]),
                desvio=float(sigma[j]),
                ajustado=float(res.adjusted[j]),
                residuo_norm=float(res.normalized_residuals[j]),
                percentual=percents[j],
                acao=used_actions[j],
            )
        )
    campanha.ajustes.append(ajuste)
    db.commit()
    alerts = diagnose(x, res.adjusted, res.normalized_residuals, res.chi2, res.dof, is_grade=componente != MASSA)
    return ajuste, alerts


# ----------------------------------------------------------------- localização
def set_location(
    db: Session, usina: Usina, uf: str, municipio_ibge: int, latitude: float | None = None, longitude: float | None = None
) -> str | None:
    """Valida UF/município no IBGE e define as coordenadas (informadas ou via geocodificação).
    Retorna um aviso (str) se algo não pôde ser resolvido; levanta ServiceError se o município não existe."""
    uf = uf.upper()
    try:
        cities = {c["id"]: c["nome"] for c in ibge.municipios(uf)}
        state_name = next((e["nome"] for e in ibge.estados() if e["sigla"] == uf), None)
    except IntegrationError as exc:
        raise ServiceError(f"{exc}. Tente novamente em instantes.") from exc
    if municipio_ibge not in cities:
        raise ServiceError("Esse município não pertence ao estado informado.")
    usina.uf, usina.municipio_ibge, usina.municipio_nome = uf, municipio_ibge, cities[municipio_ibge]
    warning = None
    if latitude is not None and longitude is not None:
        usina.latitude, usina.longitude = latitude, longitude
    else:
        try:
            coords = openmeteo.geocode(usina.municipio_nome, state_name)
        except IntegrationError:
            coords = None
        if coords:
            usina.latitude, usina.longitude = coords
        else:
            usina.latitude = usina.longitude = None
            warning = "Não foi possível obter as coordenadas automaticamente; informe latitude e longitude para ver o clima."
    db.commit()
    return warning


# ----------------------------------------------------------- unidades e cópia/cola
def set_units(db: Session, campanha: Campanha, unidade_vazao: str, unidade_teor: str) -> None:
    for label, value in (("vazão", unidade_vazao), ("teor", unidade_teor)):
        if not value.strip() or len(value.strip()) > 20 or re.search(r"[<>&\"']", value):
            raise ServiceError(f"Unidade de {label} inválida (até 20 caracteres, sem < > & aspas).")
    campanha.unidade_vazao, campanha.unidade_teor = unidade_vazao.strip(), unidade_teor.strip()
    db.commit()


def unit_for(campanha: Campanha, componente: str) -> str:
    return campanha.unidade_vazao if componente == MASSA else campanha.unidade_teor


def parse_decimal(text: str) -> float:
    """Aceita vírgula ou ponto decimal. Com os dois, o ponto é separador de milhar ('1.234,5')."""
    v = text.strip().replace(" ", "")
    v = v.replace(".", "").replace(",", ".") if "," in v and "." in v else v.replace(",", ".")
    try:
        return float(v)
    except ValueError as exc:
        raise ServiceError(f"Valor numérico inválido: '{text}'.") from exc


def parse_pasted(text: str, n_flows: int) -> list[tuple[int, float, float]]:
    """Interpreta dados colados da planilha: 'valor  desvio' por linha (na ordem dos fluxos)
    ou 'fluxo  valor  desvio'. Separadores: tab, ponto e vírgula ou espaços."""
    lines = [ln for ln in (x.strip() for x in text.splitlines()) if ln]
    if not lines:
        raise ServiceError("Cole ao menos uma linha: valor e desvio-padrão de cada fluxo.")
    rows: list[tuple[int, float, float]] = []
    for i, ln in enumerate(lines, start=1):
        parts = [p for p in re.split(r"[\t;]+|\s+", ln) if p]
        if len(parts) == 3:
            try:
                flow = int(parts[0])
            except ValueError as exc:
                raise ServiceError(f"Linha {i}: o primeiro campo deveria ser o número do fluxo.") from exc
            rows.append((flow, parse_decimal(parts[1]), parse_decimal(parts[2])))
        elif len(parts) == 2:
            rows.append((i, parse_decimal(parts[0]), parse_decimal(parts[1])))
        else:
            raise ServiceError(f"Linha {i}: use 'valor desvio' ou 'fluxo valor desvio'.")
    for flow, _, _ in rows:
        if not 1 <= flow <= n_flows:
            raise ServiceError(f"O fluxo {flow} não existe nesta usina (1 a {n_flows}).")
    return rows


def apply_pasted(db: Session, campanha: Campanha, componente: str, text: str) -> int:
    by_num = {f.numero: f.id for f in campanha.usina.fluxos}
    rows = parse_pasted(text, len(by_num))
    save_measures(
        db, campanha, componente,
        [{"fluxo_id": by_num[n], "valor": v, "desvio": d, "nao_amostrado": False} for n, v, d in rows],
    )
    return len(rows)


# ----------------------------------------------------- indicadores e redundância
def indicators_for(campanha: Campanha, componente: str, feed_num: int, prod_num: int) -> dict:
    """Recuperação, razões e rendimento a partir dos últimos ajustes de massa e do componente."""
    mass = last_adjustment(campanha, MASSA)
    comp = last_adjustment(campanha, componente)
    if componente == MASSA or mass is None or comp is None:
        raise ServiceError("Feche o balanço de massas e o balanço do componente antes de calcular indicadores.")
    w = {r.fluxo_numero: r.ajustado for r in mass.resultados}
    g = {r.fluxo_numero: r.ajustado for r in comp.resultados}
    if feed_num not in w or prod_num not in w:
        raise ServiceError("Escolha fluxos que existam na usina.")
    if feed_num == prod_num:
        raise ServiceError("Alimentação e produto precisam ser fluxos diferentes.")
    try:
        ind = indicators(w[feed_num], g[feed_num], w[prod_num], g[prod_num])
    except InvalidInputError as exc:
        raise ServiceError(str(exc)) from exc
    return {
        "recuperacao": float(ind.recovery_pct), "razao_enriquecimento": float(ind.enrichment_ratio),
        "razao_concentracao": float(ind.concentration_ratio), "rendimento": float(ind.yield_pct),
        "alimentacao": feed_num, "produto": prod_num, "componente": componente,
        "iter_massa": mass.iteracao, "iter_componente": comp.iteracao,
    }


def observability_for(campanha: Campanha) -> dict | None:
    """Análise de redundância do balanço de massas (fluxos sem medida ou 'não amostrados')."""
    sheet = build_flowsheet(campanha.usina)
    if not sheet.operations:
        return None
    measures = measures_for(campanha, MASSA)
    flows = campanha.usina.fluxos
    measured = [f.id in measures and not measures[f.id].nao_amostrado for f in flows]
    obs = analyze(sheet.matrix(), measured)
    name = {i: f"{f.numero} · {f.nome}" for i, f in enumerate(flows)}
    return {
        "redundancia": obs.redundancy,
        "nao_medidos": [name[j] for j in obs.unmeasured],
        "calculaveis": [name[j] for j in obs.determinable],
        "indeterminados": [name[j] for j in obs.indeterminate],
        "tudo_calculavel": obs.all_observable,
        "n_medidos": len(obs.measured),
    }


# -------------------------------------------------------------------- exportação
def export_csv(campanha: Campanha, componente: str) -> tuple[str, str]:
    """CSV para Excel em português (separador ';', decimal ',', com BOM). Retorna (nome, conteúdo)."""
    ajuste = last_adjustment(campanha, componente)
    if ajuste is None:
        raise ServiceError("Ainda não há ajuste para exportar. Feche o balanço primeiro.")
    unit = unit_for(campanha, componente)

    def num(v: float | None, dec: int = 4) -> str:
        return "" if v is None else f"{v:.{dec}f}".replace(".", ",")

    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", lineterminator="\r\n")
    w.writerow(["usina", campanha.usina.nome]); w.writerow(["campanha", campanha.nome])
    w.writerow(["componente", componente]); w.writerow(["iteracao", ajuste.iteracao])
    w.writerow(["qui_quadrado", num(ajuste.chi2, 3)]); w.writerow(["graus_de_liberdade", ajuste.graus])
    w.writerow([])
    w.writerow(["fluxo", "nome", f"entrada ({unit})", f"desvio ({unit})", f"ajustado ({unit})", "residuo_normalizado",
                "% da alimentacao" if componente == MASSA else "% distribuicao", "acao"])
    for r in ajuste.resultados:
        w.writerow([r.fluxo_numero, r.fluxo_nome, num(r.entrada), num(r.desvio), num(r.ajustado),
                    num(r.residuo_norm, 3), num(r.percentual, 2), r.acao])
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", f"{campanha.usina.nome}_{componente}_it{ajuste.iteracao}")
    return f"simetal_{safe}.csv", "\ufeff" + buf.getvalue()
