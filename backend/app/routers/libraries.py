import os
import shutil

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies.auth import require_admin, require_teacher_or_admin
from app.models.document import Document, DocumentLibrary
from app.models.stage_document import StageDocument
from app.models.user import User
from app.schemas.common import success_response
from app.schemas.document import (
    DocumentContentUpdateRequest,
    DocumentLibraryCreateRequest,
    DocumentLibraryResponse,
    DocumentLibraryUpdateRequest,
    DocumentListResponse,
    DocumentResponse,
)
from app.services.file_service import (
    delete_stage_dir,
    get_library_directory,
    get_library_path,
    get_library_root,
    list_backup_documents,
    list_backups,
    read_backup_document,
    restore_backup,
    sanitize_directory_name,
)

router = APIRouter(prefix="/libraries", tags=["libraries"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_library(
    request: DocumentLibraryCreateRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    existing = await session.execute(select(DocumentLibrary).where(DocumentLibrary.name == request.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="文档库名称已存在")

    try:
        directory = sanitize_directory_name(request.directory or request.name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    dir_path = os.path.join(get_library_root(), directory)
    if os.path.isdir(dir_path):
        if not request.use_existing_directory:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"目录「{directory}」已存在，是否使用该已存在目录？",
            )
    else:
        get_library_path(directory)

    library = DocumentLibrary(
        name=request.name,
        description=request.description,
        local_path=f"/storage/{directory}/",
    )
    session.add(library)
    await session.commit()
    await session.refresh(library)
    return success_response(DocumentLibraryResponse.model_validate(library), "文档库创建成功")


@router.get("")
async def list_libraries(
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(DocumentLibrary).order_by(DocumentLibrary.id))
    libraries = result.scalars().all()
    return success_response([DocumentLibraryResponse.model_validate(lib) for lib in libraries])


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    current_user: User = Depends(require_teacher_or_admin),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")

    if os.path.exists(document.path):
        os.remove(document.path)

    await session.delete(document)
    await session.commit()
    return success_response(None, "文档已删除")


@router.get("/documents/{document_id}/content")
async def get_document_content(
    document_id: int,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")

    if not os.path.exists(document.path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档文件不存在")

    with open(document.path, "r", encoding="utf-8") as f:
        content = f.read()
    return success_response({"filename": document.filename, "content": content})


@router.put("/documents/{document_id}/content")
async def update_document_content(
    document_id: int,
    request: DocumentContentUpdateRequest,
    current_user: User = Depends(require_teacher_or_admin),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")

    if not os.path.exists(document.path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档文件不存在")

    with open(document.path, "w", encoding="utf-8") as f:
        f.write(request.content)

    await session.commit()

    return success_response({"filename": document.filename, "content": request.content}, "文档已更新")


@router.get("/{library_id}/documents")
async def list_documents(
    library_id: int,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Document).where(Document.library_id == library_id).order_by(Document.id)
    )
    documents = result.scalars().all()
    return success_response(
        DocumentListResponse(
            items=[DocumentResponse.model_validate(doc) for doc in documents],
            total=len(documents),
        )
    )


@router.get("/{library_id}")
async def get_library(
    library_id: int,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(DocumentLibrary).where(DocumentLibrary.id == library_id))
    library = result.scalar_one_or_none()
    if library is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档库不存在")
    return success_response(DocumentLibraryResponse.model_validate(library))


@router.put("/{library_id}")
async def update_library(
    library_id: int,
    request: DocumentLibraryUpdateRequest,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(DocumentLibrary).where(DocumentLibrary.id == library_id))
    library = result.scalar_one_or_none()
    if library is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档库不存在")
    if request.name is not None:
        library.name = request.name
    if request.description is not None:
        library.description = request.description
    if request.directory is not None:
        try:
            directory = sanitize_directory_name(request.directory)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        library.local_path = f"/storage/{directory}/"
        get_library_path(directory)
    await session.commit()
    await session.refresh(library)
    return success_response(DocumentLibraryResponse.model_validate(library), "文档库更新成功")


@router.delete("/{library_id}")
async def delete_library(
    library_id: int,
    delete_directory: bool = False,
    force: bool = False,
    current_user: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(DocumentLibrary).where(DocumentLibrary.id == library_id))
    library = result.scalar_one_or_none()
    if library is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档库不存在")

    def _remove_file(filepath: str) -> None:
        if os.path.exists(filepath):
            os.remove(filepath)

    def _remove_dir(dirpath: str) -> None:
        if os.path.isdir(dirpath):
            shutil.rmtree(dirpath)

    def _cleanup_safe(action, *args):
        if force:
            try:
                action(*args)
            except OSError:
                pass
        else:
            action(*args)

    doc_result = await session.execute(select(Document).where(Document.library_id == library_id))
    for doc in doc_result.scalars().all():
        _cleanup_safe(_remove_file, doc.path)
        await session.delete(doc)

    stage_result = await session.execute(select(StageDocument).where(StageDocument.library_id == library_id))
    for stage_doc in stage_result.scalars().all():
        _cleanup_safe(delete_stage_dir, stage_doc.id)
        await session.delete(stage_doc)

    await session.commit()

    if delete_directory:
        directory = get_library_directory(library.local_path)
        dir_path = os.path.join(get_library_root(), directory)
        _cleanup_safe(_remove_dir, dir_path)

    await session.delete(library)
    await session.commit()

    if force:
        message = "已强制删除（目录已尽可能清理）" if delete_directory else "已强制删除（目录已保留在磁盘）"
    else:
        message = "文档库已删除（目录已清理）" if delete_directory else "文档库已删除（目录已保留在磁盘）"
    return success_response(None, message)


@router.get("/{library_id}/backups")
async def get_backups(
    library_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_teacher_or_admin),
):
    result = await session.execute(select(DocumentLibrary).where(DocumentLibrary.id == library_id))
    library = result.scalar_one_or_none()
    if library is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档库不存在")
    directory = get_library_directory(library.local_path)
    backups = list_backups(directory)
    return success_response(backups)


@router.get("/{library_id}/backups/{backup_filename}")
async def get_backup_documents(
    library_id: int,
    backup_filename: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_teacher_or_admin),
):
    result = await session.execute(select(DocumentLibrary).where(DocumentLibrary.id == library_id))
    library = result.scalar_one_or_none()
    if library is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档库不存在")
    directory = get_library_directory(library.local_path)
    try:
        docs = list_backup_documents(directory, backup_filename)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="备份文件不存在")
    return success_response(docs)


@router.get("/{library_id}/backups/{backup_filename}/documents/{doc_name}/content")
async def get_backup_document_content(
    library_id: int,
    backup_filename: str,
    doc_name: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_teacher_or_admin),
):
    result = await session.execute(select(DocumentLibrary).where(DocumentLibrary.id == library_id))
    library = result.scalar_one_or_none()
    if library is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档库不存在")
    directory = get_library_directory(library.local_path)
    try:
        content = read_backup_document(directory, backup_filename, doc_name)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return success_response({"name": doc_name, "content": content})


@router.post("/{library_id}/backups/{backup_filename}/restore")
async def restore_backup_endpoint(
    library_id: int,
    backup_filename: str,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_teacher_or_admin),
):
    result = await session.execute(select(DocumentLibrary).where(DocumentLibrary.id == library_id))
    library = result.scalar_one_or_none()
    if library is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档库不存在")

    directory = get_library_directory(library.local_path)

    doc_result = await session.execute(select(Document).where(Document.library_id == library_id))
    for d in doc_result.scalars().all():
        if os.path.exists(d.path):
            os.remove(d.path)
        await session.delete(d)
    await session.commit()

    try:
        lib_path = restore_backup(directory, directory, backup_filename)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    if os.path.isdir(lib_path):
        for name in os.listdir(lib_path):
            filepath = os.path.join(lib_path, name)
            if os.path.isfile(filepath) and name.endswith(".md"):
                doc = Document(
                    library_id=library_id,
                    filename=name,
                    path=filepath,
                    uploaded_by=current_user.id,
                )
                session.add(doc)
    await session.commit()

    return success_response(None, "文档库已恢复")
