from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from threading import Event
from unittest.mock import Mock
from uuid import uuid4

import pytest
from PIL import Image
from sqlalchemy import delete, select

from kanwoo import db
from kanwoo.chapter.entity import ChapterPagesOptimizationStatus
from kanwoo.chapter.models import Chapter, ChapterPage, OptimizedPage, Page
from kanwoo.chapter.tasks import optimize_chapter_pages
from kanwoo.entities import File
from kanwoo.manga.models import Manga
from kanwoo.models import FileModel, Privacy
from kanwoo.translation.models import Translation


def test_create_uploaded_chapter_and_replay(
    app, authorized_client, profile_id, csrf_access_token, monkeypatch
):
    def assert_chapter_is_committed(chapter_id):
        with db.engine.connect() as connection:
            status = connection.scalar(
                select(Chapter.optimization_status_id).where(Chapter.id == chapter_id)
            )
        assert status == ChapterPagesOptimizationStatus.WAITING.value

    enqueue = Mock(side_effect=assert_chapter_is_committed)
    celery = app.extensions["celery"]
    monkeypatch.setattr(celery.tasks[optimize_chapter_pages.name], "delay", enqueue)
    with app.app_context():
        public_privacy = Privacy(id=2, name="public")
        translation = Translation(
            manga=Manga(slug="upload-flow", name="Upload flow"),
            creator_id=profile_id,
        )
        db.session.add_all([public_privacy, translation])
        db.session.commit()
        privacy_id = public_privacy.id
        url = f"/v1/studio/translations/{translation.id}/chapters"

    size = 128
    storage = Mock()
    storage.get_upload_url.side_effect = lambda key, **_: f"https://storage.example/upload/{key}"
    storage.get_url.side_effect = lambda key: f"https://storage.example/read/{key}"
    storage.exists.return_value = False
    app.container.object_storage.override(storage)

    headers = {"X-CSRF-TOKEN": csrf_access_token, "Idempotency-Key": str(uuid4())}
    tokens = [str(uuid4()), str(uuid4())]
    metadata = [{
        "uuid": token,
        "file_type": "chapter_page",
        "mimetype": "image/png",
        "name": "page.png",
        "file_size": size,
    } for token in tokens]
    urls = authorized_client.post("/v1/uploads", json=metadata, headers=headers)
    assert urls.status_code == 200
    assert urls.json["data"] == [
        {
            "uuid": token,
            "presigned_url": f"https://storage.example/upload/chapters/{token}",
        }
        for token in tokens
    ]
    assert authorized_client.post("/v1/uploads", json=metadata, headers=headers).json == urls.json

    pages = [{"uuid": token, "width": 8, "height": 12 + index}
             for index, token in enumerate(tokens[::-1])]
    body = {"chapter": 1, "privacy_id": privacy_id, "pages": pages}
    with app.app_context():
        FileModel.get(tokens[1]).uploaded_by_profile_id = profile_id + 1
        db.session.commit()
    assert authorized_client.post("/v1/uploads", json=metadata[1:], headers=headers).status_code == 403
    duplicate = authorized_client.post(url, json={**body, "pages": [pages[0], pages[0]]}, headers=headers)
    assert duplicate.status_code == 400
    assert duplicate.json["error"]["code"] == "invalid_chapter"
    assert duplicate.json["error"]["detail"] == {"pages": ["Page UUIDs must be unique."]}
    assert storage.exists.call_count == 0

    missing = authorized_client.post(url, json=body, headers=headers)
    assert missing.status_code == 400
    assert missing.json["error"]["code"] == "chapter_page_not_uploaded"
    storage.exists.reset_mock()

    started = Event()
    release = Event()

    def object_exists(*args, **kwargs):
        started.set()
        assert release.wait(5)
        return True

    def create_chapter():
        with app.test_client() as client:
            for name in ("access_token_cookie", "auth_profile"):
                client.set_cookie(name, authorized_client.get_cookie(name).value)
            return client.post(url, json=body, headers=headers)

    storage.exists.side_effect = object_exists
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(create_chapter)
        try:
            assert started.wait(5)
            concurrent = authorized_client.post(url, json=body, headers=headers)
            assert concurrent.status_code == 409
            assert concurrent.json["error"]["code"] == "operation_in_progress"
        finally:
            release.set()
        first = pending.result(timeout=5)

    replay = authorized_client.post(url, json=body, headers=headers)
    assert first.status_code == replay.status_code == 200
    assert replay.json == first.json
    enqueue.assert_called_once_with(first.json["data"]["id"])
    assert [call.args[0].split("/")[-1] for call in storage.exists.call_args_list] == tokens[::-1]
    assert [page["height"] for page in first.json["data"]["pages"]] == [12, 13]
    assert [page["uuid"] for page in first.json["data"]["pages"]] == tokens[::-1]
    assert first.json["data"]["pages"][0]["link"].endswith(tokens[1])

    changed = authorized_client.post(url, json={**body, "pages": pages[::-1]}, headers=headers)
    assert changed.status_code == 409
    assert changed.json["error"]["code"] == "request_does_not_match"

    duplicate_number = authorized_client.post(
        url, json=body, headers={**headers, "Idempotency-Key": str(uuid4())}
    )
    assert duplicate_number.status_code == 400
    assert duplicate_number.json["error"]["code"] == "chapter_already_exists"
    enqueue.assert_called_once_with(first.json["data"]["id"])

    with Image.new("RGB", (500, 800), "red") as image, BytesIO() as buffer:
        image.save(buffer, format="PNG")
        storage.read.return_value = File("page.png", "image/png", buffer.getvalue())
    chapter_id = first.json["data"]["id"]
    listing = authorized_client.get(url)
    assert listing.status_code == 200
    row = next(row for row in listing.json["data"] if row["id"] == chapter_id)
    assert row == {
        field: first.json["data"][field]
        for field in ("id", "name", "chapter", "extra_number", "privacy")
    }
    storage.save.side_effect = [None, None, OSError("S3 unavailable")]
    with pytest.raises(OSError, match="S3 unavailable"):
        optimize_chapter_pages(chapter_id)

    with app.app_context():
        chapter = db.session.get(Chapter, chapter_id)
        assert chapter.optimization_status_id == ChapterPagesOptimizationStatus.WAITING.value
        assert [page.order for page in chapter.pages] == [0, 1]
        assert all(page.is_orig for page in chapter.pages)
        assert [page.file_uuid for page in chapter.chapter_pages] == tokens[::-1]
        assert db.session.scalars(select(Page).where(Page.chapter_id == chapter_id)).all() == []

    public_url = f"/v1/chapters/{chapter_id}"
    response = authorized_client.get(public_url)
    assert response.status_code == 200
    assert [page["uuid"] for page in response.json["data"]["pages"]] == tokens[::-1]

    storage.save.side_effect = None
    storage.save.reset_mock()
    optimize_chapter_pages(chapter_id)
    optimize_chapter_pages(chapter_id)

    assert storage.save.call_count == 4
    with app.app_context():
        chapter = db.session.get(Chapter, chapter_id)
        assert chapter.optimization_status_id == ChapterPagesOptimizationStatus.COMPLETED.value
        assert [(page.order, page.width, page.height) for page in chapter.pages] == [
            (order, 1000, 800) for order in (0, 1, 0, 1)
        ]
        originals = db.session.scalars(
            select(ChapterPage).where(ChapterPage.chapter_id == chapter_id, ChapterPage.is_orig)
        ).all()
        assert {page.file_uuid for page in originals} == set(tokens)
        assert all(page.file.mimetype == "image/webp" for page in chapter.pages)
        assert db.session.scalars(select(Page).where(Page.chapter_id == chapter_id)).all() == []

    response = authorized_client.get(public_url)
    assert response.status_code == 200
    assert response.json["data"]["pages_count"] == 4
    assert all(page["height"] == 800 for page in response.json["data"]["pages"])

    studio_url = f"/v1/studio/chapters/{chapter_id}"
    update_headers = {**headers, "Idempotency-Key": str(uuid4())}
    studio = authorized_client.get(studio_url)
    assert [page["uuid"] for page in studio.json["data"]["pages"]] == tokens[::-1]
    retained_parts = [page["uuid"] for page in response.json["data"]["pages"][2:]]
    new_token = str(uuid4())
    upload = authorized_client.post("/v1/uploads", json=[{**metadata[0], "uuid": new_token}], headers=headers)
    assert upload.status_code == 200
    update = {
        **body,
        "name": "Updated",
        "extra_number": 0,
        "pages": [
            {"uuid": tokens[0], "is_new": False},
            {"uuid": new_token, "is_new": True, "width": 500, "height": 800},
        ],
    }
    storage.exists.side_effect = None
    storage.exists.return_value = False
    storage.exists.reset_mock()
    enqueue.reset_mock()
    duplicate = authorized_client.put(
        studio_url, json={**update, "pages": [update["pages"][1]] * 2}, headers=update_headers
    )
    assert duplicate.status_code == 400
    assert duplicate.json["error"]["code"] == "invalid_chapter"
    assert duplicate.json["error"]["detail"] == {"pages": ["Page UUIDs must be unique."]}
    assert storage.exists.call_count == 0

    for invalid_page in (
        {"uuid": new_token, "is_new": True, "width": 500},
        {"uuid": tokens[0], "is_new": False, "width": 500, "height": 800},
        {"uuid": tokens[0]},
    ):
        invalid = authorized_client.put(
            studio_url, json={**update, "pages": [invalid_page]}, headers=update_headers
        )
        assert invalid.status_code == 400
        assert invalid.json["error"]["code"] == "invalid_chapter"
    storage.exists.assert_not_called()

    unknown = authorized_client.put(
        studio_url, json={**update, "pages": [{"uuid": new_token, "is_new": False}]}, headers=update_headers
    )
    assert unknown.status_code == 400
    assert unknown.json["error"]["code"] == "invalid_chapter_page"
    storage.exists.assert_not_called()

    missing = authorized_client.put(studio_url, json=update, headers=update_headers)
    assert missing.status_code == 400
    assert missing.json["error"]["code"] == "chapter_page_not_uploaded"
    enqueue.assert_not_called()
    assert authorized_client.get(studio_url).json == studio.json

    def assert_chapter_is_unlocked(*args, **kwargs):
        with db.engine.connect() as connection:
            locked_id = connection.scalar(
                select(Chapter.id).where(Chapter.id == chapter_id).with_for_update(nowait=True)
            )
        assert locked_id == chapter_id
        return True

    storage.exists.reset_mock()
    storage.exists.return_value = True
    saved = authorized_client.put(studio_url, json=update, headers=update_headers)
    storage.exists.side_effect = None
    assert saved.status_code == 200
    assert saved.json["data"]["name"] == "Updated"
    assert saved.json["data"]["extra_number"] == 0
    assert [page["uuid"] for page in saved.json["data"]["pages"]] == [tokens[0], new_token]
    assert authorized_client.put(studio_url, json=update, headers=update_headers).json == saved.json
    enqueue.assert_called_once_with(chapter_id)
    storage.exists.assert_called_once_with(f"chapters/{new_token}")
    pending = authorized_client.get(public_url).json["data"]
    assert [page["uuid"] for page in pending["pages"]] == [tokens[0], new_token]
    assert pending["pages_count"] == 2
    with app.app_context():
        assert set(db.session.scalars(
            select(OptimizedPage.file_uuid).where(OptimizedPage.chapter_id == chapter_id)
        )) == set(retained_parts)

    storage.read.reset_mock()
    storage.save.reset_mock()
    storage.exists.reset_mock()
    enqueue.reset_mock()

    def reorder_during_conversion():
        with app.test_client() as client:
            for name in ("access_token_cookie", "auth_profile"):
                client.set_cookie(name, authorized_client.get_cookie(name).value)
            return client.put(studio_url, json={
                **update, "pages": [
                    {"uuid": new_token, "is_new": False},
                    {"uuid": tokens[0], "is_new": False},
                ],
            }, headers={**headers, "Idempotency-Key": str(uuid4())})

    def save_part(*args, **kwargs):
        if storage.save.call_count == 1:
            assert_chapter_is_unlocked()
            assert pool.submit(reorder_during_conversion).result(timeout=5).status_code == 200

    with ThreadPoolExecutor(max_workers=1) as pool:
        storage.save.side_effect = save_part
        optimize_chapter_pages(chapter_id)
    storage.save.side_effect = None

    storage.read.assert_called_once_with(f"chapters/{new_token}")
    assert storage.save.call_count == 2
    storage.exists.assert_not_called()
    enqueue.assert_not_called()
    assert [page["uuid"] for page in authorized_client.get(studio_url).json["data"]["pages"]] == [
        new_token, tokens[0],
    ]
    response = authorized_client.get(public_url)
    optimized = [page["uuid"] for page in response.json["data"]["pages"]]
    assert optimized[2:] == retained_parts

    retained_uuid = response.json["data"]["pages"][-1]["uuid"]
    with app.app_context():
        chapter = db.session.get(Chapter, chapter_id)
        assert chapter.optimization_status_id == ChapterPagesOptimizationStatus.COMPLETED.value
        assert all(page.process_status_id == ChapterPagesOptimizationStatus.COMPLETED.value
                   for page in chapter.chapter_pages)
        assert [page.order for page in chapter.chapter_pages] == [0, 1]
        assert [page.order for page in chapter.pages] == [0, 1, 0, 1]
        service = app.container.chapter_container.chapter_service()
        service.system_update_pages(
            chapter, [storage.read.return_value], ["page.png", retained_uuid]
        )
        assert [page.order for page in chapter.pages] == [0, 1, 0]
        assert chapter.pages[-1].source_page.order == 2
        assert chapter.pages[-1].file_uuid == retained_uuid
        assert all(isinstance(page, ChapterPage) for page in chapter.pages[:-1])
        assert isinstance(chapter.pages[-1], OptimizedPage)
        assert db.session.scalars(select(Page).where(Page.chapter_id == chapter_id)).all() == []

        db.session.execute(delete(ChapterPage).where(
            ChapterPage.chapter_id == chapter_id, ChapterPage.file_uuid == tokens[0],
        ))
        db.session.commit()
        assert db.session.scalars(
            select(OptimizedPage.file_uuid).where(OptimizedPage.chapter_id == chapter_id)
        ).all() == []


def test_studio_updates_only_chapter_pages_without_object_storage(
    app, authorized_client, profile_id, privacy_id, csrf_access_token
):
    tokens = [str(uuid4()) for _ in range(3)]
    legacy_token = str(uuid4())
    completed = ChapterPagesOptimizationStatus.COMPLETED.value
    with app.app_context():
        chapter = Chapter(
            chapter=1,
            creator_id=profile_id,
            privacy_id=privacy_id,
            chapter_pages=[
                ChapterPage(
                    file=FileModel(uuid=token, path=f"chapters/{token}", mimetype="image/webp"),
                    width=100,
                    height=100,
                    order=order,
                    process_status_id=completed,
                )
                for order, token in enumerate(tokens)
            ],
            legacy_pages=[
                Page(uuid=legacy_token, path=f"pages/{legacy_token}.webp", width=100, height=100, order=3)
            ],
        )
        db.session.add(chapter)
        db.session.commit()
        chapter_id = chapter.id

    app.container.object_storage.override(None)
    url = f"/v1/studio/chapters/{chapter_id}"
    before = authorized_client.get(url)
    assert before.status_code == 200
    assert [page["uuid"] for page in before.json["data"]["pages"]] == tokens
    assert before.json["data"]["pages_count"] == len(tokens)

    rejected = authorized_client.put(
        url,
        json={
            "chapter": 1,
            "privacy_id": privacy_id,
            "pages": [{"uuid": legacy_token, "is_new": False}],
        },
        headers={"X-CSRF-TOKEN": csrf_access_token, "Idempotency-Key": str(uuid4())},
    )
    assert rejected.status_code == 400
    assert rejected.json["error"]["code"] == "invalid_chapter_page"
    assert authorized_client.get(url).json == before.json

    response = authorized_client.put(
        url,
        json={
            "chapter": 1,
            "privacy_id": privacy_id,
            "pages": [{"uuid": token, "is_new": False} for token in (tokens[2], tokens[0])],
        },
        headers={"X-CSRF-TOKEN": csrf_access_token, "Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 200
    assert [page["uuid"] for page in response.json["data"]["pages"]] == [tokens[2], tokens[0]]
    assert response.json["data"]["pages_count"] == 2
    with app.app_context():
        chapter = db.session.get(Chapter, chapter_id)
        assert chapter.optimization_status_id == completed
        assert [page.uuid for page in chapter.chapter_pages] == [tokens[2], tokens[0]]
        assert [page.uuid for page in chapter.pages] == [tokens[2], tokens[0], legacy_token]
        assert not db.session.get(Page, legacy_token).is_deleted
