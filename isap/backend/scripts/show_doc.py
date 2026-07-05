"""Show generated document content."""
import asyncio
import logging
import sys

logging.disable(logging.CRITICAL)

from uuid import UUID
from src.infrastructure.database.engine import async_session_factory
from src.infrastructure.database.models import DocumentModel
from sqlalchemy import select


async def main():
    doc_id = sys.argv[1] if len(sys.argv) > 1 else "72f5bee6-79a1-4bfb-aca8-64409f240304"
    async with async_session_factory() as session:
        result = await session.execute(
            select(DocumentModel).where(DocumentModel.id == UUID(doc_id))
        )
        doc = result.scalar_one()
        if not doc or not doc.content_docx:
            print("No content")
            return

        import docx, io
        d = docx.Document(io.BytesIO(doc.content_docx))
        for para in d.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            style = para.style.name if para.style else ""
            if "Heading" in style:
                level = style.replace("Heading ", "")
                prefix = "##" if level == "1" else "###" if level == "2" else "#"
                print(f"\n{prefix} {text}")
            else:
                print(text)


asyncio.run(main())
