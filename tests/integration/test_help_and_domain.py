"""Páginas de ajuda (públicas), rodapé, conta e recursos de domínio da campanha."""

import re


def _setup_demo(client, email="demo@ex.com"):
    client.post("/registrar", data={"nome": "Eng Demo", "email": email, "senha": "senha-forte-123"})
    r = client.post("/usinas/exemplo", follow_redirects=False)
    usina_url = r.headers["location"]
    camp_id = re.search(r"/campanhas/(\d+)", client.get(usina_url).text).group(1)
    return usina_url, camp_id


def test_help_pages_are_public_and_have_content(web):
    expected = {
        "/ajuda": ["Passo a passo", "Antes de começar", "Perfis de usuário"],
        "/ajuda/glossario": ["Hidrociclone", "Recuperação metalúrgica", "filtro-glossario"],
        "/ajuda/metodo": ["Passo 4", "Multiplicadores de Lagrange", "3.750,82", "Referências"],
        "/ajuda/boas-praticas": ["Na coleta de dados", "Perguntas frequentes", "faq-item"],
        "/ajuda/amostras": ["Calculadora de amostras"],
        "/sobre": ["Créditos", "Damasceno", "Privacidade e cookies", "Aviso de uso"],
    }
    for path, snippets in expected.items():
        r = web.get(path)
        assert r.status_code == 200, path
        for text in snippets:
            assert text in r.text, (path, text)


def test_method_page_example_is_computed_by_the_core(web):
    text = web.get("/ajuda/metodo").text
    # resíduos antes do ajuste (medidos) e depois (zero), tirados do próprio cálculo
    assert "-2.899,54" in text and "3.909,57" in text
    assert "0,000000" in text or "-0,000000" in text


def test_footer_is_complete_everywhere(web):
    for path in ("/login", "/ajuda", "/sobre"):
        page = web.get(path).text
        for text in ("Aprender", "Sistema", "Fontes e acessibilidade", "Guia rápido", "Código-fonte no GitHub",
                     "github.com/ElsonJr01/SIMETAL", "Open-Meteo.com", "VLibras", "Damasceno", "Versão 0.2.0"):
            assert text in page, (path, text)


def test_nav_changes_with_login_state(web):
    anon = web.get("/ajuda").text
    assert "Como usar" in anon and "Entrar" in anon and "Sair (" not in anon
    _setup_demo(web)
    logged = web.get("/ajuda").text
    assert "Minha conta" in logged and "Sair (" in logged


def test_sample_calculator(web):
    r = web.post("/ajuda/amostras", data={"texto": "10,0\n12,0\n14,0"})
    assert "12,000" in r.text and "2,000" in r.text  # média e desvio-padrão (n-1)
    assert "insuficiente" in web.post("/ajuda/amostras", data={"texto": "5"}).text
    assert "inválido" in web.post("/ajuda/amostras", data={"texto": "a b c"}).text


def test_account_page_and_password_change(web):
    web.post("/registrar", data={"nome": "Eng Conta", "email": "conta@ex.com", "senha": "senha-forte-123"})
    assert "conta@ex.com" in web.get("/conta").text
    bad = web.post("/conta/senha", data={"atual": "errada", "nova": "outra-senha-1", "confirmar": "outra-senha-1"})
    assert bad.status_code == 422 and "incorreta" in bad.text
    short = web.post("/conta/senha", data={"atual": "senha-forte-123", "nova": "curta", "confirmar": "curta"})
    assert "pelo menos 8" in short.text
    diff = web.post("/conta/senha", data={"atual": "senha-forte-123", "nova": "nova-senha-123", "confirmar": "outra-coisa"})
    assert "não confere" in diff.text
    ok = web.post("/conta/senha", data={"atual": "senha-forte-123", "nova": "nova-senha-123", "confirmar": "nova-senha-123"}, follow_redirects=True)
    assert "Senha alterada" in ok.text
    web.cookies.clear()
    assert web.post("/api/v1/auth/login", json={"email": "conta@ex.com", "senha": "senha-forte-123"}).status_code == 401
    assert web.post("/api/v1/auth/login", json={"email": "conta@ex.com", "senha": "nova-senha-123"}).status_code == 200


def test_distribution_column_and_indicators_on_campaign(web):
    _, camp = _setup_demo(web)
    web.post(f"/campanhas/{camp}/ajustar", data={"componente": "massa"})
    r = web.post(f"/campanhas/{camp}/ajustar", data={"componente": "cinzas"})
    assert "% de distribuição" in r.text and "21,78" in r.text and "50,55" in r.text  # Tabela 2 da monografia
    page = web.get(f"/campanhas/{camp}?componente=cinzas").text
    assert "Indicadores metalúrgicos de cinzas" in page
    ind = web.get(f"/campanhas/{camp}/indicadores?componente=cinzas&alim=1&prod=6")
    assert "50,55" in ind.text and "Recuperação metalúrgica" in ind.text and "67,53" in ind.text  # recuperação e rendimento
    assert "diferentes" in web.get(f"/campanhas/{camp}/indicadores?componente=cinzas&alim=2&prod=2").text
    assert "Feche o balanço" in web.get(f"/campanhas/{camp}/indicadores?componente=massa&alim=1&prod=6").text


def test_redundancy_panel_and_units(web):
    _, camp = _setup_demo(web)
    page = web.get(f"/campanhas/{camp}").text
    assert "Análise de redundância" in page and "Equações que sobram" in page
    r = web.post(f"/campanhas/{camp}/unidades", data={"componente": "massa", "unidade_vazao": "kg/h", "unidade_teor": "g/t"}, follow_redirects=True)
    assert "Unidades atualizadas" in r.text and "kg/h" in r.text
    bad = web.post(f"/campanhas/{camp}/unidades", data={"componente": "massa", "unidade_vazao": "<b>", "unidade_teor": "%"}, follow_redirects=True)
    assert "inválida" in bad.text


def test_paste_from_spreadsheet(web):
    _, camp = _setup_demo(web)
    text = "100,5\t5\n40\t4\n60\t6\n10\t1\n20\t2\n30\t3"
    r = web.post(f"/campanhas/{camp}/colar", data={"componente": "massa", "texto": text}, follow_redirects=True)
    assert "6 linha(s) importada(s)" in r.text and "100.5" in r.text
    bad = web.post(f"/campanhas/{camp}/colar", data={"componente": "massa", "texto": "1;2;3;4"}, follow_redirects=True)
    assert "Linha 1" in bad.text


def test_csv_export(web):
    _, camp = _setup_demo(web)
    empty = web.get(f"/campanhas/{camp}/exportar?componente=massa", follow_redirects=True)
    assert "Ainda não há ajuste" in empty.text
    web.post(f"/campanhas/{camp}/ajustar", data={"componente": "massa"})
    r = web.get(f"/campanhas/{camp}/exportar?componente=massa")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"] and r.headers["content-disposition"].endswith('.csv"')
    body = r.content.decode("utf-8")
    assert body.startswith("\ufeff") and "fluxo;nome;entrada (t/h)" in body and "3750,82" in body
