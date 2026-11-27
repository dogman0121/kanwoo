from dataclasses import dataclass


@dataclass(frozen=True)
class ChapterPageDTO:
    uuid: str
    is_new: bool
    width: int | None = None
    height: int | None = None


@dataclass(frozen=True, kw_only=True)
class ChapterDetailsDTO:
    chapter: int
    privacy_id: int
    name: str | None = None
    extra_number: int | None = None


@dataclass(frozen=True)
class CreateStudioChapterDTO(ChapterDetailsDTO):
    pages: list[ChapterPageDTO]


@dataclass(frozen=True)
class UpdateStudioChapterDTO(ChapterDetailsDTO):
    pages: list[ChapterPageDTO]
