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
    """RGD - por usina, lista cada UC com kWh injetado e valor, mes a mes."""
    sb = get_supabase_admin()

    query = sb.table("usinas").select("id, nome")
    if usina_id:
        query = query.eq("id", usina_id)
    usinas = query.order("id").execute()

    resultado = []
    for usina in usinas.data or []:
        ucs = (
            sb.table("clientes_ucs")
            .select("id, nome_uc, numero_uc, item, cliente_id, clientes(nome, valor_kwh, eh_agregado)")
            .eq("usina_id", usina["id"])
            .eq("activo", True)
            .order("item")
            .execute()
        )

        ucs_dados = []
        totais_mes = {m: {"kwh": 0, "valor": 0} for m in range(1, 13)}

        for uc in ucs.data or []:
            cliente = uc.get("clientes") or {}
            if cliente.get("eh_agregado"):
                continue

            faturas = (
                sb.table("faturas")
                .select("mes_referencia, kwh_injetado, valor_final")
                .eq("cliente_uc_id", uc["id"])
                .gte("mes_referencia", str(ano) + "-01-01")
                .lte("mes_referencia", str(ano) + "-12-01")
                .execute()
            )

            meses = {}
            total_kwh = 0
            total_valor = 0
            for m in range(1, 13):
                meses[m] = {"kwh": 0, "valor": 0}

            for f in faturas.data or []:
                mes = int(f["mes_referencia"].split("-")[1])
                kwh = f.get("kwh_injetado") or 0
                valor = f.get("valor_final") or 0
                meses[mes] = {"kwh": kwh, "valor": valor}
                total_kwh += kwh
                total_valor += valor
                totais_mes[mes]["kwh"] += kwh
                totais_mes[mes]["valor"] += valor

            ucs_dados.append({
                "uc_id": uc["id"],
                "cliente_id": uc["cliente_id"],
                "nome": cliente.get("nome", ""),
                "nome_uc": uc.get("nome_uc", ""),
                "numero_uc": uc.get("numero_uc", ""),
                "item": uc.get("item"),
                "valor_kwh": cliente.get("valor_kwh", 0),
                "meses": meses,
                "total_kwh": total_kwh,
                "total_valor": total_valor,
            })

        if ucs_dados:
            resultado.append({
                "usina_id": usina["id"],
                "usina_nome": usina["nome"],
                "clientes": ucs_dados,
                "totais_mes": totais_mes,
            })

    return resultado

@router.get("/saldo-acm")
async def get_saldo_acumulado(
    ano: int = Query(...),
    usina_id: int = Query(None),
    user: dict = Depends(require_permission("saldo_acm", "visualizar")),
):
    """Saldo Acumulado - historico de creditos por UC, mes a mes."""
    sb = get_supabase_admin()

    query = sb.table("clientes_ucs").select("id, nome_uc, numero_uc, item, usina_id, cliente_id, clientes(nome), usinas(nome)")
    if usina_id:
        query = query.eq("usina_id", usina_id)
    ucs = query.eq("activo", True).order("item").execute()

    resultado = []
    for uc in ucs.data or []:
        faturas = (
            sb.table("faturas")
            .select("mes_referencia, saldo_kwh")
            .eq("cliente_uc_id", uc["id"])
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
            "uc_id": uc["id"],
            "cliente_id": uc["cliente_id"],
            "nome": uc.get("clientes", {}).get("nome", ""),
            "nome_uc": uc.get("nome_uc", ""),
            "numero_uc": uc.get("numero_uc", ""),
            "item": uc.get("item"),
            "usina_nome": uc.get("usinas", {}).get("nome", ""),
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