import json
from importlib import import_module
from io import BytesIO

from alembic.migration import MigrationContext
from alembic.operations import Operations
from PIL import Image

from kanwoo import db, file_storage
from kanwoo.manga.models import Adult, Genre, Manga, Status, Type
from kanwoo.models import FileModel, Language
from kanwoo.moderation.models import ModerationStatusType
from kanwoo.profile.models import Profile


def image_part(filename):
    image = BytesIO()
    with Image.new("RGB", (24, 32)) as source:
        source.save(image, format="JPEG")
    image.seek(0)
    return image, filename, "image/jpeg"


def write(client, method, path, csrf_token, data, **files):
    return client.open(
        path,
        method=method,
        headers={"X-CSRF-TOKEN": csrf_token},
        content_type="multipart/form-data",
        data={"data": json.dumps(data), **files},
    )


def test_studio_manga_media(app, authorized_client, csrf_access_token, privacy_id, monkeypatch, tmp_path):
    monkeypatch.setattr(file_storage, "upload_dir", tmp_path)
    with app.app_context():
        db.session.add_all([
            Adult(id=1, name="Adult"),
            Genre(id=1, name="Action"),
            Genre(id=2, name="Comedy"),
            Status(id=1, name="Status"),
            Type(id=1, name="Type"),
            Language(id=1, name="English"),
            ModerationStatusType(id=3, name="Moderation"),
        ])
        db.session.commit()

    details = {
        "name": "Test manga", "description": "", "genres_ids": [1, 2],
        "year": 2025, "adult_id": 1, "status_id": 1, "type_id": 1, "privacy_id": privacy_id,
    }
    response = write(
        authorized_client, "POST", "/v1/studio/profiles/test/manga", csrf_access_token, details,
        poster=image_part("poster.jpg"), background=image_part("background.jpg"),
    )
    assert response.status_code == 200, response.get_json()
    slug = response.get_json()["data"]["slug"]

    with app.app_context():
        manga = db.session.scalar(db.select(Manga).filter_by(slug=slug))
        assert {genre.id for genre in manga.genres} == {1, 2}
        assert len(manga.poster.files) == 4
        poster_ids = {version.file_uuid for version in manga.poster.files}
        assert all(version.file.filename == "poster.jpg" for version in manga.poster.files)
        assert all((tmp_path / version.file.path).is_file() for version in manga.poster.files)
        background_id = manga.background.file_uuid

    response = write(
        authorized_client, "PUT", f"/v1/studio/manga/{slug}", csrf_access_token,
        {
            **details, "slug": slug, "name_translations": [{"lang": 1, "name": "English title"}],
            "background_action": "delete", "promo_logo_action": "update",
        },
        promo_logo=image_part("logo.jpg"),
    )
    assert response.status_code == 200, response.get_json()

    with app.app_context():
        manga = db.session.scalar(db.select(Manga).filter_by(slug=slug))
        assert {version.file_uuid for version in manga.poster.files} == poster_ids
        assert manga.background is None
        assert FileModel.get(background_id).is_deleted
        assert manga.promo_logo.file.filename == "logo.jpg"
        assert manga.name_translations[0].name == "English title"
    assert len(list((tmp_path / "manga").iterdir())) == 6


def test_studio_profile_avatar(app, authorized_client, csrf_access_token, profile_id, monkeypatch, tmp_path):
    monkeypatch.setattr(file_storage, "upload_dir", tmp_path)
    path = "/v1/studio/profiles/test"
    details = {"name": "Test profile", "slug": "test", "links": [{"name": "Site", "link": "https://example.com"}]}

    for data in ("[1]", '{"name":'):
        response = authorized_client.put(
            path, headers={"X-CSRF-TOKEN": csrf_access_token}, content_type="multipart/form-data",
            data={"data": data},
        )
        assert response.status_code == 400
    response = write(authorized_client, "PUT", path, csrf_access_token, {**details, "avatar_action": "update"})
    assert response.status_code == 400
    assert not (tmp_path / "profiles").exists()

    response = write(
        authorized_client, "PUT", path, csrf_access_token, {**details, "avatar_action": "update"},
        avatar=image_part("avatar.jpg"),
    )
    assert response.status_code == 200, response.get_json()
    with app.app_context():
        profile = Profile.get(profile_id)
        file_uuid = profile.avatar.file_uuid
        assert profile.avatar.file.filename == "avatar.jpg"
        assert (tmp_path / profile.avatar.file.path).is_file()
        assert profile.links[0].name == "Site"

    response = write(
        authorized_client, "PUT", path, csrf_access_token, {**details, "avatar_action": "update"},
        avatar=image_part("replacement.jpg"),
    )
    assert response.status_code == 200, response.get_json()
    with app.app_context():
        assert FileModel.get(file_uuid).is_deleted
        avatar = Profile.get(profile_id).avatar
        file_uuid = avatar.file_uuid
        assert avatar.file.filename == "replacement.jpg"

    response = write(authorized_client, "PUT", path, csrf_access_token, {**details, "avatar_action": "remove"})
    assert response.status_code == 200, response.get_json()
    with app.app_context():
        assert Profile.get(profile_id).avatar is None
        assert FileModel.get(file_uuid).is_deleted


def test_studio_media_migration_preserves_legacy_paths(app):
    migration = import_module("migrations.versions.6afe9b67d741_link_studio_media_to_files")
    with app.app_context(), db.engine.connect() as connection, connection.begin():
        connection.exec_driver_sql("""
            CREATE TEMP TABLE file (
                uuid varchar PRIMARY KEY, path varchar NOT NULL, filename varchar,
                mimetype varchar NOT NULL, created_at timestamp NOT NULL, is_deleted boolean NOT NULL
            ) ON COMMIT DROP
        """)
        for table in migration.MEDIA_TABLES:
            connection.exec_driver_sql(f"""
                CREATE TEMP TABLE {table} (
                    uuid varchar PRIMARY KEY, path varchar, orig_filename varchar,
                    uploaded_at timestamp NOT NULL, is_deleted boolean
                ) ON COMMIT DROP
            """)
            connection.exec_driver_sql(
                f"INSERT INTO {table} VALUES (%s, %s, %s, '2024-07-01', %s)",
                ("legacy", f"{table}/stored.jpg", "original.png", table == "manga_background"),
            )

        context = MigrationContext.configure(connection)
        with Operations.context(context):
            migration.upgrade()

        files = connection.exec_driver_sql("SELECT path, filename, is_deleted FROM file").all()
        assert len(files) == len(migration.MEDIA_TABLES)
        assert all(filename == "original.png" for _, filename, _ in files)
        assert {path for path, _, deleted in files if deleted} == {"manga_background/stored.jpg"}
        for table in migration.MEDIA_TABLES:
            assert connection.exec_driver_sql(f"""
                SELECT file.path FROM {table} JOIN file ON {table}.file_uuid = file.uuid
            """).scalar_one() == f"{table}/stored.jpg"

        with Operations.context(context):
            migration.downgrade()
        assert connection.exec_driver_sql("SELECT count(*) FROM file").scalar_one() == 0
        assert connection.exec_driver_sql(
            "SELECT path FROM profile_avatar WHERE uuid = 'legacy'"
        ).scalar_one() == "profile_avatar/stored.jpg"
