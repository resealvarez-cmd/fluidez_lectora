import asyncio
import asyncpg
import os

async def test_conn():
    # Intento con el formato oficial de Supabase
    dsn = "postgresql://postgres.chzxsaxeshipenvhsgoy:Renesebastian030818@aws-0-us-east-2.pooler.supabase.com:6543/postgres?sslmode=require"
    print(f"Probando DSN: {dsn}")
    try:
        conn = await asyncpg.connect(dsn)
        print("✅ Conexión exitosa con asyncpg!")
        await conn.close()
    except Exception as e:
        print(f"❌ Falló conexión: {e}")

if __name__ == "__main__":
    asyncio.run(test_conn())
