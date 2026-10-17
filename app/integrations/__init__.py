"""Integrações com dados públicos (IBGE, Open-Meteo, catálogo ANM).

Regra de ouro: uma fonte externa fora do ar NUNCA pode quebrar o balanço de massas.
Todas as falhas viram IntegrationError, tratadas na borda (rotas) com mensagem amigável.
"""
