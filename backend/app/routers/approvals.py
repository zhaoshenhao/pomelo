import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies.auth import require_teacher_or_admin
from app.models.document import Document, DocumentLibrary
from app.models.stage_document import StageDocument
from app.models.user import User
from app.schemas.approval import (
    ApprovalJson,
    MetaUpdateRequest,
    PreviewSaveRequest,
    RewriteRequest,
    StageDocumentResponse,
)
from app.schemas.common import success_response
from app.services.ai_service import content_diff, grammar_rewrite, style_rewrite
from app.services.document_parser import convert_to_markdown
from app.services.file_service import (
    backup_library,
    delete_stage_dir,
    get_library_directory,
    read_approval_json,
    read_stage_file,
    sanitize_filename,
    save_library_file,
    save_stage_file,
    write_approval_json,
)

ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx", ".xlsx", ".xls", ".pptx"}

STAGE_ROOTS = {
    "txt": "text",
    "md": "markdown",
    "docx": "word",
    "pdf": "pdf",
    "xlsx": "excel",
    "xls": "excel",
    "pptx": "ppt",
}

router = APIRouter(prefix="/approvals", tags=["approvals"])


def get_file_type(ext: str) -> str:
    return STAGE_ROOTS.get(ext.lstrip("."), "text")


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_approval(
    file: UploadFile = File(...),
    library_id: int = None,
    current_user: User = Depends(require_teacher_or_admin),
    session: AsyncSession = Depends(get_session),
):
    if library_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="必须指定文档库")

    result = await session.execute(select(DocumentLibrary).where(DocumentLibrary.id == library_id))
    library = result.scalar_one_or_none()
    if library is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档库不存在")

    if file.filename is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件名不能为空")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件格式: {ext}，仅支持: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    file_type = get_file_type(ext)

    content = await file.read()

    stage_doc = StageDocument(
        library_id=library_id,
        original_filename=file.filename,
        file_type=file_type,
        stage_dir="",
        status="new",
        created_by=current_user.id,
    )
    session.add(stage_doc)
    await session.commit()
    await session.refresh(stage_doc)

    stage_dir_value = f"/storage/stage/{stage_doc.id}/"
    stage_doc.stage_dir = stage_dir_value
    await session.commit()
    await session.refresh(stage_doc)

    save_stage_file(stage_doc.id, file.filename, content)

    suffix = os.path.splitext(file.filename)[1]

    import tempfile
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        md_content = convert_to_markdown(tmp_path)
    finally:
        os.unlink(tmp_path)

    save_stage_file(stage_doc.id, "origin.md", md_content)
    save_stage_file(stage_doc.id, "preview.md", md_content)

    default_new_name = os.path.splitext(file.filename)[0] + ".md"
    approval_data = ApprovalJson(
        content_choice="新增",
        replace_docs=[],
        new_name=default_new_name,
    ).model_dump()
    write_approval_json(stage_doc.id, approval_data)

    return success_response(StageDocumentResponse.model_validate(stage_doc), "已提交审批")


@router.get("")
async def list_approvals(
    library_id: int = None,
    status: str = None,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(StageDocument)
    if library_id is not None:
        stmt = stmt.where(StageDocument.library_id == library_id)
    if status is not None:
        stmt = stmt.where(StageDocument.status == status)
    else:
        stmt = stmt.where(StageDocument.status.in_(["new", "content_review", "rewrite", "preview"]))
    stmt = stmt.order_by(StageDocument.id.desc())

    result = await session.execute(stmt)
    records = result.scalars().all()

    items = []
    for r in records:
        lib_result = await session.execute(select(DocumentLibrary).where(DocumentLibrary.id == r.library_id))
        lib = lib_result.scalar_one_or_none()
        data = StageDocumentResponse.model_validate(r)
        data.library_name = lib.name if lib else None
        items.append(data)

    return success_response({
        "items": [item.model_dump() for item in items],
        "total": len(items),
    })


@router.get("/{approval_id}")
async def get_approval_detail(
    approval_id: int,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(StageDocument).where(StageDocument.id == approval_id))
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="审批记录不存在")

    origin_content = ""
    preview_content = ""
    approval_json = ApprovalJson().model_dump()
    try:
        origin_content = read_stage_file(approval_id, "origin.md")
    except FileNotFoundError:
        pass
    try:
        preview_content = read_stage_file(approval_id, "preview.md")
    except FileNotFoundError:
        pass

    approval_json = read_approval_json(approval_id)

    doc_result = await session.execute(
        select(Document).where(Document.library_id == record.library_id).order_by(Document.filename)
    )
    library_docs = doc_result.scalars().all()
    library_documents = [
        {"id": d.id, "filename": d.filename, "path": d.path, "created_at": str(d.created_at)}
        for d in library_docs
    ]

    lib_result = await session.execute(select(DocumentLibrary).where(DocumentLibrary.id == record.library_id))
    lib = lib_result.scalar_one_or_none()

    return success_response({
        "id": record.id,
        "library_id": record.library_id,
        "library_name": lib.name if lib else None,
        "original_filename": record.original_filename,
        "file_type": record.file_type,
        "stage_dir": record.stage_dir,
        "status": record.status,
        "created_by": record.created_by,
        "created_at": str(record.created_at),
        "updated_at": str(record.updated_at),
        "origin_content": origin_content,
        "preview_content": preview_content,
        "approval": approval_json,
        "library_documents": library_documents,
    })


@router.delete("/{approval_id}")
async def delete_approval(
    approval_id: int,
    current_user: User = Depends(require_teacher_or_admin),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(StageDocument).where(StageDocument.id == approval_id))
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="审批记录不存在")
    if record.status in ("completed", "deleted"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="已完成或已删除的审批记录不可操作")

    delete_stage_dir(approval_id)
    record.status = "deleted"
    await session.commit()
    return success_response(None, "审批记录已删除")


@router.put("/{approval_id}/meta")
async def update_approval_meta(
    approval_id: int,
    request: MetaUpdateRequest,
    current_user: User = Depends(require_teacher_or_admin),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(StageDocument).where(StageDocument.id == approval_id))
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="审批记录不存在")
    if record.status in ("completed", "deleted"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="已完成或已删除的审批记录不可操作")

    approval_data = read_approval_json(approval_id)
    if request.new_name is not None:
        approval_data["new_name"] = sanitize_filename(request.new_name)
    if request.content_choice is not None:
        if request.content_choice not in ("新增", "替换整个文档库", "替换部分文档"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的 content_choice")
        if request.content_choice in ("替换整个文档库", "替换部分文档"):
            doc_count_result = await session.execute(
                select(func.count(Document.id)).where(Document.library_id == record.library_id)
            )
            if doc_count_result.scalar() == 0:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文档库为空，只能选择新增")
        approval_data["content_choice"] = request.content_choice
    if request.replace_docs is not None:
        approval_data["replace_docs"] = request.replace_docs
    write_approval_json(approval_id, approval_data)
    return success_response(approval_data)


@router.post("/{approval_id}/content-diff")
async def generate_content_diff(
    approval_id: int,
    current_user: User = Depends(require_teacher_or_admin),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(StageDocument).where(StageDocument.id == approval_id))
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="审批记录不存在")
    if record.status in ("completed", "deleted"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="已完成或已删除的审批记录不可操作")

    origin_content = read_stage_file(approval_id, "origin.md")

    doc_result = await session.execute(
        select(Document).where(Document.library_id == record.library_id)
    )
    library_docs = doc_result.scalars().all()
    library_texts = {}
    for d in library_docs:
        if os.path.exists(d.path):
            with open(d.path, "r", encoding="utf-8") as f:
                library_texts[d.filename] = f.read()
        else:
            library_texts[d.filename] = ""

    diff_result = await content_diff(origin_content, library_texts)
    if "new" not in diff_result:
        diff_result = {"new": [], "conflict": []}
    if "conflict" not in diff_result:
        diff_result["conflict"] = []

    approval_data = read_approval_json(approval_id)
    approval_data["content_diff"] = diff_result
    write_approval_json(approval_id, approval_data)

    if record.status == "new":
        record.status = "content_review"
        await session.commit()

    return success_response(diff_result, "内容差异已生成")


@router.post("/{approval_id}/rewrite")
async def rewrite_content(
    approval_id: int,
    request: RewriteRequest,
    current_user: User = Depends(require_teacher_or_admin),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(StageDocument).where(StageDocument.id == approval_id))
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="审批记录不存在")
    if record.status in ("completed", "deleted"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="已完成或已删除的审批记录不可操作")

    origin_content = read_stage_file(approval_id, "origin.md")

    if request.method == "keep":
        result_content = origin_content
    elif request.method == "grammar":
        result_content = await grammar_rewrite(origin_content)
    elif request.method == "style":
        if request.style_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="自定义风格必须提供 style_id")
        from app.models.rewrite_style import RewriteStyle
        style_result = await session.execute(select(RewriteStyle).where(RewriteStyle.id == request.style_id))
        style = style_result.scalar_one_or_none()
        if style is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="改写风格不存在")
        result_content = await style_rewrite(origin_content, style.prompt)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"无效的改写方法: {request.method}")

    save_stage_file(approval_id, "preview.md", result_content)

    if record.status not in ("rewrite", "preview"):
        record.status = "rewrite"
        await session.commit()

    return success_response({"content": result_content}, "改写完成")


@router.put("/{approval_id}/preview")
async def save_preview(
    approval_id: int,
    request: PreviewSaveRequest,
    current_user: User = Depends(require_teacher_or_admin),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(StageDocument).where(StageDocument.id == approval_id))
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="审批记录不存在")
    if record.status in ("completed", "deleted"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="已完成或已删除的审批记录不可操作")

    save_stage_file(approval_id, "preview.md", request.content)

    if record.status not in ("rewrite", "preview"):
        record.status = "rewrite"
        await session.commit()

    return success_response(None, "已保存")


@router.post("/{approval_id}/confirm")
async def confirm_approval(
    approval_id: int,
    current_user: User = Depends(require_teacher_or_admin),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(StageDocument).where(StageDocument.id == approval_id))
    record = result.scalar_one_or_none()
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="审批记录不存在")
    if record.status in ("completed", "deleted"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="已完成或已删除的审批记录不可操作")

    lib_result = await session.execute(select(DocumentLibrary).where(DocumentLibrary.id == record.library_id))
    library = lib_result.scalar_one_or_none()
    if library is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档库不存在")

    approval_data = read_approval_json(approval_id)
    new_name = approval_data.get("new_name", record.original_filename)
    if not new_name.endswith(".md"):
        new_name = os.path.splitext(new_name)[0] + ".md"
    new_name = sanitize_filename(new_name)
    content_choice = approval_data.get("content_choice", "新增")
    replace_docs = approval_data.get("replace_docs", [])

    directory = get_library_directory(library.local_path)

    backup_library(directory)

    replaced_set: set[str] = set()

    if content_choice == "替换整个文档库":
        doc_result = await session.execute(select(Document).where(Document.library_id == record.library_id))
        for d in doc_result.scalars().all():
            replaced_set.add(d.filename)
            if os.path.exists(d.path):
                os.remove(d.path)
            await session.delete(d)
    elif content_choice == "替换部分文档" and replace_docs:
        replaced_set = set(replace_docs)
        doc_result = await session.execute(
            select(Document).where(
                Document.library_id == record.library_id,
                Document.filename.in_(replace_docs),
            )
        )
        for d in doc_result.scalars().all():
            if os.path.exists(d.path):
                os.remove(d.path)
            await session.delete(d)
    await session.commit()

    if new_name not in replaced_set:
        remaining_result = await session.execute(
            select(Document).where(
                Document.library_id == record.library_id,
                Document.filename == new_name,
            )
        )
        if remaining_result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"文档库中已存在同名文件「{new_name}」，请修改入库名称",
            )

    preview_content = read_stage_file(approval_id, "preview.md")
    filepath = save_library_file(directory, new_name, preview_content)

    document = Document(
        library_id=record.library_id,
        filename=new_name,
        path=filepath,
        uploaded_by=current_user.id,
    )
    session.add(document)
    await session.commit()

    delete_stage_dir(approval_id)
    record.status = "completed"
    await session.commit()

    return success_response(None, "审批完成，文档已入库")
