from dataclasses import dataclass


@dataclass(frozen=True)
class StoredChapterPageDTO:
    key: str
    width: int
    height: int
    original_filename: str


@dataclass(frozen=True)
class CreateStudioChapterDTO:
    creator_id: int
    chapter: int
    privacy_id: int
    pages: list[StoredChapterPageDTO]
    name: str | None = None
    extra_number: int | None = None
