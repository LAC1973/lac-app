import os
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
ADMIN_NAME = os.getenv("ADMIN_NAME")
ADMIN_PHONE = os.getenv("ADMIN_PHONE")

if not ADMIN_EMAIL or not ADMIN_PASSWORD:
    print("Defina ADMIN_EMAIL e ADMIN_PASSWORD no ambiente (ou no .env) antes de rodar este script.")
    sys.exit(1)

print(f"Criando admin: {ADMIN_EMAIL}")

try:
    auth_result = sb.auth.admin.create_user({
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD,
        "email_confirm": True,
    })
    user_id = str(auth_result.user.id)
    print(f"Auth user criado: {user_id}")
except Exception as e:
    print(f"Erro: {e}")
    exit()

sb.table("profiles").insert({
    "id": user_id,
    "full_name": ADMIN_NAME,
    "email": ADMIN_EMAIL,
    "phone": ADMIN_PHONE,
    "is_admin": True,
    "activo": True,
}).execute()

print()
print("=" * 40)
print("Admin criado com sucesso!")
print(f"  Email: {ADMIN_EMAIL}")
print("=" * 40)