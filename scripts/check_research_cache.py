import asyncio
import sys
from pathlib import Path

# Setup paths for monorepo
repo_root = Path(__file__).resolve().parent.parent
api_src = repo_root / "apps" / "api" / "src"
sys.path.insert(0, str(api_src))

from sqlalchemy import select
from torii_api.config import get_settings
from torii_api.db.engine import create_engine, create_session_factory
from torii_api.db.models import ScopeResearch, Jurisdiction, VisaCategory, CaseAction
from torii_api.services.research import research_is_usable, RESEARCH_TTL_DAYS

async def check_db():
    settings = get_settings()
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    
    print("=" * 60)
    print("  TORII 30-DAY CORRIDOR RESEARCH CACHE")
    print(f"  Active TTL Window : {RESEARCH_TTL_DAYS} Days")
    print(f"  Database Path     : {settings.database_url}")
    print("=" * 60)
    
    async with session_factory() as session:
        researches = (await session.scalars(select(ScopeResearch))).all()
        print(f"\nTotal Corridors in Database: {len(researches)}")
        
        if not researches:
            print("No corridors researched yet. Start an application to trigger the agent.")
            return

        for r in researches:
            j = await session.get(Jurisdiction, r.jurisdiction_id)
            v = await session.get(VisaCategory, r.visa_category_id)
            usable = research_is_usable(r)
            
            origin = r.origin_country or "ANY"
            dest = j.code if j else str(r.jurisdiction_id)
            category = v.code if v else "general"
            
            print(f"\n[Record #{r.id}] Corridor: {origin} -> {dest} ({category})")
            print(f"  * Status        : {r.status}")
            print(f"  * Researched At : {r.researched_at or 'Pending'}")
            print(f"  * Expires At    : {r.expires_at or 'Pending'}")
            print(f"  * 30-Day Cache  : {'ACTIVE (Loads instantly from DB)' if usable else 'EXPIRED/PENDING'}")
            
            payload = r.payload or {}
            docs = payload.get("document_requirements", [])
            questions = payload.get("intake_questions", [])
            rules = payload.get("eligibility_rules", [])
            print(f"  * Saved Data    : {len(docs)} documents | {len(questions)} questions | {len(rules)} rules")
            if docs:
                first_doc = docs[0]
                doc_name = first_doc.get("name")
                if isinstance(doc_name, dict):
                    doc_name = doc_name.get("en", str(doc_name))
                print(f"  * Sample Doc    : {first_doc.get('code')} ({doc_name})")
    
    await engine.dispose()
    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(check_db())
