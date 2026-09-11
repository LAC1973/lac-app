import os
# pyrefly: ignore [missing-import]
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, users, usinas, inversores, clientes, percentuais, producao, faturas, exportar, leituras, recibos, placas, documentos, energisa, relatorios, despesas, financiamentos, dashboard, configuracoes
app = FastAPI(
    title="LAC Solar API",
    version="1.0.0",
    description="API do sistema de gestão LAC Solar",
)

# Domínios liberados: localhost para dev + os da variável CORS_ORIGINS
# (separados por vírgula) em produção.
origins = ["http://localhost:5173", "http://localhost:3000"]
extra = os.getenv("CORS_ORIGINS", "")
if extra:
    origins += [o.strip() for o in extra.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(users.router, prefix="/api/users", tags=["Usuários"])

app.include_router(usinas.router, prefix="/api/usinas", tags=["Usinas"])
app.include_router(inversores.router, prefix="/api/inversores", tags=["Inversores"])

app.include_router(clientes.router, prefix="/api/clientes", tags=["Clientes"])
app.include_router(percentuais.router, prefix="/api/percentuais", tags=["Percentuais"])

app.include_router(producao.router, prefix="/api/producao", tags=["Produção"])
app.include_router(faturas.router, prefix="/api/faturas", tags=["Faturas"])

app.include_router(exportar.router, prefix="/api/exportar", tags=["Exportar"])
app.include_router(leituras.router, prefix="/api/leituras", tags=["Leituras"])

app.include_router(recibos.router, prefix="/api/recibos", tags=["Recibos"])
app.include_router(placas.router, prefix="/api/placas", tags=["Placas"])

app.include_router(documentos.router, prefix="/api/documentos", tags=["Documentos"])
app.include_router(energisa.router, prefix="/api/energisa", tags=["Energisa"])

app.include_router(relatorios.router, prefix="/api/relatorios", tags=["Relatorios"])
app.include_router(despesas.router, prefix="/api/despesas", tags=["Despesas"])
app.include_router(financiamentos.router, prefix="/api/financiamentos", tags=["Financiamentos"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(configuracoes.router, prefix="/api/configuracoes", tags=["Configuracoes"])

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "LAC Solar API"}