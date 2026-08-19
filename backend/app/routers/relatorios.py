from fastapi import APIRouter, Depends, Query
from app.core.auth import require_permission
from app.core.supabase import get_supabase_admin

router = APIRouter()


@router.get("/rgd")
async def get_rgd(
    ano: int = Query(...),
    usina_id: int = Query(None),
    user: dict = Depends(require_permission("rgd", "visualizar")),
):
    """RGD - Relatorio Gerencial de Desempenho. Consolida por usina, mês a mês."""
    sb = get_supabase_admin()

    query = sb.table("usinas").select("id, nome")
    if usina_id:
        query = query.eq("id", usina_id)
    usinas = query.order("id").execute()

    resultado = []
    for usina in usinas.data or []:
        clientes = (
            sb.table("clientes")
            .select("id, nome, nome_uc, numero_uc")
            .eq("usina_id", usina["id"])
            .eq("activo", True)
            .eq("eh_agregado", False)
            .order("nome")
            .execute()
        )

        cliente_ids = [c["id"] for c in clientes.data or []]
        if not cliente_ids:
            continue

        faturas = (
            sb.table("faturas")
            .select("cliente_id, mes_referencia, kwh_injetado, valor_final, status")
            .in_("cliente_id", cliente_ids)
            .gte("mes_referencia", str(ano) + "-01-01")
            .lte("mes_referencia", str(ano) + "-12-01")
            .execute()
        )

        fatura_map = {}
        for f in faturas.data or []:
            mes = int(f["mes_referencia"].split("-")[1])
            key = (f["cliente_id"], mes)
            fatura_map[key] = f

        clientes_dados = []
        totais_mes = {m: {"kwh": 0, "valor": 0} for m in range(1, 13)}

        for c in clientes.data or []:
            meses = {}
            total_kwh = 0
            total_valor = 0
            for m in range(1, 13):
                f = fatura_map.get((c["id"], m))
                kwh = f["kwh_injetado"] if f and f.get("kwh_injetado") else 0
                valor = f["valor_final"] if f and f.get("valor_final") else 0
                meses[m] = {"kwh": kwh, "valor": valor}
                total_kwh += kwh
                total_valor += valor
                totais_mes[m]["kwh"] += kwh
                totais_mes[m]["valor"] += valor

            clientes_dados.append({
                "cliente_id": c["id"],
                "nome": c["nome"],
                "nome_uc": c["nome_uc"],
                "numero_uc": c["numero_uc"],
                "meses": meses,
                "total_kwh": total_kwh,
                "total_valor": total_valor,
            })

        resultado.append({
            "usina_id": usina["id"],
            "usina_nome": usina["nome"],
            "clientes": clientes_dados,
            "totais_mes": totais_mes,
        })

    return resultado


@router.get("/saldo-acm")
async def get_saldo_acumulado(
    ano: int = Query(...),
    usina_id: int = Query(None),
    user: dict = Depends(require_permission("saldo_acm", "visualizar")),
):
    """Saldo Acumulado - historico de creditos de cada UC mês a mês."""
    sb = get_supabase_admin()

    query = sb.table("clientes").select("id, nome, nome_uc, numero_uc, usina_id, usinas(nome)")
    if usina_id:
        query = query.eq("usina_id", usina_id)
    clientes = query.eq("activo", True).order("nome").execute()

    resultado = []
    for c in clientes.data or []:
        faturas = (
            sb.table("faturas")
            .select("mes_referencia, saldo_kwh")
            .eq("cliente_id", c["id"])
            .gte("mes_referencia", str(ano) + "-01-01")
            .lte("mes_referencia", str(ano) + "-12-01")
            .order("mes_referencia")
            .execute()
        )

        meses = {}
        for m in range(1, 13):
            meses[m] = None

        for f in faturas.data or []:
            mes = int(f["mes_referencia"].split("-")[1])
            meses[mes] = f["saldo_kwh"]

        resultado.append({
            "cliente_id": c["id"],
            "nome": c["nome"],
            "nome_uc": c["nome_uc"],
            "numero_uc": c["numero_uc"],
            "usina_nome": c.get("usinas", {}).get("nome", ""),
            "meses": meses,
        })

    return resultado


@router.get("/dre")
async def get_dre(
    ano: int = Query(...),
    user: dict = Depends(require_permission("dre", "visualizar")),
):
    """DRE - Demonstrativo de Resultado do Exercicio."""
    sb = get_supabase_admin()

    resultado = {m: {} for m in range(1, 13)}

    for mes in range(1, 13):
        mes_ref = str(ano) + "-" + str(mes).zfill(2) + "-01"

        # A - Receita Bruta (soma de todas as faturas pagas/pendentes)
        faturas = (
            sb.table("faturas")
            .select("valor_final, cliente_id")
            .eq("mes_referencia", mes_ref)
            .execute()
        )

        # Separar agregados
        agregados_result = (
            sb.table("clientes")
            .select("id")
            .eq("eh_agregado", True)
            .execute()
        )
        agregado_ids = {a["id"] for a in agregados_result.data or []}

        receita_bruta = 0
        valor_agregados = 0
        for f in faturas.data or []:
            valor = f.get("valor_final") or 0
            if f["cliente_id"] in agregado_ids:
                valor_agregados += valor
            else:
                receita_bruta += valor

        # E - Despesas Operacionais
        despesas = (
            sb.table("despesas")
            .select("categoria, subcategoria, valor_mensal")
            .eq("mes_referencia", mes_ref)
            .execute()
        )
        total_despesas = sum(d["valor_mensal"] for d in despesas.data or [])

        despesas_por_categoria = {}
        for d in despesas.data or []:
            cat = d["categoria"]
            if cat not in despesas_por_categoria:
                despesas_por_categoria[cat] = 0
            despesas_por_categoria[cat] += d["valor_mensal"]

        # F - Financiamentos
        financiamentos = (
            sb.table("financiamentos")
            .select("nome, valor_mensal")
            .eq("mes_referencia", mes_ref)
            .execute()
        )
        total_financiamentos = sum(f["valor_mensal"] for f in financiamentos.data or [])

        # Calculos
        receita_operacional = receita_bruta - valor_agregados
        resultado_operacional = receita_operacional - total_despesas - total_financiamentos

        resultado[mes] = {
            "receita_bruta": round(receita_bruta, 2),
            "agregados": round(valor_agregados, 2),
            "receita_operacional": round(receita_operacional, 2),
            "despesas": round(total_despesas, 2),
            "despesas_por_categoria": despesas_por_categoria,
            "financiamentos": round(total_financiamentos, 2),
            "resultado_operacional": round(resultado_operacional, 2),
        }

    return resultado