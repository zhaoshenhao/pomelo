import json
import logging
import os
import re

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies.auth import require_student
from app.models.document import DocumentLibrary
from app.models.study_assignment import StudyAssignment
from app.models.study_material import StudyMaterial
from app.models.user import User
from app.schemas.common import success_response
from app.schemas.study_assignment import (
    StudyAssignmentStartResponse,
    StudyProgressRequest,
)
from app.services.file_service import (
    get_library_directory,
    get_material_file_path,
    read_material_file,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/study-assignments", tags=["study_assignments"])


def _material_char_count(material_id: int, lib_dir: str) -> int:
    try:
        raw = read_material_file(lib_dir, material_id, "manifest.json")
        manifest = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return 0
    total = 0
    for p in manifest.get("pages", []):
        try:
            txt = read_material_file(lib_dir, material_id, p.get("text_file", ""))
            total += len(txt)
        except (OSError, ValueError):
            pass
    return total


@router.get("/my")
async def my_courses(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_student),
):
    materials = (await session.execute(
        select(StudyMaterial).where(StudyMaterial.active).order_by(StudyMaterial.id)
    )).scalars().all()

    if not materials:
        return success_response({"items": []})

    mat_ids = [m.id for m in materials]
    assignments = (await session.execute(
        select(StudyAssignment).where(
            StudyAssignment.material_id.in_(mat_ids),
            StudyAssignment.student_id == current_user.id,
        )
    )).scalars().all()
    assign_map = {a.material_id: a for a in assignments}

    items = []
    for m in materials:
        a = assign_map.get(m.id)
        items.append({
            "material_id": m.id,
            "material_name": m.name,
            "material_description": m.description,
            "document_names": m.document_names,
            "min_minutes": m.min_minutes,
            "active": m.active,
            "read_count": m.read_count,
            "complete_count": m.complete_count,
            "last_study_at": a.last_study_at.isoformat() if a and a.last_study_at else None,
            "total_study_seconds": a.total_study_seconds if a else 0,
            "has_started": bool(a) if a else False,
            "completed": a.status == "completed" if a else False,
            "assignment_id": a.id if a else None,
        })

    return success_response({"items": items})


@router.get("/start")
async def start_study(
    material_id: int = Query(...),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_student),
):
    material = (await session.execute(
        select(StudyMaterial).where(StudyMaterial.id == material_id, StudyMaterial.active)
    )).scalar_one_or_none()
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="课程不存在或未激活")

    assignment = (await session.execute(
        select(StudyAssignment).where(
            StudyAssignment.material_id == material_id,
            StudyAssignment.student_id == current_user.id,
        )
    )).scalar_one_or_none()

    if assignment is None:
        assignment = StudyAssignment(
            material_id=material_id, student_id=current_user.id, status="assigned",
        )
        session.add(assignment)
        await session.commit()
        await session.refresh(assignment)

    assignment.read_count += 1
    material.read_count += 1
    await session.commit()

    lib = (await session.execute(
        select(DocumentLibrary).where(DocumentLibrary.id == material.library_id)
    )).scalar_one_or_none()
    lib_dir = get_library_directory(lib.local_path) if lib else ""

    pages = []
    try:
        raw = read_material_file(lib_dir, material.id, "manifest.json")
        manifest = json.loads(raw)
        for p in manifest.get("pages", []):
            p["title"] = re.sub(r"<[^>]+>", "", p.get("title", "")).strip()
            pages.append(p)
    except (OSError, json.JSONDecodeError):
        pass

    return success_response(StudyAssignmentStartResponse(
        id=assignment.id, material_id=material.id,
        material_name=material.name, material_description=material.description,
        min_minutes=material.min_minutes,
        total_study_seconds=assignment.total_study_seconds,
        completed=assignment.status == "completed",
        pages=pages,
    ))


@router.get("/{assignment_id}/audio/{filename:path}")
async def get_assignment_audio(
    assignment_id: int,
    filename: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_student),
):
    assignment = (await session.execute(
        select(StudyAssignment).where(
            StudyAssignment.id == assignment_id,
            StudyAssignment.student_id == current_user.id,
        )
    )).scalar_one_or_none()
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="未安排此学习资料")

    base = os.path.basename(filename)
    if not base.endswith(".mp3"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持 MP3 格式")

    material = (await session.execute(
        select(StudyMaterial).where(StudyMaterial.id == assignment.material_id)
    )).scalar_one_or_none()
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="学习资料不存在")

    lib = (await session.execute(
        select(DocumentLibrary).where(DocumentLibrary.id == material.library_id)
    )).scalar_one_or_none()
    if lib is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="关联文档库不存在")

    lib_dir = get_library_directory(lib.local_path)
    try:
        filepath = get_material_file_path(lib_dir, material.id, base)
    except (OSError, ValueError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="音频文件不存在")

    if not os.path.isfile(filepath):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="音频文件不存在")

    return FileResponse(filepath, media_type="audio/mpeg")


@router.get("/{assignment_id}/page/{filename:path}")
async def get_page(
    assignment_id: int,
    filename: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_student),
):
    assignment = (await session.execute(
        select(StudyAssignment).where(StudyAssignment.id == assignment_id)
    )).scalar_one_or_none()
    if assignment is None or assignment.student_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="进度记录不存在")

    base = os.path.basename(filename)
    if not base.endswith(".html"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持请求 HTML 页面")

    material = (await session.execute(
        select(StudyMaterial).where(StudyMaterial.id == assignment.material_id)
    )).scalar_one_or_none()
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="学习资料不存在")

    lib = (await session.execute(
        select(DocumentLibrary).where(DocumentLibrary.id == material.library_id)
    )).scalar_one_or_none()
    lib_dir = get_library_directory(lib.local_path)
    try:
        html = read_material_file(lib_dir, material.id, base)
        txt_file = base.replace(".html", ".txt")
        txt = ""
        try:
            txt = read_material_file(lib_dir, material.id, txt_file)
        except OSError:
            pass
        return success_response({"html": html, "text": txt})
    except (OSError, ValueError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="页面不存在")


@router.post("/{assignment_id}/progress")
async def report_progress(
    assignment_id: int,
    request: StudyProgressRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_student),
):
    assignment = (await session.execute(
        select(StudyAssignment).where(StudyAssignment.id == assignment_id)
    )).scalar_one_or_none()
    if assignment is None or assignment.student_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="进度记录不存在")

    assignment.total_study_seconds += request.seconds
    assignment.last_study_at = func.now()
    await session.commit()
    return success_response(None, "已记录")


@router.post("/{assignment_id}/complete")
async def complete_study(
    assignment_id: int,
    request: StudyProgressRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_student),
):
    assignment = (await session.execute(
        select(StudyAssignment).where(StudyAssignment.id == assignment_id)
    )).scalar_one_or_none()
    if assignment is None or assignment.student_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="进度记录不存在")

    assignment.total_study_seconds += request.seconds
    assignment.status = "completed"
    assignment.last_study_at = func.now()
    assignment.complete_count += 1

    material = (await session.execute(
        select(StudyMaterial).where(StudyMaterial.id == assignment.material_id)
    )).scalar_one_or_none()
    if material:
        material.complete_count += 1
    await session.commit()
    return success_response(None, "学习完成")
