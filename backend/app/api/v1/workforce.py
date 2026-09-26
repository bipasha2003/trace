"""
TRACE - Admin → Workforce API (DEVELOPMENT.md Phase 8 step 2, PROJECT.md §5, §9.1)

One set of routes for every tab — employees, managers, leaves, holidays,
attendance, shifts, departments, designations. The fields of each come from
`app.services.workforce`, which the page reads first (`GET /admin/workforce`).
Admin only.
"""

from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_admin
from app.database import get_db
from app.services import workforce as wf

router = APIRouter(prefix="/admin/workforce", tags=["Workforce"], dependencies=[Depends(require_admin)])


@router.get("", summary="The tabs and their fields")
async def catalogue():
    return wf.catalogue()


@router.get("/{entity}", summary="Every record of one tab")
async def list_records(entity: str, db: AsyncSession = Depends(get_db)):
    return await wf.list_rows(db, entity)


@router.post("/{entity}", status_code=status.HTTP_201_CREATED, summary="Add a record")
async def create_record(entity: str, data: dict, db: AsyncSession = Depends(get_db)):
    row_id = await wf.create_row(db, entity, data)
    await db.commit()
    return {"id": row_id}


@router.put("/{entity}/{row_id}", summary="Edit a record (fields left out are unchanged)")
async def update_record(entity: str, row_id: int, data: dict, db: AsyncSession = Depends(get_db)):
    await wf.update_row(db, entity, row_id, data)
    await db.commit()
    return {"id": row_id}


@router.delete("/{entity}/{row_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a record")
async def delete_record(entity: str, row_id: int, db: AsyncSession = Depends(get_db)):
    await wf.delete_row(db, entity, row_id)
    await db.commit()


@router.get("/{entity}/template", summary="An empty CSV with this tab's columns",
            response_class=Response, responses={200: {"content": {"text/csv": {}}}})
async def csv_template(entity: str):
    return Response(wf.template(entity), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{entity}-template.csv"'})


@router.post("/{entity}/bulk", summary="Bulk upload a CSV — good rows are added, bad rows are reported")
async def bulk_upload(entity: str, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    return await wf.bulk_upload(db, entity, await file.read())
