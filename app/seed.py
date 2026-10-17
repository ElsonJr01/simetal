"""Dados de demonstração: circuito de finos retornados da Cia. Carbonífera Cambuí
(Chaves, 1990, apud Damasceno & Nunes, 1992). Tabelas 1 e 2 da monografia."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Campanha, Medida, Usina
from app.services import save_flowsheet

CAMBUI_FLOWS = [
    "Alimentação ciclone",
    "Overflow ciclone",
    "Underflow ciclone",
    "Rejeito espiral",
    "Midlings",
    "Concentrado espiral",
]
CAMBUI_OPS = [("Ciclone", [1], [2, 3]), ("Espiral", [3], [4, 5, 6])]
CAMBUI_MASSA = [(3682.36, 3682.36), (554.1, 554.1), (6027.8, 858.423), (239.85, 63.701), (405.13, 35.613), (1473.25, 525.66)]
CAMBUI_CINZAS = [(23.04, 23.04), (49.95, 2.747), (32.59, 6.06), (80.37, 3.201), (35.35, 4.683), (24.78, 4.898)]


def create_cambui(db: Session, dono_id: int) -> Usina:
    usina = Usina(nome="Cambuí (exemplo)", descricao="Circuito de finos retornados - dados da monografia.", dono_id=dono_id)
    db.add(usina)
    db.flush()
    save_flowsheet(db, usina, CAMBUI_FLOWS, CAMBUI_OPS)
    camp = Campanha(usina_id=usina.id, nome="Campanha 1990 (monografia)")
    db.add(camp)
    db.flush()
    for componente, dados in (("massa", CAMBUI_MASSA), ("cinzas", CAMBUI_CINZAS)):
        for fluxo, (valor, desvio) in zip(usina.fluxos, dados, strict=True):
            db.add(Medida(campanha_id=camp.id, fluxo_id=fluxo.id, componente=componente, valor=valor, desvio=desvio))
    db.commit()
    return usina
