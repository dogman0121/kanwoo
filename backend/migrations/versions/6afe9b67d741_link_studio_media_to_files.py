"""Link manga media and profile avatars to FileModel."""

from alembic import op
import sqlalchemy as sa


revision = "6afe9b67d741"
down_revision = "c79c8cb813b6"
branch_labels = None
depends_on = None

MEDIA_TABLES = (
    "manga_poster_file",
    "manga_background",
    "manga_promo_name",
    "manga_promo_logo",
    "manga_promo_background",
    "profile_avatar",
)


def upgrade():
    for table in MEDIA_TABLES:
        op.add_column(table, sa.Column("file_uuid", sa.String(), nullable=True))
        # Namespace old media IDs by table because they were unique only within each table.
        op.execute(f"""
            UPDATE {table}
            SET file_uuid = CAST(CAST(md5('{revision}/{table}/' || uuid) AS uuid) AS varchar)
        """)
        null_deleted = "false" if table == "profile_avatar" else "true"
        op.execute(f"""
            INSERT INTO file (uuid, path, filename, mimetype, created_at, is_deleted)
            SELECT file_uuid, coalesce(path, ''), orig_filename,
                CASE
                    WHEN lower(path) LIKE '%.webp' THEN 'image/webp'
                    WHEN lower(path) LIKE '%.jpg' OR lower(path) LIKE '%.jpeg' THEN 'image/jpeg'
                    WHEN lower(path) LIKE '%.png' THEN 'image/png'
                    WHEN lower(path) LIKE '%.gif' THEN 'image/gif'
                    ELSE 'application/octet-stream'
                END,
                uploaded_at, coalesce(is_deleted, {null_deleted})
            FROM {table}
        """)
        op.alter_column(table, "file_uuid", existing_type=sa.String(), nullable=False)
        op.create_foreign_key(f"fk_{table}_file_uuid", table, "file", ["file_uuid"], ["uuid"])
        for column in ("path", "orig_filename", "uploaded_at"):
            op.drop_column(table, column)


def downgrade():
    for table in MEDIA_TABLES:
        op.add_column(table, sa.Column("path", sa.String(), nullable=True))
        op.add_column(table, sa.Column("orig_filename", sa.String(), nullable=True))
        op.add_column(table, sa.Column("uploaded_at", sa.DateTime(), nullable=True))
        op.execute(f"""
            UPDATE {table} AS media
            SET path = nullif(file.path, ''), orig_filename = file.filename,
                uploaded_at = file.created_at
            FROM file
            WHERE file.uuid = media.file_uuid
        """)
        op.alter_column(table, "uploaded_at", existing_type=sa.DateTime(), nullable=False)
        op.drop_constraint(f"fk_{table}_file_uuid", table, type_="foreignkey")
        op.execute(f"DELETE FROM file USING {table} WHERE file.uuid = {table}.file_uuid")
        op.drop_column(table, "file_uuid")
