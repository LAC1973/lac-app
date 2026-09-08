"""
Importação única dos dados históricos da planilha de gerenciamento para o LAC Solar.

Uso:
    python importar_excel.py --arquivo "2026_geral_gerenciamento.xlsx" --etapa usinas --dry-run
    python importar_excel.py --arquivo "2026_geral_gerenciamento.xlsx" --etapa usinas

Etapas (rodar nesta ordem, cada uma depende da anterior):
    1. usinas      -> usinas + inversores + placas       (aba "Dados Usinas")
    2. clientes    -> clientes + clientes_ucs            (abas "FATURAS" / "RGD")   [pendente]
    3. percentuais -> percentuais                        (aba "Percentuais")        [pendente]
    4. faturas     -> faturas                            (abas "FATURAS" / "RGD")   [pendente]
    5. producao    -> producao_diaria                    (abas "D- Conj N")         [pendente]

O script é idempotente: roda de novo sem duplicar (faz match por chave natural).
"""

import argparse
import os
import re
import sys
from datetime import date

import openpyxl
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------- infraestrutura

_sb = None


def sb():
    global _sb
    if _sb is None:
        from supabase import create_client  # importado só quando vai gravar de verdade

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")
        if not url or not key:
            sys.exit("Defina SUPABASE_URL e SUPABASE_SERVICE_KEY no .env do backend.")
        _sb = create_client(url, key)
    return _sb


class Ctx:
    """Contexto da execução: controla dry-run e acumula o log."""

    def __init__(self, dry_run: bool):
        self.dry_run = dry_run
        self.criados = 0
        self.atualizados = 0
        self.pulados = 0
        self.erros = []

    def log(self, msg):
        prefixo = "[SIMULA] " if self.dry_run else "         "
        print(prefixo + msg)

    def erro(self, msg):
        self.erros.append(msg)
        print("  !! " + msg)

    def resumo(self, titulo):
        print("\n" + "=" * 60)
        print(f"{titulo}: {self.criados} criados, {self.atualizados} atualizados, "
              f"{self.pulados} pulados, {len(self.erros)} erros")
        if self.dry_run:
            print("(dry-run — nada foi gravado no banco)")
        print("=" * 60)


# ---------------------------------------------------------------- helpers de parsing

MARCAS_VALIDAS = ["Growatt", "Solis", "SAJ", "Fronius", "Candian", "Deye"]

# A planilha usa grafias diferentes das aceitas pelo app.
NORMALIZA_MARCA = {
    "growaltt": "Growatt",
    "growatt": "Growatt",
    "grow": "Growatt",
    "solis": "Solis",
    "saj": "SAJ",
    "fronius": "Fronius",
    "candian": "Candian",
    "canadian": "Candian",
    "canidian": "Candian",  # grafia usada na usina 05 da planilha
    "deye": "Deye",
}


def marca_inversor(valor):
    if not valor:
        return None
    chave = str(valor).strip().lower()
    return NORMALIZA_MARCA.get(chave)


def num(valor):
    """Converte célula em float. Aceita '112,5 kwp', '85 kwp', 90.0, None."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    txt = str(valor).strip().replace(".", "").replace(",", ".")
    achado = re.search(r"-?\d+(?:\.\d+)?", txt)
    return float(achado.group()) if achado else None


def inteiro(valor):
    v = num(valor)
    return int(v) if v is not None else None


def texto(valor):
    if valor is None:
        return None
    t = str(valor).strip()
    return t or None


def para_data(valor):
    if valor is None or valor == "":
        return None
    if hasattr(valor, "date"):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    return None


# ---------------------------------------------------------------- ETAPA 1: usinas

# A aba "Dados Usinas" repete o mesmo bloco a cada 21 linhas.
# Bloco começando na linha B (B=2 para a usina 0):
#   B+0  B: nº da usina | D: nome da usina        | F: observações
#   B+1  D: nome do proprietário
#   B+2  D: CPF          B+3 D: identidade        B+4 D: celular
#   B+5  D: endereço     B+6 D: UC/poste          B+7 D: início da operação
#   B+8  D: dia da leitura                        B+9 D: potência do transformador
#   B+14..B+18  linhas dos inversores 01..05
#        C: rótulo | D: marca | E: potência kWp | G: qtd placas | H: potência Wp da placa
BLOCO_PRIMEIRA_LINHA = 2
BLOCO_ALTURA = 21
BLOCO_MAX_USINAS = 20
INVERSOR_OFFSET = 14
INVERSOR_QTD = 5


def ler_usinas(caminho):
    """Lê a aba 'Dados Usinas' e devolve uma lista de dicts prontos pro banco."""
    wb = openpyxl.load_workbook(caminho, data_only=True)
    ws = wb["Dados Usinas"]
    usinas = []

    for i in range(BLOCO_MAX_USINAS):
        base = BLOCO_PRIMEIRA_LINHA + i * BLOCO_ALTURA
        if base > ws.max_row:
            break

        nome = texto(ws.cell(base, 4).value)
        if not nome or not nome.upper().startswith("USINA"):
            continue

        usina = {
            "nome": nome,
            "proprietario_nome": texto(ws.cell(base + 1, 4).value),
            "proprietario_cpf": texto(ws.cell(base + 2, 4).value),
            "proprietario_identidade": texto(ws.cell(base + 3, 4).value),
            "proprietario_celular": texto(ws.cell(base + 4, 4).value),
            "proprietario_endereco": texto(ws.cell(base + 5, 4).value),
            "uc_poste": texto(ws.cell(base + 6, 4).value),
            "inicio_operacao": para_data(ws.cell(base + 7, 4).value),
            "data_leitura": inteiro(ws.cell(base + 8, 4).value),
            "potencia_kwp": num(ws.cell(base + 9, 4).value),
            "observacoes": texto(ws.cell(base, 6).value),
            "_inversores": [],
        }

        for j in range(INVERSOR_QTD):
            linha = base + INVERSOR_OFFSET + j
            marca_raw = ws.cell(linha, 4).value
            potencia = num(ws.cell(linha, 5).value)
            if not marca_raw or not potencia:
                continue  # linha "Inversor 04:" vazia

            marca = marca_inversor(marca_raw)
            if marca is None:
                marca = texto(marca_raw)  # mantém o original; reportado depois

            inv = {
                "marca": marca,
                "_marca_original": texto(marca_raw),
                "potencia_kwp": potencia,
                "tipo": "principal" if j == 0 else "secundario",
                "ordem": j + 1,
                "_placas": [],
            }

            qtd = inteiro(ws.cell(linha, 7).value)
            pot_wp = num(ws.cell(linha, 8).value)
            if qtd and pot_wp:
                inv["_placas"].append({"quantidade": qtd, "potencia_wp": pot_wp})

            usina["_inversores"].append(inv)

        usinas.append(usina)

    return usinas


def importar_usinas(caminho, ctx):
    usinas = ler_usinas(caminho)
    print(f"\nEncontradas {len(usinas)} usinas na aba 'Dados Usinas'.\n")

    if not ctx.dry_run:
        existentes = {u["nome"]: u["id"] for u in sb().table("usinas").select("id, nome").execute().data or []}
    else:
        existentes = {}

    for u in usinas:
        inversores = u.pop("_inversores")
        nome = u["nome"]

        marcas_ruins = [i["_marca_original"] for i in inversores if i["marca"] not in MARCAS_VALIDAS]
        if marcas_ruins:
            ctx.erro(f"{nome}: marca de inversor fora da lista do app -> {marcas_ruins} "
                     f"(aceitas: {', '.join(MARCAS_VALIDAS)})")

        dados = {k: v for k, v in u.items() if v is not None}

        if nome in existentes:
            usina_id = existentes[nome]
            ctx.log(f"Atualiza usina '{nome}' (id={usina_id})")
            if not ctx.dry_run:
                sb().table("usinas").update(dados).eq("id", usina_id).execute()
            ctx.atualizados += 1
        else:
            ctx.log(f"Cria usina '{nome}' — {u.get('potencia_kwp')} kWp, "
                    f"leitura dia {u.get('data_leitura')}, {len(inversores)} inversor(es)")
            usina_id = None
            if not ctx.dry_run:
                res = sb().table("usinas").insert(dados).execute()
                usina_id = res.data[0]["id"]
            ctx.criados += 1

        # inversores: match por (ordem) dentro da usina
        if not ctx.dry_run:
            invs_atuais = {i["ordem"]: i["id"] for i in
                           sb().table("inversores").select("id, ordem").eq("usina_id", usina_id).execute().data or []}
        else:
            invs_atuais = {}

        for inv in inversores:
            placas = inv.pop("_placas")
            inv.pop("_marca_original")
            ctx.log(f"   inversor {inv['ordem']}: {inv['marca']} {inv['potencia_kwp']} kWp"
                    + (f" + {placas[0]['quantidade']}x{placas[0]['potencia_wp']}Wp" if placas else ""))

            if ctx.dry_run:
                continue

            if inv["ordem"] in invs_atuais:
                inv_id = invs_atuais[inv["ordem"]]
                sb().table("inversores").update(inv).eq("id", inv_id).execute()
            else:
                inv_id = sb().table("inversores").insert({**inv, "usina_id": usina_id}).execute().data[0]["id"]

            for p in placas:
                ja_tem = sb().table("placas").select("id").eq("inversor_id", inv_id).execute().data
                if ja_tem:
                    sb().table("placas").update(p).eq("id", ja_tem[0]["id"]).execute()
                else:
                    sb().table("placas").insert({**p, "inversor_id": inv_id, "usina_id": usina_id}).execute()

    ctx.resumo("Usinas")


# ---------------------------------------------------------------- resolver usinas

# As usinas já estão cadastradas no banco. Para as etapas seguintes precisamos
# ligar cada bloco da planilha ("USINA 03 - Parque Mirella II - Ant") à usina
# certa. O match é feito pelo prefixo "USINA NN", que é estável mesmo se o nome
# no banco estiver escrito diferente. Se algum não bater, preencha na mão aqui:
#   MAPA_USINAS_MANUAL = {"USINA 05": 12}
MAPA_USINAS_MANUAL = {}

PREFIXO_USINA = re.compile(r"USINA\s*(\d+)", re.IGNORECASE)


def prefixo_usina(nome):
    """'USINA 03 - Parque Mirella II - Ant' -> 'USINA 03'"""
    m = PREFIXO_USINA.search(nome or "")
    return f"USINA {int(m.group(1)):02d}" if m else None


def resolver_usinas(ctx):
    """Devolve {'USINA 00': id, ...} a partir do que já existe no banco."""
    if ctx.dry_run:
        return {}
    mapa = {}
    for u in sb().table("usinas").select("id, nome").execute().data or []:
        p = prefixo_usina(u["nome"])
        if p:
            mapa[p] = u["id"]
    mapa.update(MAPA_USINAS_MANUAL)
    print(f"Usinas encontradas no banco: {', '.join(sorted(mapa)) or '(nenhuma)'}")
    return mapa


# ---------------------------------------------------------------- ETAPA 2: clientes

RE_NUMERO_UC = re.compile(r"^\s*\d+/\d+-\d\s*$")
RE_DIA = re.compile(r"(\d{1,2})")

# --- Correções combinadas com o Luiz -------------------------------------
# A aba RECIBOS tem alguns números de UC digitados errado. A aba FATURAS é a
# fonte da verdade (é ela que alimenta RGD, Percentuais e Saldo ACM), então
# aqui corrigimos o que vem de RECIBOS antes de cruzar.
#   {(nome do cliente, numero errado): numero certo}
CORRIGE_UC_RECIBOS = {
    # A UC da Beatriz é a "Cativa 2 (poste 4)". Em RECIBOS ela foi digitada com
    # o número da Alva Contadora, o que fazia a mesma UC cair em dois clientes.
    ("Beatriz Ariane Miguel da Silva", "6/5279496-3"): "6/5269650-7",
}

# UCs que o cliente trocou: {numero antigo: numero novo}.
# A partir da troca, FATURAS/RGD/Percentuais passam a usar só o número novo,
# então o cruzamento é sempre feito pelo novo. No banco os dois ficam
# guardados: 'numero_uc' recebe o antigo e 'numero_uc_novo' recebe o atual,
# que é a convenção da tela de clientes.
TROCAS_UC = {
    "6/4993134-8": "6/5255692-5",  # Jucielly Silveira Penteado, trocou em 2026
}

UC_NOVA_PARA_ANTIGA = {novo: antigo for antigo, novo in TROCAS_UC.items()}

# Números de UC digitados errado em alguma aba. A forma correta é a que
# aparece em FATURAS e RECIBOS.
CORRIGE_UC_DIGITACAO = {
    "6/52779496-3": "6/5279496-3",  # Dalva (Contadora), célula E87 de Percentuais
}

# Nomes de cliente a corrigir na importação.
# (nenhum no momento)
CORRIGE_NOME_CLIENTE = {}

# UCs das próprias usinas: aparecem em FATURAS mas não são cliente de ninguém.
# Não devem virar cliente nem UC — elas são o ponto de geração.
UCS_DAS_USINAS = {
    "6/2636350-7",  # Poste 00 - LAC Concursos
    "6/3211493-6",  # Poste 01 - Mirella - LAC
    "6/4437581-4",  # Poste 02 - Mirella - João
    "6/4231936-8",  # Poste 03 - Mirella - Antonio
    "6/4231532-5",  # Poste 04 - Mirella - Vini
    "6/5259361-3",  # Poste 05 - Mirella - Aninha
}

# UCs que entram na compensação só agora e ainda não têm cadastro em RECIBOS.
# Decisão do Luiz: ficam fora da importação e serão cadastradas direto no
# sistema quando começarem a compensar.
UCS_FORA_DA_IMPORTACAO = {
    "6/5385480-8": "Andreia (Paulix)",
    "6/5402349-4": "Zelita (mãe da Jucielly)",
}

# UCs de clientes que saíram. Continuam aparecendo nas abas FATURAS e RECIBOS,
# então sem esta lista a reimportação recriaria o que já foi excluído na mão.
# Quando todas as UCs de um cliente estão aqui, o cliente também é pulado.
UCS_ENCERRADAS = {
    "6/5153334-7": "Francisco (Lancha) — saiu",
    "6/4754874-8": "Moisés Pereira Bastos — saiu",
    "6/5088251-3": "Águas do Manso 06 (Leonardo) — UC desativada",
    "6/4223815-4": "Valdomiro Antunes de Almeida Junior — saiu",
    "6/5166399-5": "Leonardo Klein Rezende — saiu",
}


def indexar_ucs_faturas(caminho):
    """
    Varre a aba FATURAS e monta {numero_uc: {...}}.
    A aba é uma sequência de blocos por usina; cada bloco tem uma linha de
    cabeçalho ('Item | Nome da UC | ... | número da UC') e as UCs abaixo dela.
    Coluna B=item, C=nome da UC, D=dia da leitura, F=número da UC.
    """
    wb = openpyxl.load_workbook(caminho, data_only=True)
    ws = wb["FATURAS"]
    ucs = {}
    usina_atual = None
    desativado = False
    fechado = False  # já passou pela linha de "Total" do bloco

    for linha in range(1, ws.max_row + 1):
        b = texto(ws.cell(linha, 2).value)
        c = texto(ws.cell(linha, 3).value)

        if b and prefixo_usina(b):
            usina_atual = prefixo_usina(b)
            desativado = False
            fechado = False
            continue
        if c and c.lower().startswith("desativado"):
            desativado = True
            fechado = False
            continue

        rotulo_f = texto(ws.cell(linha, 6).value)
        if rotulo_f and rotulo_f.strip().lower() == "total":
            # Depois do Total só há sobras soltas na planilha (ex.: a linha 68,
            # com um número de UC que não aparece em nenhuma outra aba).
            fechado = True
            continue

        numero = rotulo_f
        if not numero or not RE_NUMERO_UC.match(numero) or fechado:
            continue  # pula 'Total', cabeçalhos, linhas vazias e restos de bloco

        numero = numero.strip()
        ucs[numero] = {
            "numero_uc": numero,
            "nome_uc": c,
            "item": inteiro(b),
            "dia_leitura": inteiro(ws.cell(linha, 4).value),
            "codigo_energisa": texto(ws.cell(linha, 5).value),
            "usina_prefixo": usina_atual,
            "linha": linha,
            "activo": not desativado,
        }

    return ucs


def ler_clientes(caminho):
    """
    Varre a aba RECIBOS. Cada cliente é um bloco que começa numa linha com
    número na coluna A e 'Nome' na coluna B. A altura do bloco varia, então a
    varredura vai até o começo do próximo bloco.
    Dentro do bloco, a lista de UCs do cliente está em B (nome) / C (número).
    """
    wb = openpyxl.load_workbook(caminho, data_only=True)
    ws = wb["RECIBOS"]

    inicios = []
    for linha in range(1, ws.max_row + 1):
        a = ws.cell(linha, 1).value
        b = texto(ws.cell(linha, 2).value)
        if isinstance(a, (int, float)) and b and b.lower().startswith("nome"):
            inicios.append(linha)

    clientes = []
    for idx, inicio in enumerate(inicios):
        fim = inicios[idx + 1] - 1 if idx + 1 < len(inicios) else ws.max_row

        rotulos = {}
        ucs = []
        for linha in range(inicio, fim + 1):
            rotulo = texto(ws.cell(linha, 2).value)
            valor = ws.cell(linha, 3).value
            if not rotulo:
                continue
            if valor and RE_NUMERO_UC.match(str(valor)):
                ucs.append({"nome_uc": rotulo, "numero_uc": str(valor).strip()})
            else:
                chave = rotulo.lower().rstrip(":").strip()
                if chave not in rotulos:
                    rotulos[chave] = valor

        nome = texto(rotulos.get("nome"))
        if not nome:
            continue
        nome = CORRIGE_NOME_CLIENTE.get(nome, nome)

        for uc in ucs:
            certo = CORRIGE_UC_RECIBOS.get((nome, uc["numero_uc"]))
            if certo:
                uc["numero_uc"] = certo
            # UC trocada: a partir daqui trabalhamos sempre com o número novo
            uc["numero_uc"] = TROCAS_UC.get(uc["numero_uc"], uc["numero_uc"])
        # depois de normalizar, a UC trocada aparece duas vezes no mesmo bloco
        vistas, unicas = set(), []
        for uc in ucs:
            if uc["numero_uc"] not in vistas:
                vistas.add(uc["numero_uc"])
                unicas.append(uc)
        ucs = unicas

        vencimento = texto(rotulos.get("data de vencimento"))
        dia_venc = RE_DIA.search(vencimento) if vencimento else None

        clientes.append({
            "item": inteiro(ws.cell(inicio, 1).value),
            "nome": nome,
            "cpf_cnpj": texto(rotulos.get("cpf/cnpj")),
            "identidade": texto(rotulos.get("identidade")),
            "celular": texto(rotulos.get("celular")),
            "email": texto(rotulos.get("e-mail")),
            "endereco": texto(rotulos.get("endereco") or rotulos.get("endereço")),
            "data_contratacao": para_data(rotulos.get("data da contratação")),
            "valor_kwh": num(rotulos.get("valor do kwh/mês")) or 0.75,
            "dia_vencimento": int(dia_venc.group(1)) if dia_venc else 5,
            "_ucs": ucs,
            "_linha": inicio,
        })

    return clientes


def importar_clientes(caminho, ctx):
    ucs_faturas = indexar_ucs_faturas(caminho)
    clientes = ler_clientes(caminho)
    mapa_usinas = resolver_usinas(ctx)

    ucs_usadas = set()
    dono = {}
    for c in clientes:
        for u in c["_ucs"]:
            ucs_usadas.add(u["numero_uc"])
            dono.setdefault(u["numero_uc"], []).append(c["nome"])

    for numero, donos in dono.items():
        if len(donos) > 1:
            ctx.erro(f"UC {numero} aparece em mais de um cliente: {', '.join(donos)} "
                     f"— o script gravaria só o último")

    orfas = sorted(set(ucs_faturas) - ucs_usadas - UCS_DAS_USINAS - set(UCS_FORA_DA_IMPORTACAO))

    print(f"\n{len(clientes)} clientes na aba RECIBOS, "
          f"{len(ucs_faturas)} UCs na aba FATURAS, "
          f"{len(ucs_usadas)} UCs ligadas a algum cliente.\n")

    if not ctx.dry_run:
        existentes = {}
        for c in sb().table("clientes").select("id, nome, cpf_cnpj").execute().data or []:
            existentes[(c.get("cpf_cnpj") or c["nome"]).strip()] = c["id"]
        ucs_existentes = {}
        for u in sb().table("clientes_ucs").select(
                "id, numero_uc, numero_uc_novo").execute().data or []:
            ucs_existentes[u["numero_uc"]] = u["id"]
            if u.get("numero_uc_novo"):
                # uma UC trocada pode estar cadastrada pelo número novo
                ucs_existentes.setdefault(u["numero_uc_novo"], u["id"])
    else:
        existentes, ucs_existentes = {}, {}

    encerrados = []
    for c in clientes:
        ucs = c.pop("_ucs")
        linha = c.pop("_linha")

        restantes = [u for u in ucs if u["numero_uc"] not in UCS_ENCERRADAS]
        if not restantes:
            encerrados.append(c["nome"])
            ctx.pulados += 1
            continue
        ucs = restantes

        chave = (c.get("cpf_cnpj") or c["nome"]).strip()

        if not c.get("cpf_cnpj"):
            ctx.erro(f"'{c['nome']}' (RECIBOS linha {linha}) está sem CPF/CNPJ")

        dados = {k: v for k, v in c.items() if v is not None}
        dados["activo"] = True
        dados["eh_agregado"] = False

        if chave in existentes:
            cliente_id = existentes[chave]
            ctx.log(f"Atualiza cliente '{c['nome']}' (id={cliente_id})")
            if not ctx.dry_run:
                sb().table("clientes").update(dados).eq("id", cliente_id).execute()
            ctx.atualizados += 1
        else:
            ctx.log(f"Cria cliente '{c['nome']}' — venc. dia {c['dia_vencimento']}, "
                    f"R$ {c['valor_kwh']}/kWh, {len(ucs)} UC(s)")
            cliente_id = None
            if not ctx.dry_run:
                cliente_id = sb().table("clientes").insert(dados).execute().data[0]["id"]
            ctx.criados += 1

        for uc in ucs:
            info = ucs_faturas.get(uc["numero_uc"])
            if info is None:
                ctx.erro(f"UC {uc['numero_uc']} ('{uc['nome_uc']}', cliente {c['nome']}) "
                         f"não existe na aba FATURAS — sem usina para vincular")
                continue

            usina_id = mapa_usinas.get(info["usina_prefixo"])
            if not ctx.dry_run and usina_id is None:
                ctx.erro(f"UC {uc['numero_uc']}: usina '{info['usina_prefixo']}' "
                         f"não encontrada no banco (veja MAPA_USINAS_MANUAL)")
                continue

            antiga = UC_NOVA_PARA_ANTIGA.get(uc["numero_uc"])
            registro = {
                "cliente_id": cliente_id,
                "usina_id": usina_id,
                "nome_uc": info["nome_uc"] or uc["nome_uc"],
                "numero_uc": antiga or uc["numero_uc"],
                "numero_uc_novo": uc["numero_uc"] if antiga else None,
                "item": info["item"],
                "dia_leitura": info["dia_leitura"],
            }
            if antiga:
                ctx.log(f"   UC {antiga} -> {uc['numero_uc']} (trocada) — "
                        f"{registro['nome_uc']} ({info['usina_prefixo']})")
            else:
                ctx.log(f"   UC {uc['numero_uc']} — {registro['nome_uc']} "
                        f"({info['usina_prefixo']}, leitura dia {info['dia_leitura']})")

            if ctx.dry_run:
                continue
            existente_id = (ucs_existentes.get(registro["numero_uc"])
                            or ucs_existentes.get(uc["numero_uc"]))
            if existente_id:
                sb().table("clientes_ucs").update(registro).eq("id", existente_id).execute()
            else:
                sb().table("clientes_ucs").insert(registro).execute()

    if encerrados:
        print(f"\nPulados por terem saído (já excluídos no sistema): "
              f"{', '.join(encerrados)}")

    print("\nDeixadas de fora de propósito (cadastrar na mão quando entrarem "
          "na compensação):")
    for numero, quem in sorted(UCS_FORA_DA_IMPORTACAO.items()):
        print(f"  - {numero:16s} {quem}")

    if orfas:
        print(f"\n{len(orfas)} UCs em FATURAS ainda sem cliente "
              f"(fora as {len(UCS_DAS_USINAS)} UCs das próprias usinas, que são ignoradas):")
        for numero in orfas:
            info = ucs_faturas[numero]
            marca = "" if info["activo"] else "  [desativada]"
            print(f"  - {numero:16s} {str(info['nome_uc'])[:40]:42s} {info['usina_prefixo']}{marca}")

    ctx.resumo("Clientes")


# ---------------------------------------------------------------- ETAPA 3: percentuais

# Na aba "Percentuais" cada usina é um bloco. A linha de cabeçalho tem
# 'Item' na coluna C e, a partir da coluna I, uma data por coluna: é a
# data_vigencia daquele rateio. As colunas vêm da mais recente para a mais
# antiga. Colunas antes de I são de controle ('PRÓXIMO') e são ignoradas.
PRIMEIRA_COLUNA_DATA = 9  # coluna I

# Rateio vigente de cada usina, confirmado com o Luiz. Serve de trava: se
# alguém reordenar as colunas da planilha, o script acusa em vez de importar
# um rateio antigo como se fosse o atual. Atualize junto com a planilha.
VIGENTE_ESPERADO = {
    "USINA 00": "2026-02-07",
    "USINA 01": "2026-02-07",
    "USINA 02": "2026-09-03",
    "USINA 03": "2026-06-25",
    "USINA 04": "2026-05-20",
}


def ler_percentuais(caminho, historico=False):
    """
    Por padrão importa apenas a coluna I de cada bloco, que é o rateio vigente.
    Com historico=True traz também as colunas anteriores (rateios antigos).
    """
    wb = openpyxl.load_workbook(caminho, data_only=True)
    ws = wb["Percentuais"]

    registros = []
    fora_do_bloco = []
    repetidos = []
    vistos = set()
    usina_atual = None
    colunas = {}   # {coluna: data_vigencia}
    fechado = False

    for linha in range(1, ws.max_row + 1):
        c = texto(ws.cell(linha, 3).value)
        e = texto(ws.cell(linha, 5).value)

        if c and prefixo_usina(c):
            usina_atual = prefixo_usina(c)
            colunas = {}
            fechado = False
            continue

        if c and c.strip().lower() == "item":
            colunas = {}
            ultima = ws.max_column if historico else PRIMEIRA_COLUNA_DATA
            for col in range(PRIMEIRA_COLUNA_DATA, ultima + 1):
                d = para_data(ws.cell(linha, col).value)
                if d:
                    colunas[col] = d
            continue

        if e and e.strip().lower() == "total":
            fechado = True
            continue

        if not e or not RE_NUMERO_UC.match(e) or not colunas:
            continue

        numero = e.strip()
        numero = CORRIGE_UC_DIGITACAO.get(numero, numero)
        numero = TROCAS_UC.get(numero, numero)
        for col, vigencia in colunas.items():
            valor = ws.cell(linha, col).value
            if valor is None or valor == "" or str(valor).strip() == "-":
                continue
            pct = num(valor)
            if pct is None:
                continue
            # A planilha guarda o rateio como fração (0,05). O sistema usa a
            # escala de 0 a 100 — a tela mostra o número cru com '%' e a fatura
            # calcula percentual/100.
            pct = round(pct * 100, 4)
            item = {
                "numero_uc": numero,
                "nome_uc": texto(ws.cell(linha, 4).value),
                "usina_prefixo": usina_atual,
                "percentual": pct,
                "data_vigencia": vigencia,
                "linha": linha,
            }
            if fechado:
                fora_do_bloco.append(item)
                continue

            # A USINA 03 tem a data 2025-08-20 repetida em duas colunas do
            # cabeçalho, com valores diferentes. Vale a coluna mais à esquerda
            # (a mais recente na ordem da planilha); a outra fica registrada.
            chave_unica = (usina_atual, numero, vigencia)
            if chave_unica in vistos:
                repetidos.append(item)
                continue
            vistos.add(chave_unica)
            registros.append(item)

    return registros, fora_do_bloco, repetidos


def importar_percentuais(caminho, ctx, historico=False):
    registros, fora_do_bloco, repetidos = ler_percentuais(caminho, historico)
    mapa_usinas = resolver_usinas(ctx)
    if not historico:
        print("Importando apenas o rateio vigente de cada usina (coluna I).\n")

    if repetidos:
        datas_rep = sorted({(r["usina_prefixo"], r["data_vigencia"]) for r in repetidos})
        print("Aviso: data de vigência repetida no cabeçalho — usei a primeira "
              "coluna e descartei a segunda:")
        for usina, vigencia in datas_rep:
            print(f"  - {usina} {vigencia} ({sum(1 for r in repetidos if r['data_vigencia'] == vigencia)} UCs)")
        print()

    datas = sorted({r["data_vigencia"] for r in registros})
    ucs = sorted({r["numero_uc"] for r in registros})
    print(f"\n{len(registros)} percentuais, {len(ucs)} UCs, "
          f"{len(datas)} datas de vigência ({datas[0]} a {datas[-1]}).\n")

    # Rateios antigos da planilha nem sempre fecham em 100%. Por orientação do
    # Luiz isso é histórico e não impede a importação — fica só como aviso.
    somas = {}
    for r in registros:
        chave = (r["usina_prefixo"], r["data_vigencia"])
        somas[chave] = somas.get(chave, 0) + r["percentual"]
    fora = [(u, v, t) for (u, v), t in sorted(somas.items()) if abs(t - 100) > 1.1]
    if fora:
        print(f"Aviso: {len(fora)} rateios não fecham em 100% (importados assim mesmo):")
        for usina, vigencia, total in fora:
            print(f"  - {usina} {vigencia}: {total:.0f}%")
        print()

    # trava: a data mais recente de cada usina tem que ser o rateio vigente
    vigente_lido = {}
    for r in registros:
        u = r["usina_prefixo"]
        if r["data_vigencia"] > vigente_lido.get(u, ""):
            vigente_lido[u] = r["data_vigencia"]
    for usina, esperado in sorted(VIGENTE_ESPERADO.items()):
        lido = vigente_lido.get(usina)
        if lido is None:
            ctx.erro(f"{usina}: nenhum percentual encontrado na planilha")
        elif lido != esperado:
            ctx.erro(f"{usina}: o rateio mais recente da planilha é {lido}, "
                     f"mas o vigente confirmado é {esperado} — confira se as "
                     f"colunas da aba Percentuais foram reordenadas")
    if not ctx.erros:
        print("Rateio vigente de cada usina confere com o combinado.\n")

    if ctx.dry_run:
        ucs_banco = {}
    else:
        ucs_banco = {}
        for u in sb().table("clientes_ucs").select(
                "id, cliente_id, numero_uc, numero_uc_novo").execute().data or []:
            dados_uc = (u["id"], u["cliente_id"])
            ucs_banco[u["numero_uc"]] = dados_uc
            if u.get("numero_uc_novo"):
                ucs_banco[u["numero_uc_novo"]] = dados_uc

        existentes = {}
        for p in sb().table("percentuais").select(
                "id, cliente_uc_id, usina_id, data_vigencia, percentual").execute().data or []:
            existentes[(p["cliente_uc_id"], p["usina_id"], p["data_vigencia"])] = (
                p["id"], float(p["percentual"]))

    ignoradas = set()
    for r in registros:
        if r["numero_uc"] in UCS_FORA_DA_IMPORTACAO or r["numero_uc"] in UCS_ENCERRADAS:
            ignoradas.add(r["numero_uc"])
            continue

        usina_id = mapa_usinas.get(r["usina_prefixo"])
        if not ctx.dry_run and usina_id is None:
            ctx.erro(f"{r['usina_prefixo']} não existe no banco "
                     f"(percentual da UC {r['numero_uc']} em {r['data_vigencia']})")
            continue

        if ctx.dry_run:
            ctx.log(f"{r['usina_prefixo']} {r['data_vigencia']} — "
                    f"UC {r['numero_uc']}: {r['percentual']:.0f}%")
            ctx.criados += 1
            continue

        achado = ucs_banco.get(r["numero_uc"])
        if achado is None:
            ctx.erro(f"UC {r['numero_uc']} ('{r['nome_uc']}') não está cadastrada "
                     f"— rode a etapa clientes antes")
            continue
        uc_id, cliente_id = achado

        chave = (uc_id, usina_id, r["data_vigencia"])
        if chave in existentes:
            registro_id, valor_atual = existentes[chave]
            if abs(valor_atual - r["percentual"]) < 0.0001:
                ctx.pulados += 1
            else:
                sb().table("percentuais").update(
                    {"percentual": r["percentual"]}).eq("id", registro_id).execute()
                ctx.log(f"{r['usina_prefixo']} {r['data_vigencia']} — UC {r['numero_uc']}: "
                        f"{valor_atual:g}% -> {r['percentual']:g}%")
                ctx.atualizados += 1
            continue

        sb().table("percentuais").insert({
            "cliente_id": cliente_id,
            "cliente_uc_id": uc_id,
            "usina_id": usina_id,
            "percentual": r["percentual"],
            "data_vigencia": r["data_vigencia"],
        }).execute()
        existentes[chave] = (None, r["percentual"])
        ctx.criados += 1

    if ignoradas:
        print(f"\nPuladas (UCs deixadas fora da importação): {', '.join(sorted(ignoradas))}")

    if fora_do_bloco:
        print(f"\n{len(fora_do_bloco)} percentuais estão ABAIXO da linha de Total "
              f"do bloco e NÃO foram importados:")
        for r in fora_do_bloco:
            print(f"  - linha {r['linha']}: {r['numero_uc']} "
                  f"({r['nome_uc']}) {r['usina_prefixo']} "
                  f"{r['data_vigencia']} = {r['percentual']:.0f}%")

    ctx.resumo("Percentuais")


# ------------------------------------------------- LIMPEZA: UCs duplicadas

def limpar_duplicatas(caminho, ctx):
    """
    Remove linhas repetidas em clientes_ucs (mesmo numero_uc no mesmo cliente).
    Só apaga a duplicata que NÃO tem percentual nem fatura ligados a ela.
    Não usa a planilha — o argumento --arquivo é ignorado nesta etapa.
    """
    if ctx.dry_run:
        print("Esta etapa precisa consultar o banco. Rode sem --dry-run "
              "(ela mostra o que vai apagar e só apaga o que for seguro).\n")
        return

    todas = sb().table("clientes_ucs").select(
        "id, cliente_id, numero_uc, numero_uc_novo, nome_uc").execute().data or []

    grupos = {}
    for u in todas:
        grupos.setdefault((u["cliente_id"], u["numero_uc"]), []).append(u)

    duplicadas = {k: v for k, v in grupos.items() if len(v) > 1}
    if not duplicadas:
        print("Nenhuma UC duplicada encontrada.")
        ctx.resumo("Limpeza")
        return

    print(f"{len(duplicadas)} UC(s) com linha repetida:\n")

    for (cliente_id, numero), linhas in duplicadas.items():
        print(f"UC {numero} (cliente {cliente_id}) — {len(linhas)} linhas: "
              f"ids {', '.join(str(l['id']) for l in linhas)}")

        # quantas referências cada linha tem
        peso = {}
        for l in linhas:
            n_perc = len(sb().table("percentuais").select("id")
                         .eq("cliente_uc_id", l["id"]).execute().data or [])
            n_fat = len(sb().table("faturas").select("id")
                        .eq("cliente_uc_id", l["id"]).execute().data or [])
            completa = 1 if l.get("numero_uc_novo") else 0
            peso[l["id"]] = (n_perc + n_fat, completa)
            print(f"   id={l['id']}: {n_perc} percentuais, {n_fat} faturas"
                  + (", tem numero_uc_novo" if completa else ""))

        # fica a linha com mais referências; empate, a que tem numero_uc_novo
        manter = max(linhas, key=lambda l: peso[l["id"]])
        print(f"   -> mantendo id={manter['id']}")

        for l in linhas:
            if l["id"] == manter["id"]:
                continue
            refs, _ = peso[l["id"]]
            if refs > 0:
                ctx.erro(f"UC {numero}: id={l['id']} tem {refs} registro(s) "
                         f"ligados e NÃO foi apagada — resolva na mão")
                continue
            sb().table("clientes_ucs").delete().eq("id", l["id"]).execute()
            print(f"   -> apagada id={l['id']}")
            ctx.atualizados += 1
        print()

    ctx.resumo("Limpeza")


# ---------------------------------------------------------------- ETAPA 4: faturas

MESES = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8, "setembro": 9,
    "outubro": 10, "novembro": 11, "dezembro": 12,
}

# Na aba FATURAS cada mês ocupa 5 colunas seguidas, sempre nesta ordem.
COLUNAS_MES = ["leitura_inicial", "leitura_final", "consumo_kwh",
               "kwh_injetado", "saldo_kwh"]


def ler_faturas_leituras(caminho, ano):
    """
    Aba FATURAS: para cada UC e cada mês, lê inicial/final/consumo/injetado/saldo.
    Devolve {(numero_uc, 'AAAA-MM-01'): {campos}}.
    """
    wb = openpyxl.load_workbook(caminho, data_only=True)
    ws = wb["FATURAS"]
    dados = {}
    usina_atual = None
    meses = {}      # {coluna inicial: 'AAAA-MM-01'}
    fechado = False

    for linha in range(1, ws.max_row + 1):
        b = texto(ws.cell(linha, 2).value)
        c = texto(ws.cell(linha, 3).value)

        if b and prefixo_usina(b):
            usina_atual = prefixo_usina(b)
            fechado = False
            continue
        if c and c.lower().startswith("desativado"):
            fechado = False
            continue

        # linha de cabeçalho: os nomes dos meses estão duas linhas acima
        if b and b.strip().lower() == "item":
            meses = {}
            for col in range(7, ws.max_column + 1):
                nome = texto(ws.cell(linha - 2, col).value)
                if nome and nome.strip().lower() in MESES:
                    meses[col] = f"{ano}-{MESES[nome.strip().lower()]:02d}-01"
            continue

        rotulo_f = texto(ws.cell(linha, 6).value)
        if rotulo_f and rotulo_f.strip().lower() == "total":
            fechado = True
            continue
        if not rotulo_f or not RE_NUMERO_UC.match(rotulo_f) or fechado or not meses:
            continue

        numero = CORRIGE_UC_DIGITACAO.get(rotulo_f.strip(), rotulo_f.strip())
        numero = TROCAS_UC.get(numero, numero)

        for col, mes in meses.items():
            valores = {}
            for i, campo in enumerate(COLUNAS_MES):
                valores[campo] = num(ws.cell(linha, col + i).value)
            if all(v is None for v in valores.values()):
                continue  # mês ainda não preenchido
            if valores["leitura_final"] is None:
                # mês ainda não fechado: a planilha arrasta a leitura inicial e
                # a fórmula do consumo devolve lixo (negativo). Não é fatura.
                continue
            valores["usina_prefixo"] = usina_atual
            valores["nome_uc"] = c
            dados[(numero, mes)] = valores

    return dados


def ler_faturas_valores(caminho, por_nome=None):
    """
    Aba RGD: por UC e mês, o injetado e o valor cobrado. Também o valor do kWh
    do cliente (coluna E). Devolve ({(numero_uc, mes): {...}}, resgatadas).

    Algumas linhas têm o número da UC quebrado (#ERROR! na fórmula). Nesses
    casos o número é resolvido pelo nome da UC, usando o mapa `por_nome`
    montado a partir da aba FATURAS.
    """
    por_nome = por_nome or {}
    wb = openpyxl.load_workbook(caminho, data_only=True)
    ws = wb["RGD"]
    dados = {}
    resgatadas = []
    meses = {}
    fechado = False

    for linha in range(1, ws.max_row + 1):
        b = texto(ws.cell(linha, 2).value)
        c = texto(ws.cell(linha, 3).value)
        d = texto(ws.cell(linha, 4).value)

        if b and prefixo_usina(b):
            meses = {}
            for col in range(6, ws.max_column + 1):
                m = para_data(ws.cell(linha, col).value)
                if m:
                    meses[col] = m
            fechado = False
            continue

        if b and b.strip().lower() == "item":
            continue
        if d and d.strip().lower() == "total":
            fechado = True
            continue
        if fechado or not meses:
            continue

        if d and RE_NUMERO_UC.match(d):
            bruto = d.strip()
        elif c and c.strip() in por_nome:
            bruto = por_nome[c.strip()]
            resgatadas.append((c.strip(), bruto, linha))
        else:
            continue

        numero = CORRIGE_UC_DIGITACAO.get(bruto, bruto)
        numero = TROCAS_UC.get(numero, numero)
        valor_kwh = num(ws.cell(linha, 5).value)

        for col, mes in meses.items():
            inj = num(ws.cell(linha, col).value)
            valor = num(ws.cell(linha, col + 1).value)
            if not inj and not valor:
                continue
            dados[(numero, mes)] = {
                "kwh_injetado": inj,
                "valor_total": valor,
                "valor_kwh_aplicado": valor_kwh,
            }

    return dados, resgatadas


def importar_faturas(caminho, ctx, ano=2026, ate_mes=None):
    # Mês futuro nunca vira fatura: a planilha às vezes tem número digitado
    # numa coluna à frente. Por padrão o limite é o mês corrente.
    if ate_mes is None:
        hoje = date.today()
        ate_mes = f"{hoje.year}-{hoje.month:02d}-01"

    leituras = ler_faturas_leituras(caminho, ano)
    por_nome = {}
    for (numero, _mes), v in leituras.items():
        if v.get("nome_uc"):
            por_nome.setdefault(v["nome_uc"].strip(), numero)
    valores, resgatadas = ler_faturas_valores(caminho, por_nome)
    mapa_usinas = resolver_usinas(ctx)

    if resgatadas:
        vistos = {(nome, numero) for nome, numero, _l in resgatadas}
        print("Aviso: número da UC quebrado na aba RGD, resolvido pelo nome:")
        for nome, numero in sorted(vistos):
            print(f"  - linha da RGD com '{nome}' -> {numero}")
        print()

    futuras = sorted(k for k in set(leituras) | set(valores) if k[1] > ate_mes)
    if futuras:
        print(f"Descartadas {len(futuras)} linha(s) de mês posterior a "
              f"{ate_mes[:7]} (mês futuro não vira fatura):")
        for numero, mes in futuras:
            nome = (leituras.get((numero, mes), {}) or {}).get("nome_uc") or ""
            print(f"  - {mes[:7]} {numero} {nome}")
        print()
        for k in futuras:
            leituras.pop(k, None)
            valores.pop(k, None)

    chaves = sorted(set(leituras) | set(valores), key=lambda k: (k[1], k[0]))
    meses = sorted({m for _, m in chaves})
    print(f"\n{len(chaves)} faturas em {len(meses)} meses "
          f"({meses[0]} a {meses[-1]}).\n")

    so_leitura = sorted(set(leituras) - set(valores))
    so_valor = sorted(set(valores) - set(leituras))
    if so_leitura:
        print(f"Aviso: {len(so_leitura)} faturas têm leitura em FATURAS mas não "
              f"têm valor em RGD (entram sem valor).")
    if so_valor:
        print(f"Aviso: {len(so_valor)} faturas têm valor em RGD mas não têm "
              f"leitura em FATURAS.")
    if so_leitura or so_valor:
        print()

    if not ctx.dry_run:
        ucs_banco = {}
        for u in sb().table("clientes_ucs").select(
                "id, cliente_id, numero_uc, numero_uc_novo, dia_leitura").execute().data or []:
            info = (u["id"], u["cliente_id"], u.get("dia_leitura"))
            ucs_banco[u["numero_uc"]] = info
            if u.get("numero_uc_novo"):
                ucs_banco.setdefault(u["numero_uc_novo"], info)

        existentes = {}
        for f in sb().table("faturas").select(
                "id, cliente_uc_id, mes_referencia").execute().data or []:
            existentes[(f["cliente_uc_id"], f["mes_referencia"])] = f["id"]
    else:
        ucs_banco, existentes = {}, {}

    ignoradas = set()
    for numero, mes in chaves:
        if numero in UCS_FORA_DA_IMPORTACAO or numero in UCS_ENCERRADAS:
            ignoradas.add(numero)
            continue

        base = dict(leituras.get((numero, mes), {}))
        extra = valores.get((numero, mes), {})
        usina_prefixo = base.pop("usina_prefixo", None)
        nome_uc = base.pop("nome_uc", None)

        # o injetado aparece nas duas abas; RGD é a fonte do valor cobrado
        registro = {k: v for k, v in base.items() if v is not None}
        for k, v in extra.items():
            if v is not None:
                registro[k] = v
        if registro.get("valor_total") is not None:
            registro["valor_final"] = registro["valor_total"]
        registro["mes_referencia"] = mes

        if ctx.dry_run:
            ctx.log(f"{mes} {numero} ({nome_uc}) — consumo "
                    f"{registro.get('consumo_kwh')}, injetado "
                    f"{registro.get('kwh_injetado')}, R$ {registro.get('valor_total')}")
            ctx.criados += 1
            continue

        achado = ucs_banco.get(numero)
        if achado is None:
            ctx.erro(f"UC {numero} ('{nome_uc}') não está cadastrada — "
                     f"rode a etapa clientes antes")
            continue
        uc_id, cliente_id, _dia = achado

        registro["cliente_id"] = cliente_id
        registro["cliente_uc_id"] = uc_id

        chave = (uc_id, mes)
        if chave in existentes:
            sb().table("faturas").update(registro).eq("id", existentes[chave]).execute()
            ctx.atualizados += 1
        else:
            sb().table("faturas").insert(registro).execute()
            ctx.criados += 1

    if ignoradas:
        print(f"\nPuladas (UCs fora da importação): {', '.join(sorted(ignoradas))}")

    ctx.resumo("Faturas")


# ---------------------------------------------------------------- ETAPA 5: produção diária

# A planilha de produção diária tem uma aba por mês. Em cada uma:
#   - uma linha com as datas (a partir da coluna G)
#   - blocos por conjunto: a coluna B traz "Conjunto N - ...", e abaixo uma
#     linha por inversor com a marca na coluna E e a potência em kWp na F
#   - linhas "Reserva", "sub-total" e "Ano 20XX" que não são inversores
# Os anos nos cabeçalhos estão inconsistentes (misturam 2025 e 2026), então o
# ano vem do parâmetro e só o dia é lido da célula.
ABAS_PRODUCAO = {
    "Jan": 1, "Fev": 2, "Mar": 3, "Abr": 4,
    "Maio": 5, "Junho": 6, "Julho": 7, "Agosto": 8,
    "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12,
}
PRIMEIRA_COLUNA_DIA = 7  # coluna G
RE_CONJUNTO = re.compile(r"Conjunto\s*(\d+)", re.IGNORECASE)
NAO_INVERSOR = ("reserva", "sub-total", "subtotal", "total")


def ler_producao(caminho, ano):
    """Devolve [{usina_prefixo, marca, potencia_kwp, data, producao_kwh}]."""
    wb = openpyxl.load_workbook(caminho, data_only=True)
    registros = []
    quebrados = 0

    for aba, mes in ABAS_PRODUCAO.items():
        if aba not in wb.sheetnames:
            continue
        ws = wb[aba]

        # linha das datas: a que tem mais células de data
        melhor = (0, None)
        for linha in range(1, 11):
            n = sum(1 for col in range(PRIMEIRA_COLUNA_DIA, ws.max_column + 1)
                    if hasattr(ws.cell(linha, col).value, "year"))
            if n > melhor[0]:
                melhor = (n, linha)
        if melhor[1] is None:
            continue

        dias = {}
        for col in range(PRIMEIRA_COLUNA_DIA, ws.max_column + 1):
            v = ws.cell(melhor[1], col).value
            if hasattr(v, "year"):
                dias[col] = f"{ano}-{mes:02d}-{v.day:02d}"

        usina_atual = None
        ocorrencias = {}
        for linha in range(melhor[1] + 1, ws.max_row + 1):
            b = texto(ws.cell(linha, 2).value)
            if b:
                m = RE_CONJUNTO.search(b)
                if m:
                    usina_atual = f"USINA {int(m.group(1)):02d}"

            marca_raw = texto(ws.cell(linha, 5).value)
            potencia = num(ws.cell(linha, 6).value)
            if not marca_raw or potencia is None or not usina_atual:
                continue
            if any(p in marca_raw.lower() for p in NAO_INVERSOR):
                continue
            marca = marca_inversor(marca_raw)
            if marca is None:
                continue

            # a mesma usina pode ter dois inversores iguais (ex.: 2x Solis 15).
            # Guardamos a ordem de aparição para parear com o cadastro.
            chave = (usina_atual, marca, potencia)
            ocorrencia = ocorrencias.get(chave, 0)
            ocorrencias[chave] = ocorrencia + 1

            for col, data in dias.items():
                v = ws.cell(linha, col).value
                if v is None or v == "":
                    continue
                if isinstance(v, str) and ("REF" in v or "ERROR" in v or "#" in v):
                    quebrados += 1
                    continue
                kwh = num(v)
                if kwh is None:
                    continue
                registros.append({
                    "usina_prefixo": usina_atual,
                    "marca": marca,
                    "potencia_kwp": potencia,
                    "ocorrencia": ocorrencia,
                    "data": data,
                    "producao_kwh": kwh,
                })

    return registros, quebrados


def importar_producao(caminho, ctx, ano=2026, ate_mes=None):
    if ate_mes is None:
        hoje = date.today()
        ate_mes = f"{hoje.year}-{hoje.month:02d}"

    registros, quebrados = ler_producao(caminho, ano)
    registros = [r for r in registros if r["data"][:7] <= ate_mes]
    mapa_usinas = resolver_usinas(ctx)

    datas = sorted({r["data"] for r in registros})
    inversores_planilha = sorted({(r["usina_prefixo"], r["marca"], r["potencia_kwp"],
                                   r["ocorrencia"]) for r in registros})
    print(f"\n{len(registros)} registros de produção, "
          f"{len(inversores_planilha)} inversores, "
          f"{len(datas)} dias ({datas[0]} a {datas[-1]}).\n")
    if quebrados:
        print(f"Aviso: {quebrados} células com #REF!/#ERROR! na planilha, ignoradas.\n")

    if ctx.dry_run:
        print("Inversores encontrados na planilha:")
        for usina, marca, pot, ocor in inversores_planilha:
            n = sum(1 for r in registros
                    if (r["usina_prefixo"], r["marca"], r["potencia_kwp"], r["ocorrencia"])
                    == (usina, marca, pot, ocor))
            sufixo = f" (#{ocor + 1})" if any(
                i[:3] == (usina, marca, pot) and i[3] > 0 for i in inversores_planilha) else ""
            print(f"  - {usina} {marca} {pot:g} kWp{sufixo} — {n} dias")
        ctx.criados = len(registros)
        ctx.resumo("Produção")
        return

    # casa cada coluna da planilha com um inversor do banco (usina + marca + kWp)
    banco = {}
    for inv in sorted(
            sb().table("inversores").select("id, usina_id, marca, potencia_kwp, ordem")
            .execute().data or [],
            key=lambda i: (i["usina_id"], i.get("ordem") or 0, i["id"])):
        banco.setdefault(
            (inv["usina_id"], inv["marca"], float(inv["potencia_kwp"])), []
        ).append(inv["id"])

    existentes = set()
    for p in sb().table("producao_diaria").select("inversor_id, data").execute().data or []:
        existentes.add((p["inversor_id"], p["data"]))

    nao_encontrados = set()
    for r in registros:
        usina_id = mapa_usinas.get(r["usina_prefixo"])
        iguais = banco.get((usina_id, r["marca"], r["potencia_kwp"]), [])
        if len(iguais) <= r["ocorrencia"]:
            nao_encontrados.add((r["usina_prefixo"], r["marca"], r["potencia_kwp"],
                                 r["ocorrencia"], len(iguais)))
            continue
        inversor_id = iguais[r["ocorrencia"]]

        if (inversor_id, r["data"]) in existentes:
            ctx.pulados += 1
            continue

        sb().table("producao_diaria").insert({
            "inversor_id": inversor_id,
            "data": r["data"],
            "producao_kwh": r["producao_kwh"],
        }).execute()
        existentes.add((inversor_id, r["data"]))
        ctx.criados += 1

    for usina, marca, pot, ocor, tem in sorted(nao_encontrados):
        ctx.erro(f"{usina}: a planilha tem {ocor + 1} inversor(es) {marca} {pot:g} kWp "
                 f"mas o cadastro tem {tem} — confira o cadastro da usina")

    ctx.resumo("Produção")


def conferir_inversores(caminho, ctx):
    """Lista os inversores do banco lado a lado com os da planilha de produção."""
    if ctx.dry_run:
        print("Esta etapa precisa consultar o banco. Rode sem --dry-run.\n")
        return

    usinas = sb().table("usinas").select("id, nome").order("id").execute().data or []
    invs = sb().table("inversores").select(
        "id, usina_id, marca, potencia_kwp, tipo, ordem").execute().data or []

    print("\n=== INVERSORES CADASTRADOS NO BANCO ===")
    for u in usinas:
        meus = [i for i in invs if i["usina_id"] == u["id"]]
        print(f"\n{u['nome']} (id={u['id']}) — {len(meus)} inversor(es)")
        for i in sorted(meus, key=lambda x: (x.get("ordem") or 0, x["id"])):
            print(f"   id={i['id']} ordem={i.get('ordem')} "
                  f"marca={i['marca']!r} potencia_kwp={i['potencia_kwp']!r} "
                  f"tipo={i.get('tipo')!r}")

    orfaos = [i for i in invs if not any(u["id"] == i["usina_id"] for u in usinas)]
    if orfaos:
        print(f"\n{len(orfaos)} inversor(es) apontando para usina inexistente:")
        for i in orfaos:
            print(f"   id={i['id']} usina_id={i['usina_id']} {i['marca']} {i['potencia_kwp']}")

    try:
        registros, _ = ler_producao(caminho, 2026)
    except Exception as e:
        print(f"\n(não consegui ler a planilha de produção: {e})")
        return

    print("\n=== O QUE A PLANILHA DE PRODUÇÃO ESPERA ===")
    esperados = sorted({(r["usina_prefixo"], r["marca"], r["potencia_kwp"],
                         r["ocorrencia"]) for r in registros})
    for usina, marca, pot, ocor in esperados:
        print(f"   {usina} marca={marca!r} potencia_kwp={pot!r}"
              + (f" (#{ocor + 1})" if ocor else ""))
    print()


def criar_inversores(caminho, ctx):
    """
    Cria no banco os inversores que a planilha de produção usa e que ainda não
    estão cadastrados. Não apaga nem altera nada do que já existe.
    """
    registros, _ = ler_producao(caminho, 2026)
    mapa_usinas = resolver_usinas(ctx)

    # o que a planilha usa, na ordem em que aparece
    esperados = sorted({(r["usina_prefixo"], r["marca"], r["potencia_kwp"],
                         r["ocorrencia"]) for r in registros})

    if ctx.dry_run:
        atuais = {}
    else:
        atuais = {}
        for i in sb().table("inversores").select(
                "id, usina_id, marca, potencia_kwp").execute().data or []:
            atuais.setdefault(
                (i["usina_id"], i["marca"], float(i["potencia_kwp"])), []
            ).append(i["id"])

    sobrando = {k: list(v) for k, v in atuais.items()}
    por_usina = {}
    for usina, marca, pot, ocor in esperados:
        por_usina.setdefault(usina, []).append((marca, pot, ocor))

    for usina in sorted(por_usina):
        usina_id = mapa_usinas.get(usina)
        if not ctx.dry_run and usina_id is None:
            ctx.erro(f"{usina} não existe no banco")
            continue

        print(f"\n{usina}:")
        for ordem, (marca, pot, ocor) in enumerate(por_usina[usina], start=1):
            chave = (usina_id, marca, pot)
            ja_tem = len(atuais.get(chave, []))
            if ja_tem > ocor:
                print(f"   ok      {marca} {pot:g} kWp (já cadastrado)")
                if sobrando.get(chave):
                    sobrando[chave].pop(0)
                ctx.pulados += 1
                continue

            print(f"   CRIAR   {marca} {pot:g} kWp (ordem {ordem})")
            if not ctx.dry_run:
                sb().table("inversores").insert({
                    "usina_id": usina_id,
                    "marca": marca,
                    "potencia_kwp": pot,
                    "tipo": "principal" if ordem == 1 else "secundario",
                    "ordem": ordem,
                }).execute()
                atuais.setdefault(chave, []).append("novo")
            ctx.criados += 1

    nao_usados = [(k, v) for k, v in sobrando.items() if v]
    if nao_usados:
        print("\nCadastrados no banco mas NÃO usados pela planilha de produção "
              "(confira se estão certos antes de apagar):")
        for (usina_id, marca, pot), ids in sorted(nao_usados, key=lambda x: str(x[0])):
            nome = next((u for u, i in mapa_usinas.items() if i == usina_id), usina_id)
            print(f"   {nome} — {marca} {pot:g} kWp (id {', '.join(map(str, ids))})")

    ctx.resumo("Inversores")


def limpar_inversores(caminho, ctx, confirmar=False):
    """
    Remove inversores que a planilha de produção não usa. Por segurança:
    só apaga os que não têm nenhum registro de produção ligado, e só quando
    a flag --confirmar é passada. Sem ela, apenas lista.
    """
    if ctx.dry_run:
        print("Esta etapa precisa consultar o banco. Rode sem --dry-run "
              "(sem --confirmar ela só lista, não apaga).\n")
        return

    registros, _ = ler_producao(caminho, 2026)
    mapa_usinas = resolver_usinas(ctx)
    nome_usina = {v: k for k, v in mapa_usinas.items()}

    # quantos inversores de cada tipo a planilha espera por usina
    esperado = {}
    for r in registros:
        usina_id = mapa_usinas.get(r["usina_prefixo"])
        chave = (usina_id, r["marca"], r["potencia_kwp"])
        esperado[chave] = max(esperado.get(chave, 0), r["ocorrencia"] + 1)

    atuais = {}
    for i in sb().table("inversores").select(
            "id, usina_id, marca, potencia_kwp").execute().data or []:
        atuais.setdefault(
            (i["usina_id"], i["marca"], float(i["potencia_kwp"])), []
        ).append(i["id"])

    candidatos = []
    for chave, ids in atuais.items():
        excedente = ids[esperado.get(chave, 0):]  # os que passam do esperado
        for inv_id in excedente:
            n = len(sb().table("producao_diaria").select("id")
                    .eq("inversor_id", inv_id).execute().data or [])
            candidatos.append((chave, inv_id, n))

    if not candidatos:
        print("Nenhum inversor sobrando.")
        ctx.resumo("Limpeza de inversores")
        return

    print("\nInversores que a planilha de produção NÃO usa:\n")
    for (usina_id, marca, pot), inv_id, n in sorted(candidatos, key=lambda x: x[1]):
        usina = nome_usina.get(usina_id, f"usina_id={usina_id}")
        destino = ("APAGAR" if n == 0 and confirmar else
                   "apagaria" if n == 0 else "MANTER (tem produção)")
        print(f"   id={inv_id:4d} {usina} {marca} {pot:g} kWp — "
              f"{n} registro(s) de produção  ->  {destino}")

    if not confirmar:
        print("\nNada foi apagado. Para apagar os que não têm produção, "
              "repita o comando com --confirmar")
        ctx.resumo("Limpeza de inversores")
        return

    for _chave, inv_id, n in candidatos:
        if n > 0:
            ctx.erro(f"inversor id={inv_id} tem {n} registros de produção "
                     f"e NÃO foi apagado")
            continue
        sb().table("inversores").delete().eq("id", inv_id).execute()
        ctx.atualizados += 1

    ctx.resumo("Limpeza de inversores")


# ---------------------------------------------------------------- CLI

ETAPAS = {
    "usinas": importar_usinas,
    "clientes": importar_clientes,
    "percentuais": importar_percentuais,
    "faturas": importar_faturas,
    "producao": importar_producao,
    "conferir-inversores": conferir_inversores,
    "criar-inversores": criar_inversores,
    "limpar-inversores": limpar_inversores,
    "limpar-duplicatas": limpar_duplicatas,
}


def main():
    p = argparse.ArgumentParser(description="Importa os dados históricos da planilha pro LAC Solar.")
    p.add_argument("--arquivo", required=True, help="Caminho do .xlsx de gerenciamento")
    p.add_argument("--etapa", required=True, choices=list(ETAPAS.keys()))
    p.add_argument("--dry-run", action="store_true", help="Só mostra o que faria, sem gravar")
    p.add_argument("--historico", action="store_true",
                   help="Percentuais: importa também os rateios antigos, "
                        "não só o vigente (coluna I)")
    p.add_argument("--ano", type=int, default=2026,
                   help="Faturas: ano dos meses da aba FATURAS (padrão 2026). "
                        "A aba só traz o nome do mês, sem ano.")
    p.add_argument("--confirmar", action="store_true",
                   help="limpar-inversores: apaga de verdade (sem isso, só lista)")
    p.add_argument("--ate-mes", metavar="AAAA-MM",
                   help="Faturas: ignora meses posteriores a este "
                        "(padrão: mês atual)")
    args = p.parse_args()

    if not os.path.exists(args.arquivo):
        sys.exit(f"Arquivo não encontrado: {args.arquivo}")

    ctx = Ctx(args.dry_run)
    if args.etapa == "percentuais":
        importar_percentuais(args.arquivo, ctx, historico=args.historico)
    elif args.etapa == "faturas":
        limite = f"{args.ate_mes}-01" if args.ate_mes else None
        importar_faturas(args.arquivo, ctx, ano=args.ano, ate_mes=limite)
    elif args.etapa == "producao":
        importar_producao(args.arquivo, ctx, ano=args.ano, ate_mes=args.ate_mes)
    elif args.etapa == "limpar-inversores":
        limpar_inversores(args.arquivo, ctx, confirmar=args.confirmar)
    else:
        ETAPAS[args.etapa](args.arquivo, ctx)

    if ctx.erros:
        print("\nPendências que precisam de decisão sua:")
        for e in ctx.erros:
            print("  - " + e)


if __name__ == "__main__":
    main()