import pytest
from sqlalchemy.orm import Session

from kanwoo import db
from kanwoo.chapter.exceptions import ChapterWithNumberAlreadyExists
from kanwoo.chapter.models import Chapter
from kanwoo.chapter.repositories import ChapterRepository
from kanwoo.manga.models import Manga
from kanwoo.translation.models import Translation
from kanwoo.unit_of_work import UnitOfWork


def test_create_chapter_rejects_duplicate_after_both_checks_pass(app, profile_id):
    with app.app_context(), Session(db.engine) as first, Session(db.engine) as second:
        with UnitOfWork(first):
            translation = Translation(manga=Manga(slug="chapter-race", name="Chapter race"))
            first.add(translation)
            first.flush()
            translation_id = translation.id

        first_repo = ChapterRepository(first)
        second_repo = ChapterRepository(second)

        assert not first_repo.check_chapter_with_number(translation_id, 1, None)
        assert not second_repo.check_chapter_with_number(translation_id, 1, None)

        with UnitOfWork(first):
            first_repo.create_chapter(
                Chapter(translation_id=translation_id, chapter=1, creator_id=profile_id)
            )

        with pytest.raises(ChapterWithNumberAlreadyExists):
            with UnitOfWork(second):
                second_repo.create_chapter(
                    Chapter(translation_id=translation_id, chapter=1, creator_id=profile_id)
                )

        with UnitOfWork(second):
            assert second_repo.check_chapter_with_number(translation_id, 1, None)
            second_repo.create_chapter(
                Chapter(
                    translation_id=translation_id,
                    chapter=1,
                    extra_number=1,
                    creator_id=profile_id,
                )
            )
