import asyncio
from database import AsyncSessionLocal
from group_model import WhatsAppGroup
from sqlalchemy import select

async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(WhatsAppGroup))
        groups = result.scalars().all()
        for g in groups:
            print(f"id={g.id} | group_id={g.group_id} | name={g.group_name} | enabled={g.enabled}")

asyncio.run(main())