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

    primeiro_dia_ano = f"{ano}-01-01"
    ultimo_dia_ano = f"{ano}-12-01"

    # Separar agregados (não muda por mês, buscar uma única vez)
    agregados_result = (
        sb.table("clientes")
        .select("id")
        .eq("eh_agregado", True)
        .execute()
    )
    agregado_ids = {a["id"] for a in agregados_result.data or []}

    # A - Receita Bruta (soma de todas as faturas pagas/pendentes) - ano inteiro de uma vez
    faturas_ano = (
        sb.table("faturas")
        .select("valor_final, cliente_id, mes_referencia")
        .gte("mes_referencia", primeiro_dia_ano)
        .lte("mes_referencia", ultimo_dia_ano)
        .execute()
    )
    faturas_por_mes = {m: [] for m in range(1, 13)}
    for f in faturas_ano.data or []:
        faturas_por_mes[int(f["mes_referencia"].split("-")[1])].append(f)

    # E - Despesas Operacionais - ano inteiro de uma vez
    despesas_ano = (
        sb.table("despesas")
        .select("categoria, subcategoria, valor_mensal, mes_referencia")
        .gte("mes_referencia", primeiro_dia_ano)
        .lte("mes_referencia", ultimo_dia_ano)
        .execute()
    )
    despesas_por_mes = {m: [] for m in range(1, 13)}
    for d in despesas_ano.data or []:
        despesas_por_mes[int(d["mes_referencia"].split("-")[1])].append(d)

    # F - Financiamentos - ano inteiro de uma vez
    financiamentos_ano = (
        sb.table("financiamentos")
        .select("nome, valor_mensal, mes_referencia")
        .gte("mes_referencia", primeiro_dia_ano)
        .lte("mes_referencia", ultimo_dia_ano)
        .execute()
    )
    financiamentos_por_mes = {m: [] for m in range(1, 13)}
    for fin in financiamentos_ano.data or []:
        financiamentos_por_mes[int(fin["mes_referencia"].split("-")[1])].append(fin)

    for mes in range(1, 13):
        receita_bruta = 0
        valor_agregados = 0
        for f in faturas_por_mes[mes]:
            valor = f.get("valor_final") or 0
            if f["cliente_id"] in agregado_ids:
                valor_agregados += valor
            else:
                receita_bruta += valor

        total_despesas = sum(d["valor_mensal"] for d in despesas_por_mes[mes])

        despesas_por_categoria = {}
        for d in despesas_por_mes[mes]:
            cat = d["categoria"]
            if cat not in despesas_por_categoria:
                despesas_por_categoria[cat] = 0
            despesas_por_categoria[cat] += d["valor_mensal"]

        total_financiamentos = sum(f["valor_mensal"] for f in financiamentos_por_mes[mes])

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