import json
import logging
import os
import shutil
import zipfile
from datetime import datetime

from app.config import settings

logger = logging.getLogger(__name__)


def sanitize_directory_name(name: str) -> str:
    name = name.strip()
    if not name:
        raise ValueError("目录名称不能为空")
    if name in (".", "..") or name.startswith("../") or name.startswith("..\\"):
        raise ValueError("目录名称不能使用特殊路径符号")
    if "/" in name or "\\" in name:
        raise ValueError("目录名称不能包含路径分隔符")
    if len(name) > 200:
        raise ValueError("目录名称过长")
    return name


def sanitize_filename(name: str) -> str:
    name = name.strip()
    if not name:
        raise ValueError("文件名不能为空")
    if name in (".", "..") or name.startswith("../") or name.startswith("..\\"):
        raise ValueError("文件名不能使用特殊路径符号")
    if "/" in name or "\\" in name:
        raise ValueError("文件名不能包含路径分隔符")
    return name


def get_library_directory(local_path: str) -> str:
    return local_path.strip("/\\").rsplit("/", 1)[-1].rsplit("\\", 1)[-1]


def get_docs_root() -> str:
    docs_root = settings.DOCS_ROOT
    if not os.path.isabs(docs_root):
        docs_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), docs_root)
    return os.path.normpath(docs_root)


def get_library_root() -> str:
    path = os.path.join(get_docs_root(), "docs")
    os.makedirs(path, exist_ok=True)
    return path


def get_library_path(directory_name: str) -> str:
    path = os.path.join(get_library_root(), directory_name)
    os.makedirs(path, exist_ok=True)
    return path


def save_library_file(directory_name: str, filename: str, content: str) -> str:
    library_path = get_library_path(directory_name)
    filepath = os.path.join(library_path, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath


def get_stage_root() -> str:
    path = os.path.join(get_docs_root(), "stage")
    os.makedirs(path, exist_ok=True)
    return path


def get_stage_dir(stage_id: int) -> str:
    path = os.path.join(get_stage_root(), str(stage_id))
    os.makedirs(path, exist_ok=True)
    return path


def save_stage_file(stage_id: int, filename: str, content: bytes | str) -> str:
    stage_dir = get_stage_dir(stage_id)
    filepath = os.path.join(stage_dir, filename)
    if isinstance(content, str):
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    else:
        with open(filepath, "wb") as f:
            f.write(content)
    return filepath


def read_stage_file(stage_id: int, filename: str) -> str:
    stage_dir = get_stage_dir(stage_id)
    filepath = os.path.join(stage_dir, filename)
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"文件不存在: {filename}")
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def read_approval_json(stage_id: int) -> dict:
    stage_dir = get_stage_dir(stage_id)
    filepath = os.path.join(stage_dir, "approval.json")
    if not os.path.exists(filepath):
        return {
            "content_choice": "新增",
            "replace_docs": [],
            "content_diff": {"new": [], "conflict": []},
            "new_name": "",
        }
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def write_approval_json(stage_id: int, data: dict) -> str:
    stage_dir = get_stage_dir(stage_id)
    filepath = os.path.join(stage_dir, "approval.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filepath


def delete_stage_dir(stage_id: int) -> None:
    stage_dir = get_stage_dir(stage_id)
    if os.path.isdir(stage_dir):
        shutil.rmtree(stage_dir)


def backup_library(directory_name: str) -> str:
    lib_path = get_library_path(directory_name)
    if not os.path.isdir(lib_path):
        raise FileNotFoundError(f"文档库目录不存在: {directory_name}")
    backup_root = os.path.join(get_docs_root(), "backup", directory_name)
    os.makedirs(backup_root, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
    base_name = os.path.join(backup_root, timestamp)
    return shutil.make_archive(base_name, "zip", lib_path)


def _get_backup_path(directory_name: str, backup_filename: str) -> str:
    backup_root = os.path.join(get_docs_root(), "backup", directory_name)
    return os.path.join(backup_root, backup_filename)


def _parse_backup_timestamp(filename: str) -> datetime | None:
    stem = filename.removesuffix(".zip")
    try:
        return datetime.strptime(stem, "%Y-%m-%d-%H-%M")
    except ValueError:
        return None


def list_backups(directory_name: str) -> list[dict]:
    backup_dir = os.path.join(get_docs_root(), "backup", directory_name)
    if not os.path.isdir(backup_dir):
        return []
    entries = []
    for name in os.listdir(backup_dir):
        if not name.endswith(".zip"):
            continue
        filepath = os.path.join(backup_dir, name)
        stat = os.stat(filepath)
        created_at = _parse_backup_timestamp(name)
        if created_at is None:
            created_at = datetime.fromtimestamp(stat.st_mtime)
        entries.append({
            "filename": name,
            "size": stat.st_size,
            "created_at": created_at.isoformat(),
        })
    entries.sort(key=lambda e: e["created_at"], reverse=True)
    return entries


def _safe_zip_member(name: str) -> str | None:
    safe = os.path.basename(name)
    if safe in (".", "..") or not safe:
        return None
    if "/" in name or "\\" in name:
        if safe != name:
            return None
    return safe


def list_backup_documents(directory_name: str, backup_filename: str) -> list[dict]:
    filepath = _get_backup_path(directory_name, backup_filename)
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"备份文件不存在: {backup_filename}")
    docs = []
    with zipfile.ZipFile(filepath, "r") as zf:
        for info in zf.infolist():
            safe = _safe_zip_member(info.filename)
            if safe is None or info.is_dir():
                continue
            dt = datetime(*info.date_time)
            docs.append({
                "name": safe,
                "size": info.file_size,
                "modified_at": dt.isoformat(),
            })
    docs.sort(key=lambda d: d["name"])
    return docs


def read_backup_document(directory_name: str, backup_filename: str, doc_name: str) -> str:
    filepath = _get_backup_path(directory_name, backup_filename)
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"备份文件不存在: {backup_filename}")
    safe = _safe_zip_member(doc_name)
    if safe is None:
        raise ValueError("无效的文档名")
    with zipfile.ZipFile(filepath, "r") as zf:
        try:
            return zf.read(doc_name).decode("utf-8")
        except KeyError:
            raise FileNotFoundError(f"备份中不存在文档: {doc_name}")


def restore_backup(library_directory: str, directory_name: str, backup_filename: str) -> str:
    zip_path = _get_backup_path(directory_name, backup_filename)
    if not os.path.isfile(zip_path):
        raise FileNotFoundError(f"备份文件不存在: {backup_filename}")
    lib_path = get_library_path(library_directory)
    if os.path.isdir(lib_path):
        shutil.rmtree(lib_path)
    os.makedirs(lib_path, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.namelist():
            safe = _safe_zip_member(member)
            if safe is None:
                continue
            target = os.path.join(lib_path, safe)
            with zf.open(member) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
    logger.info("Restored backup %s to library %s", backup_filename, directory_name)
    return lib_path
