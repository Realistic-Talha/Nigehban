"""Seed scam patterns, curated references, and sample claims."""

import asyncio
import json
import uuid
from pathlib import Path

from app.core.database import AsyncSessionLocal
from app.models.claim import Claim
from app.models.curated_reference import CuratedReference
from app.models.scam_pattern import ScamPattern
from app.services.embeddings import embedding_service

SEEDS_DIR = Path(__file__).resolve().parent.parent / "seeds"


async def seed_curated() -> int:
    path = SEEDS_DIR / "curated_references.json"
    if not path.exists():
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    count = 0
    async with AsyncSessionLocal() as session:
        for item in data:
            ref = CuratedReference(
                id=uuid.uuid4(),
                url=item["url"],
                title=item["title"],
                publisher=item.get("publisher"),
                category=item.get("category"),
                keywords=item.get("keywords"),
                description_en=item.get("description_en"),
                description_ur=item.get("description_ur"),
            )
            session.add(ref)
            count += 1
        await session.commit()
    return count


async def seed_scam_patterns() -> int:
    path = SEEDS_DIR / "scam_patterns.json"
    if not path.exists():
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    count = 0
    async with AsyncSessionLocal() as session:
        for item in data:
            embedding = await embedding_service.generate_embedding(item["pattern_text"])
            pattern = ScamPattern(
                id=uuid.uuid4(),
                pattern_text=item["pattern_text"],
                scam_type=item["scam_type"],
                description_en=item.get("description_en"),
                description_ur=item.get("description_ur"),
                embedding=embedding,
                times_reported=item.get("times_reported", 1),
            )
            session.add(pattern)
            count += 1
        await session.commit()
    return count


async def seed_claims() -> int:
    path = SEEDS_DIR / "claims.json"
    if not path.exists():
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    count = 0
    async with AsyncSessionLocal() as session:
        for item in data:
            claim = Claim(
                id=uuid.uuid4(),
                title=item["title"][:512],
                body=item.get("body"),
                category=item.get("category"),
                verdict=item.get("verdict"),
                confidence_score=item.get("confidence_score"),
                explanation_en=item.get("explanation_en"),
                explanation_ur=item.get("explanation_ur"),
                sources=item.get("sources"),
                language=item.get("language", "en"),
            )
            if item.get("body"):
                claim.embedding = await embedding_service.generate_embedding(item["body"])
            session.add(claim)
            count += 1
        await session.commit()
    return count


async def main() -> None:
    c = await seed_curated()
    s = await seed_scam_patterns()
    cl = await seed_claims()
    print(f"Seeded curated={c}, scam_patterns={s}, claims={cl}")


if __name__ == "__main__":
    asyncio.run(main())
