from fastapi import APIRouter, Depends
from app.core.auth import require_permission
from app.core.supabase import get_supabase_admin
from datetime import date, timedelta

router = APIRouter()


@router.get("/")
async def get_dashboard(
    user: dict = Depends(require_permission("dashboard", "visualizar")),
):
    """Resumo do painel administrativo: contas a receber, vencimentos, receita,
    resultado do mês e alertas operacionais (produção e percentuais)."""
    sb = get_supabase_admin()

    hoje = date.today()
    ano, mes = hoje.year, hoje.month

    primeiro_dia_mes = f"{ano}-{mes:02d}-01"
    ultimo_dia_mes = f"{ano + 1}-01-01" if mes == 12 else f"{ano}-{mes + 1:02d}-01"

    ano_ant, mes_ant = (ano - 1, 12) if mes == 1 else (ano, mes - 1)
    primeiro_dia_mes_ant = f"{ano_ant}-{mes_ant:02d}-01"

    # 1) Contas a receber (faturas pendentes/atrasadas)
    contas = (
        sb.table("faturas")
        .select("valor_final")
        .in_("status", ["pendente", "atrasada"])
        .execute()
    )
    contas_a_receber = {
        "quantidade": len(contas.data or []),
        "valor_total": round(sum(f.get("valor_final") or 0 for f in contas.data or []), 2),
    }

    # 2) Proximos vencimentos (7 dias, faturas ainda nao pagas)
    limite = hoje + timedelta(days=7)
    venc = (
        sb.table("faturas")
        .select("id, valor_final, data_vencimento, clientes(nome)")
        .neq("status", "paga")
        .gte("data_vencimento", str(hoje))
        .lte("data_vencimento", str(limite))
        .order("data_vencimento")
        .execute()
    )
    proximos_vencimentos = [
        {
            "fatura_id": f["id"],
            "cliente_nome": (f.get("clientes") or {}).get("nome"),
            "valor_final": f.get("valor_final"),
            "data_vencimento": f["data_vencimento"],
        }
        for f in venc.data or []
    ]

    # Clientes agregados (excluidos da receita, igual ao DRE)
    agregados_result = sb.table("clientes").select("id").eq("eh_agregado", True).execute()
    agregado_ids = {a["id"] for a in agregados_result.data or []}

    # 3) Receita do mes atual vs mes anterior
    faturas_2meses = (
        sb.table("faturas")
        .select("valor_final, cliente_id, mes_referencia")
        .gte("mes_referencia", primeiro_dia_mes_ant)
        .lt("mes_referencia", ultimo_dia_mes)
        .execute()
    )
    receita_mes_atual = 0
    receita_mes_anterior = 0
    for f in faturas_2meses.data or []:
        if f["cliente_id"] in agregado_ids:
            continue
        valor = f.get("valor_final") or 0
        if f["mes_referencia"] == primeiro_dia_mes:
            receita_mes_atual += valor
        elif f["mes_referencia"] == primeiro_dia_mes_ant:
            receita_mes_anterior += valor

    variacao_pct = (
        round((receita_mes_atual - receita_mes_anterior) / receita_mes_anterior * 100, 1)
        if receita_mes_anterior
        else None
    )

    # 4) Resultado operacional do mes atual (mesma formula do DRE, so o mes corrente)
    despesas_mes = sb.table("despesas").select("valor_mensal").eq("mes_referencia", primeiro_dia_mes).execute()
    total_despesas = sum(d["valor_mensal"] for d in despesas_mes.data or [])

    financiamentos_mes = sb.table("financiamentos").select("valor_mensal").eq("mes_referencia", primeiro_dia_mes).execute()
    total_financiamentos = sum(f["valor_mensal"] for f in financiamentos_mes.data or [])

    resultado_mes_atual = {
        "receita": round(receita_mes_atual, 2),
        "despesas": round(total_despesas, 2),
        "financiamentos": round(total_financiamentos, 2),
        "resultado_operacional": round(receita_mes_atual - total_despesas - total_financiamentos, 2),
    }

    # 5) Usinas sem producao lancada no mes + producao total do mes vs mes anterior (kWh)
    usinas = sb.table("usinas").select("id, nome, inversores(id)").execute()
    todos_inversor_ids = [inv["id"] for u in usinas.data or [] for inv in u.get("inversores", [])]

    inversores_com_producao = set()
    producao_mes_atual_kwh = 0
    producao_mes_anterior_kwh = 0
    if todos_inversor_ids:
        producao = (
            sb.table("producao_diaria")
            .select("inversor_id, data, producao_kwh")
            .in_("inversor_id", todos_inversor_ids)
            .gte("data", primeiro_dia_mes_ant)
            .lt("data", ultimo_dia_mes)
            .execute()
        )
        for r in producao.data or []:
            kwh = r.get("producao_kwh") or 0
            if r["data"] >= primeiro_dia_mes:
                producao_mes_atual_kwh += kwh
                inversores_com_producao.add(r["inversor_id"])
            else:
                producao_mes_anterior_kwh += kwh

    producao_variacao_pct = (
        round((producao_mes_atual_kwh - producao_mes_anterior_kwh) / producao_mes_anterior_kwh * 100, 1)
        if producao_mes_anterior_kwh
        else None
    )

    usinas_sem_producao = [
        {"usina_id": u["id"], "usina_nome": u["nome"]}
        for u in usinas.data or []
        if u.get("inversores") and not any(
            inv["id"] in inversores_com_producao for inv in u["inversores"]
        )
    ]

    # 6) Percentuais que nao fecham 100% (mesma regra de percentuais.py, aplicada a todas as usinas)
    clientes = (
        sb.table("clientes")
        .select("id, usina_id")
        .eq("activo", True)
        .eq("eh_agregado", False)
        .execute()
    )
    cliente_usina_map = {c["id"]: c["usina_id"] for c in clientes.data or []}

    percentual_map = {}
    if cliente_usina_map:
        percs = (
            sb.table("percentuais")
            .select("cliente_id, usina_id, percentual")
            .in_("cliente_id", list(cliente_usina_map.keys()))
            .order("data_vigencia", desc=True)
            .execute()
        )
        for p in percs.data or []:
            cid = p["cliente_id"]
            if cid in percentual_map:
                continue
            if p["usina_id"] != cliente_usina_map.get(cid):
                continue
            percentual_map[cid] = p["percentual"]

    soma_por_usina = {}
    clientes_por_usina = {}
    for cid, usina_id in cliente_usina_map.items():
        soma_por_usina[usina_id] = soma_por_usina.get(usina_id, 0) + percentual_map.get(cid, 0)
        clientes_por_usina[usina_id] = clientes_por_usina.get(usina_id, 0) + 1

    usina_nomes = {u["id"]: u["nome"] for u in usinas.data or []}
    percentuais_incompletos = [
        {"usina_id": uid, "usina_nome": usina_nomes.get(uid, ""), "soma_percentuais": round(soma, 2)}
        for uid, soma in soma_por_usina.items()
        if clientes_por_usina.get(uid, 0) > 0 and abs(soma - 100) >= 0.01
    ]

    # 7) Contagens gerais (usinas cadastradas, clientes ativos)
    total_clientes_ativos = sb.table("clientes").select("id", count="exact").eq("activo", True).limit(1).execute()

    contagens = {
        "usinas": len(usinas.data or []),
        "clientes_ativos": total_clientes_ativos.count or 0,
    }

    # 8) Economia acumulada dos clientes no ano corrente
    # soma economia_mensal (nao economia_acumulada_ano, que ja e um total por recibo -
    # somar essa coluna direto contaria a mesma economia varias vezes se o cliente
    # tiver recibo em mais de um mes do ano)
    recibos_ano = (
        sb.table("recibos")
        .select("economia_mensal")
        .gte("mes_referencia", f"{ano}-01-01")
        .lte("mes_referencia", f"{ano}-12-01")
        .execute()
    )
    economia_acumulada_ano = round(sum(r.get("economia_mensal") or 0 for r in recibos_ano.data or []), 2)

    return {
        "contas_a_receber": contas_a_receber,
        "proximos_vencimentos": proximos_vencimentos,
        "receita": {
            "mes_atual": round(receita_mes_atual, 2),
            "mes_anterior": round(receita_mes_anterior, 2),
            "variacao_pct": variacao_pct,
        },
        "resultado_mes_atual": resultado_mes_atual,
        "producao": {
            "mes_atual_kwh": round(producao_mes_atual_kwh, 2),
            "mes_anterior_kwh": round(producao_mes_anterior_kwh, 2),
            "variacao_pct": producao_variacao_pct,
        },
        "usinas_sem_producao": usinas_sem_producao,
        "percentuais_incompletos": percentuais_incompletos,
        "contagens": contagens,
        "economia_acumulada_ano": economia_acumulada_ano,
    }
