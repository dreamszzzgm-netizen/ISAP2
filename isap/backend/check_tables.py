import asyncio
from sqlalchemy import text
from src.infrastructure.database.engine import async_session_factory

async def check():
    async with async_session_factory() as session:
        tables = ['import_jobs','emergency_services','emergency_rescue_units','pmla_questionnaires','import_rows']
        for t in tables:
            r = await session.execute(text(f"SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='{t}')"))
            print(f'{t}: exists={r.scalar()}')
        
        for t in ['import_jobs','emergency_services','emergency_rescue_units','pmla_questionnaires']:
            try:
                r = await session.execute(text(f'SELECT COUNT(*) FROM {t}'))
                print(f'{t} rows: {r.scalar()}')
            except Exception as e:
                print(f'{t} error: {e}')

asyncio.run(check())
