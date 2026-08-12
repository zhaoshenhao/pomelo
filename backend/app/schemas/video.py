from datetime import datetime

from pydantic import BaseModel


class VideoListItem(BaseModel):
    id: int
    name: str
    description: str
    library_id: int | None = None
    library_name: str = ""
    creator_name: str = ""
    duration_seconds: int
    active: bool
    source: str
    oss_path: str
    original_filename: str
    total_views: int
    total_watch_seconds: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VideoListResponse(BaseModel):
    items: list[VideoListItem]
    total: int
    page: int
    page_size: int


class VideoCreateFromOss(BaseModel):
    name: str
    description: str = ""
    library_id: int | None = None
    oss_path: str
    active: bool = True


class VideoUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    library_id: int | None = None
    active: bool | None = None


class VideoDeleteRequest(BaseModel):
    delete_oss: bool = False


class VideoUploadResult(BaseModel):
    id: int
    name: str
    oss_path: str
    duration_seconds: int


class VideoDetailResponse(VideoListItem):
    pass


class VideoCommentItem(BaseModel):
    id: int
    video_id: int
    user_id: int
    username: str = ""
    content: str
    created_at: str


class VideoCommentListResponse(BaseModel):
    items: list[VideoCommentItem]
    total: int
    page: int
    page_size: int


class VideoCommentCreate(BaseModel):
    content: str


class VideoWatchReport(BaseModel):
    watch_seconds: int


class VideoMyItem(BaseModel):
    id: int
    name: str
    description: str
    library_id: int | None = None
    library_name: str = ""
    duration_seconds: int
    watched: bool
    my_views: int
    my_watch_seconds: int
    last_watched_at: str | None


class VideoStatsResponse(BaseModel):
    video_id: int
    video_name: str
    total_viewers: int
    total_views: int
    total_watch_seconds: int


class VideoViewRecordItem(BaseModel):
    watched_at: str
    username: str
    watch_seconds: int
