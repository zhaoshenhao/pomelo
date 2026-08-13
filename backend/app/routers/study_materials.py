import asyncio
import json
import logging
import os
import re
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.dependencies.auth import require_teacher_or_admin
from app.models.ai_prompt import AIPrompt
from app.models.document import Document, DocumentLibrary
from app.models.study_assignment import StudyAssignment
from app.models.study_material import StudyMaterial
from app.models.user import User, UserRole
from app.schemas.common import success_response
from app.schemas.study_material import (
    ManifestPage,
    StudyMaterialDetailResponse,
    StudyMaterialGenerateRequest,
    StudyMaterialListItem,
    StudyMaterialListResponse,
    StudyMaterialStudentItem,
    StudyMaterialSummaryStats,
    StudyMaterialUpdateRequest,
    VoiceRequest,
)
from app.services.ai_service import generate_study_material
from app.services.file_service import (
    delete_material_dir,
    get_library_directory,
    get_material_file_path,
    read_material_file,
    save_material_file,
)
from app.services.tts_service import synthesize

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/study-materials", tags=["study_materials"])

SHARED_CSS = """*{margin:0;padding:0;box-sizing:border-box}body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",Roboto,"Helvetica Neue",Arial,sans-serif;line-height:1.8;color:#1a1a1a;background:#fff}
.page{max-width:860px;margin:60px auto;padding:0 24px}
h1{font-size:2.4rem;font-weight:800;margin-bottom:1rem;line-height:1.3;color:#111}
h2{font-size:1.8rem;font-weight:700;margin:2rem 0 .8rem;color:#222}
h3{font-size:1.3rem;font-weight:600;margin:1.5rem 0 .6rem;color:#333}
p{margin-bottom:1rem}
ul,ol{margin:.8rem 0 1rem 1.5rem}
li{margin-bottom:.4rem}
strong{font-weight:700}
em{font-style:italic;color:#555}
blockquote{border-left:4px solid #6366f1;padding:1rem 1.2rem;margin:1.2rem 0;background:#f8f7ff;border-radius:0 8px 8px 0;color:#444}
.card{background:#fff;border-radius:12px;padding:1.5rem;margin:1rem 0;box-shadow:0 2px 12px rgba(0,0,0,.06);border:1px solid #f0f0f0;transition:box-shadow .2s,transform .2s}
.card:hover{box-shadow:0 4px 20px rgba(0,0,0,.1);transform:translateY(-2px)}
.highlight{background:linear-gradient(135deg,#eff6ff,#faf5ff);border-left:4px solid #6366f1;padding:1rem 1.2rem;margin:1rem 0;border-radius:0 8px 8px 0}
.callout{background:#fffbeb;border:1px solid #fcd34d;border-radius:10px;padding:1rem 1.2rem;margin:1rem 0;color:#92400e}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1rem;margin:1rem 0}
.badge{display:inline-block;padding:2px 10px;font-size:.8rem;font-weight:600;border-radius:999px;background:#eef2ff;color:#4f46e5}
.stat{text-align:center;padding:1.2rem;background:#f9fafb;border-radius:10px;margin:.5rem 0}
.stat strong{display:block;font-size:1.8rem;color:#4f46e5}
img{max-width:100%;height:auto;border-radius:8px;margin:.5rem 0}
@keyframes fadeUp{from{opacity:0;transform:translateY(24px)}to{opacity:1;transform:translateY(0)}}
@keyframes fadeIn{from{opacity:0}to{opacity:1}}
@keyframes slideInLeft{from{opacity:0;transform:translateX(-30px)}to{opacity:1;transform:translateX(0)}}
@keyframes gradientFlow{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}
.page{animation:fadeUp .6s ease-out}
body.cover{display:flex;align-items:center;justify-content:center;min-height:100vh;text-align:center}
body.cover .page{max-width:600px}
body.cover h1{font-size:3rem;animation:fadeIn .8s ease-out;animation-fill-mode:both}
body.cover .page>:not(h1){animation:fadeUp .6s ease-out;animation-delay:.25s;animation-fill-mode:both}
body.chapter-cover{display:flex;align-items:center;justify-content:center;min-height:80vh;text-align:center}
body.chapter-cover .page{max-width:700px}
body.chapter-cover h2{font-size:2.2rem;border:none;padding:0;animation:slideInLeft .5s ease-out}
body.chapter-cover .page>:not(h2){animation:fadeUp .5s ease-out;animation-delay:.15s;animation-fill-mode:both}
body.end{display:flex;align-items:center;justify-content:center;min-height:100vh;text-align:center}
body.end .page{max-width:600px}
body.end .page>*{animation:fadeUp .5s ease-out;animation-fill-mode:both}
.card{animation:fadeUp .5s ease-out;animation-fill-mode:both}
.card:nth-child(1){animation-delay:0s}
.card:nth-child(2){animation-delay:.08s}
.card:nth-child(3){animation-delay:.16s}
.card:nth-child(4){animation-delay:.24s}
.card:nth-child(5){animation-delay:.32s}
.card:nth-child(6){animation-delay:.40s}
"""


def _render_page_html(title: str, body: str, page_class: str = "page", page_css: str = "") -> str:
    body_class = page_class if page_class != "page" else ""
    extra_style = page_css if page_css else ""
    css = SHARED_CSS + extra_style
    return f'<!DOCTYPE html>\n<html lang="zh-CN">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width,initial-scale=1.0">\n<title>{title}</title>\n<style>\n{css}\n</style>\n</head>\n<body class="{body_class}">\n<div class="page">\n{body}\n</div>\n</body>\n</html>'


def _sanitize_css(css: str) -> str:
    css = re.sub(r"@import\s+[^;]+;?", "", css, flags=re.IGNORECASE)
    css = re.sub(r"url\s*\([^)]*\)", "", css, flags=re.IGNORECASE)
    css = re.sub(r"expression\s*\([^)]*\)", "", css, flags=re.IGNORECASE)
    css = re.sub(r"javascript\s*:", "", css, flags=re.IGNORECASE)
    css = css.replace("<script", "")
    css = css.replace("</script>", "")
    css = css.replace("</style>", "")
    return css


def _strip_html(text: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _coerce_str(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(_coerce_str(v) for v in value)
    return str(value)


def _coerce_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


async def _resolve_names(
    session: AsyncSession,
    library_ids: set[int],
    user_ids: set[int],
) -> tuple[dict[int, str], dict[int, str]]:
    lib_map: dict[int, str] = {}
    user_map: dict[int, str] = {}
    if library_ids:
        libs = await session.execute(
            select(DocumentLibrary.id, DocumentLibrary.name).where(DocumentLibrary.id.in_(library_ids))
        )
        for lid, lname in libs:
            lib_map[lid] = lname
    if user_ids:
        usrs = await session.execute(
            select(User.id, User.username).where(User.id.in_(user_ids))
        )
        for uid, uname in usrs:
            user_map[uid] = uname
    return lib_map, user_map


def _files_for_material(data: dict) -> list[dict]:
    files = []
    seq = 0
    cover = _coerce_dict(data.get("cover"))
    if cover:
        files.append({
            "type": "cover", "chapter": None, "page": None,
            "title": _strip_html(_coerce_str(cover.get("title", ""))),
            "source_key": "cover", "body_key": "description",
            "narration_key": "narration",
            "file": "cover.html", "text_file": "cover.txt",
            "css_class": "cover",
        })
        seq += 1
    for ci, ch in enumerate(data.get("chapters", []), 1):
        ch = _coerce_dict(ch)
        files.append({
            "type": "chapter_cover", "chapter": ci, "page": None,
            "title": _strip_html(_coerce_str(ch.get("title", f"第{ci}章"))),
            "source_key": f"chapters.{ci-1}", "body_key": "summary",
            "narration_key": "narration",
            "file": f"chapter-{ci}-cover.html", "text_file": f"chapter-{ci}-cover.txt",
            "css_class": "chapter-cover",
        })
        seq += 1
        for pi, page in enumerate(ch.get("pages", []), 1):
            page = _coerce_dict(page)
            files.append({
                "type": "page", "chapter": ci, "page": pi,
                "title": _strip_html(_coerce_str(page.get("title", ""))),
                "source_key": f"chapters.{ci-1}.pages.{pi-1}", "body_key": "content",
                "narration_key": "narration",
                "file": f"chapter-{ci}-page-{pi}.html", "text_file": f"chapter-{ci}-page-{pi}.txt",
                "css_class": "page",
            })
            seq += 1
    end = _coerce_dict(data.get("end"))
    if end:
        files.append({
            "type": "end", "chapter": None, "page": None,
            "title": _strip_html(_coerce_str(end.get("title", "结束"))),
            "source_key": "end", "body_key": "content",
            "narration_key": "narration",
            "file": "end.html", "text_file": "end.txt",
            "css_class": "end",
        })
        seq += 1
    return files


def _get_nested(data: dict, key: str):
    parts = key.split(".")
    val = data
    for p in parts:
        if isinstance(val, dict):
            val = val.get(p, "")
        elif isinstance(val, list):
            try:
                val = val[int(p)]
            except (IndexError, ValueError):
                val = {}
        else:
            return ""
    return val


@router.get("", response_model=None)
async def list_study_materials(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(""),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_teacher_or_admin),
):
    base = select(StudyMaterial)
    if search:
        like = f"%{search}%"
        base = base.where(StudyMaterial.name.ilike(like))

    count_q = select(func.count()).select_from(base.subquery())
    total = (await session.execute(count_q)).scalar() or 0

    offset = (page - 1) * page_size
    rows = await session.execute(base.order_by(StudyMaterial.id.desc()).offset(offset).limit(page_size))
    materials = rows.scalars().all()

    lib_ids = {m.library_id for m in materials}
    user_ids = {m.created_by for m in materials}
    lib_map, user_map = await _resolve_names(session, lib_ids, user_ids)

    items = [
        StudyMaterialListItem(
            id=m.id, name=m.name, description=m.description,
            library_id=m.library_id, library_name=lib_map.get(m.library_id, ""),
            document_names=m.document_names, voice=m.voice,
            active=m.active, read_count=m.read_count, complete_count=m.complete_count, min_minutes=m.min_minutes,
            creator_name=user_map.get(m.created_by, ""),
            created_at=m.created_at, updated_at=m.updated_at,
        )
        for m in materials
    ]
    return success_response(StudyMaterialListResponse(items=items, total=total, page=page, page_size=page_size))


@router.get("/{material_id}/summary")
async def get_material_summary(
    material_id: int,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_teacher_or_admin),
):
    return success_response(await _compute_material_summary(material_id, session))


@router.post("/{material_id}/summary/regenerate")
async def regenerate_material_summary(
    material_id: int,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_teacher_or_admin),
):
    return success_response(await _compute_material_summary(material_id, session), "已重新汇总")


async def _compute_material_summary(material_id: int, session: AsyncSession) -> dict:
    material = (await session.execute(
        select(StudyMaterial).where(StudyMaterial.id == material_id)
    )).scalar_one_or_none()
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="学习资料不存在")

    assignments = (await session.execute(
        select(StudyAssignment).where(StudyAssignment.material_id == material_id)
    )).scalars().all()

    assign_by_student = {a.student_id: a for a in assignments}
    students_viewed = len(assign_by_student)
    students_completed = sum(1 for a in assignments if a.status == "completed")
    total_watch_seconds = sum(a.total_study_seconds for a in assignments)
    avg_watch_seconds = round(total_watch_seconds / students_viewed, 1) if students_viewed > 0 else 0.0

    stats = StudyMaterialSummaryStats(
        material_id=material.id,
        material_name=material.name,
        students_viewed=students_viewed,
        students_completed=students_completed,
        total_open_count=material.read_count,
        total_watch_seconds=total_watch_seconds,
        avg_watch_seconds=avg_watch_seconds,
    )

    students = (await session.execute(
        select(User).where(User.role == UserRole.STUDENT).order_by(User.id)
    )).scalars().all()

    student_items = []
    for s in students:
        a = assign_by_student.get(s.id)
        student_items.append(StudyMaterialStudentItem(
            student_id=s.id,
            name=s.display_name or s.username,
            viewed=a is not None,
            completed=(a.status == "completed") if a else False,
            total_study_seconds=a.total_study_seconds if a else 0,
            read_count=a.read_count if a else 0,
            complete_count=a.complete_count if a else 0,
        ))

    return {
        "stats": stats.model_dump(),
        "students": [si.model_dump() for si in student_items],
    }




_jobs: dict[str, dict] = {}
_background_tasks: set[asyncio.Task] = set()


async def _run_generation(
    job_id: str, name: str, description: str, library_id: int,
    doc_names_str: str, prompt_id: int, prompt_text: str,
    doc_contents: dict, lib_local_path: str, user_id: int,
):
    logger.info("_run_generation started job %s", job_id)
    try:
        from app import database as _db
        async with _db.async_session() as session:
            material = StudyMaterial(
                name=name, description=description,
                library_id=library_id, document_names=doc_names_str,
                prompt_id=prompt_id, created_by=user_id, min_minutes=10,
                created_at=datetime.now(),
            )
            session.add(material)
            await session.commit()

            try:
                ai_data = await generate_study_material(doc_contents, prompt_text)
            except Exception as e:
                logger.warning("Study material AI generation failed for job %s: %s", job_id, e)
                await session.delete(material)
                await session.commit()
                _jobs[job_id] = {"status": "failed", "error": "AI 调用失败，请稍后再试"}
                return

            if not isinstance(ai_data, dict) or "cover" not in ai_data:
                await session.delete(material)
                await session.commit()
                _jobs[job_id] = {"status": "failed", "error": "AI 返回内容格式不正确"}
                return

            lib_dir = get_library_directory(lib_local_path)
            try:
                page_css = _sanitize_css(ai_data.get("style", ""))
                file_entries = _files_for_material(ai_data)
                manifest_pages = []
                for entry in file_entries:
                    body_key = entry["body_key"]
                    src = _coerce_dict(_get_nested(ai_data, entry["source_key"]))
                    title = _coerce_str(src.get("title", entry["title"]))
                    body = _coerce_str(src.get(body_key, ""))
                    if entry["type"] == "cover":
                        html_body = f'<h1 class="page-title">{title}</h1>\n{body}'
                    elif entry["type"] in ("chapter_cover", "end"):
                        html_body = f'<h2 class="page-title">{title}</h2>\n{body}'
                    else:
                        html_body = body
                    html = _render_page_html(entry["title"], html_body, entry["css_class"], page_css)
                    save_material_file(lib_dir, material.id, entry["file"], html)
                    narration_text = _coerce_str(src.get(entry.get("narration_key", ""), ""))
                    save_material_file(lib_dir, material.id, entry["text_file"], narration_text)
                    manifest_pages.append(ManifestPage(
                        type=entry["type"], chapter=entry["chapter"], page=entry["page"],
                        title=entry["title"], file=entry["file"], text_file=entry["text_file"],
                    ))

                default_voice = settings.TTS_DEFAULT_VOICE
                if default_voice:
                    for mp in manifest_pages:
                        audio_file = mp.text_file.replace(".txt", ".mp3")
                        narration_text = read_material_file(lib_dir, material.id, mp.text_file)
                        try:
                            duration = await synthesize(narration_text, default_voice, get_material_file_path(lib_dir, material.id, audio_file))
                            mp.audio_file = audio_file
                            mp.audio_duration = duration
                        except Exception as e:
                            logger.warning("TTS failed for %s: %s", audio_file, e)

                material.voice = default_voice
                await session.commit()

                save_material_file(lib_dir, material.id, "manifest.json",
                    json.dumps({"id": material.id, "name": material.name, "created_at": str(material.created_at), "style": page_css, "pages": [p.model_dump() for p in manifest_pages]}, ensure_ascii=False, indent=2))
            except Exception:
                logger.exception("Study material file generation failed for job %s", job_id)
                delete_material_dir(lib_dir, material.id)
                await session.delete(material)
                await session.commit()
                _jobs[job_id] = {"status": "failed", "error": "生成文件写入失败"}
                return

        _jobs[job_id] = {"status": "done", "material_id": material.id}
    except Exception as e:
        logger.exception("Generation job %s failed", job_id)
        _jobs[job_id] = {"status": "failed", "error": str(e)}


@router.post("/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_material(
    request: StudyMaterialGenerateRequest,
    current_user: User = Depends(require_teacher_or_admin),
    session: AsyncSession = Depends(get_session),
):
    lib = (await session.execute(
        select(DocumentLibrary).where(DocumentLibrary.id == request.library_id)
    )).scalar_one_or_none()
    if lib is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档库不存在")

    if request.document_names:
        docs = (await session.execute(
            select(Document).where(
                Document.library_id == request.library_id,
                Document.filename.in_(request.document_names),
            )
        )).scalars().all()
        found_names = {d.filename for d in docs}
        for name in request.document_names:
            if name not in found_names:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"文档「{name}」在该库中不存在")
    else:
        docs = (await session.execute(
            select(Document).where(Document.library_id == request.library_id)
        )).scalars().all()
        if not docs:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文档库中没有文档可供生成")

    prompt = (await session.execute(
        select(AIPrompt).where(AIPrompt.id == request.prompt_id, AIPrompt.prompt_type == "study")
    )).scalar_one_or_none()
    if prompt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="学习资料提示词不存在")

    doc_contents: dict[str, str] = {}
    for doc in docs:
        try:
            with open(doc.path, "r", encoding="utf-8") as f:
                doc_contents[doc.filename] = f.read()
        except OSError:
            continue

    if not doc_contents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="所选文档均无法读取")

    doc_names_str = ",".join(request.document_names) if request.document_names else ",".join(d.filename for d in docs)

    job_id = uuid.uuid4().hex[:12]
    _jobs[job_id] = {"status": "running", "material_id": None, "error": None}
    task = asyncio.create_task(_run_generation(
        job_id, request.name, request.description, request.library_id,
        doc_names_str, request.prompt_id, prompt.prompt, doc_contents,
        lib.local_path, current_user.id,
    ))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    logger.info("Job %s created, background task scheduled", job_id)
    return success_response({"job_id": job_id}, "生成任务已启动")


@router.get("/generate/{job_id}")
async def get_generation_status(job_id: str):
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    return success_response(job)


@router.get("/voices")
async def list_voices(_: User = Depends(require_teacher_or_admin)):
    voices = [v.strip() for v in settings.TTS_AVAILABLE_VOICES.split(",") if v.strip()]
    return success_response({"default": settings.TTS_DEFAULT_VOICE, "voices": voices})


@router.post("/{material_id}/voice")
async def voice_material(
    material_id: int,
    request: VoiceRequest,
    current_user: User = Depends(require_teacher_or_admin),
    session: AsyncSession = Depends(get_session),
):
    voice = request.voice.strip()
    available = [v.strip() for v in settings.TTS_AVAILABLE_VOICES.split(",") if v.strip()]
    if voice not in available:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的配音角色")

    material = (await session.execute(
        select(StudyMaterial).where(StudyMaterial.id == material_id)
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
        raw = read_material_file(lib_dir, material_id, "manifest.json")
        manifest = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="无法读取学习资料元数据")

    success_count = 0
    for p in manifest.get("pages", []):
        text_file = p.get("text_file", "")
        if not text_file:
            continue
        audio_file = text_file.replace(".txt", ".mp3")
        try:
            narration = read_material_file(lib_dir, material_id, text_file)
            duration = await synthesize(narration, voice, get_material_file_path(lib_dir, material_id, audio_file))
            p["audio_file"] = audio_file
            p["audio_duration"] = duration
            success_count += 1
        except Exception as e:
            logger.warning("TTS failed for material %d page %s: %s", material_id, audio_file, e)
            p.pop("audio_file", None)
            p.pop("audio_duration", None)

    if success_count == 0:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="配音生成失败，请稍后重试")

    material.voice = voice
    await session.commit()

    save_material_file(lib_dir, material_id, "manifest.json",
                       json.dumps(manifest, ensure_ascii=False, indent=2))

    return success_response(None, f"配音完成（{success_count} 页）")


@router.get("/{material_id}/audio/{filename:path}")
async def get_material_audio(
    material_id: int,
    filename: str,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_teacher_or_admin),
):
    base = os.path.basename(filename)
    if not base.endswith(".mp3"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持 MP3 格式")

    material = (await session.execute(
        select(StudyMaterial).where(StudyMaterial.id == material_id)
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
        filepath = get_material_file_path(lib_dir, material_id, base)
    except (OSError, ValueError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="音频文件不存在")

    if not os.path.isfile(filepath):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="音频文件不存在")

    return FileResponse(filepath, media_type="audio/mpeg")


@router.get("/{material_id}")
async def get_material_detail(
    material_id: int,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_teacher_or_admin),
):
    material = (await session.execute(
        select(StudyMaterial).where(StudyMaterial.id == material_id)
    )).scalar_one_or_none()
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="学习资料不存在")

    lib = (await session.execute(
        select(DocumentLibrary).where(DocumentLibrary.id == material.library_id)
    )).scalar_one_or_none()

    user = (await session.execute(
        select(User).where(User.id == material.created_by)
    )).scalar_one_or_none()

    lib_dir = get_library_directory(lib.local_path) if lib else ""
    pages = []
    try:
        raw = read_material_file(lib_dir, material_id, "manifest.json")
        manifest = json.loads(raw)
        for p in manifest.get("pages", []):
            p["title"] = _strip_html(p.get("title", ""))
            pages.append(ManifestPage(**p))
    except (OSError, json.JSONDecodeError):
        pass

    return success_response(
        StudyMaterialDetailResponse(
            id=material.id, name=material.name, description=material.description,
            library_id=material.library_id, library_name=lib.name if lib else "",
            document_names=material.document_names, prompt_id=material.prompt_id, voice=material.voice,
            active=material.active, read_count=material.read_count, complete_count=material.complete_count, min_minutes=material.min_minutes,
            created_by=material.created_by, creator_name=user.username if user else "",
            created_at=material.created_at, updated_at=material.updated_at,
            pages=pages,
        )
    )


@router.get("/{material_id}/page/{page_file:path}")
async def get_material_page(
    material_id: int,
    page_file: str,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_teacher_or_admin),
):
    material = (await session.execute(
        select(StudyMaterial).where(StudyMaterial.id == material_id)
    )).scalar_one_or_none()
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="学习资料不存在")

    lib = (await session.execute(
        select(DocumentLibrary).where(DocumentLibrary.id == material.library_id)
    )).scalar_one_or_none()
    if lib is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="关联文档库不存在")

    lib_dir = get_library_directory(lib.local_path)
    base = os.path.basename(page_file)
    if not base.endswith(".html"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持请求 HTML 页面")

    try:
        html = read_material_file(lib_dir, material_id, base)
        txt_file = base.replace(".html", ".txt")
        txt = ""
        try:
            txt = read_material_file(lib_dir, material_id, txt_file)
        except OSError:
            pass
        return success_response({"html": html, "text": txt})
    except (OSError, ValueError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="页面不存在")


@router.put("/{material_id}")
async def update_material(
    material_id: int,
    request: StudyMaterialUpdateRequest,
    current_user: User = Depends(require_teacher_or_admin),
    session: AsyncSession = Depends(get_session),
):
    material = (await session.execute(
        select(StudyMaterial).where(StudyMaterial.id == material_id)
    )).scalar_one_or_none()
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="学习资料不存在")
    if request.name is not None:
        if not request.name.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="名称不能为空")
        material.name = request.name
    if request.description is not None:
        material.description = request.description
    if request.active is not None:
        material.active = request.active
    if request.min_minutes is not None:
        material.min_minutes = request.min_minutes
    await session.commit()
    await session.refresh(material)
    return success_response(None, "更新成功")


@router.delete("/{material_id}")
async def delete_material(
    material_id: int,
    current_user: User = Depends(require_teacher_or_admin),
    session: AsyncSession = Depends(get_session),
):
    material = (await session.execute(
        select(StudyMaterial).where(StudyMaterial.id == material_id)
    )).scalar_one_or_none()
    if material is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="学习资料不存在")

    lib = (await session.execute(
        select(DocumentLibrary).where(DocumentLibrary.id == material.library_id)
    )).scalar_one_or_none()
    if lib:
        lib_dir = get_library_directory(lib.local_path)
        delete_material_dir(lib_dir, material_id)

    await session.delete(material)
    await session.commit()
    return success_response(None, "删除成功")
