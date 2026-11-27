"""Переведены страницы глав на ChapterPage

Revision ID: c79c8cb813b6
Revises: ecf448fd0143
Create Date: 2026-11-26 23:08:22.804318

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c79c8cb813b6'
down_revision = 'ecf448fd0143'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('chapter', schema=None) as batch_op:
        batch_op.add_column(sa.Column('optimization_status_id', sa.Integer(), server_default='2', nullable=False))
        batch_op.create_check_constraint(
            'ck_chapter_optimization_status', 'optimization_status_id IN (1, 2)'
        )

    with op.batch_alter_table('chapter_page', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_orig', sa.Boolean(), server_default='false', nullable=False))
        batch_op.add_column(sa.Column('process_status_id', sa.Integer(), server_default='2', nullable=False))
        batch_op.alter_column(
            'file_uuid',
            existing_type=sa.Integer(),
            type_=sa.String(),
            existing_nullable=False,
            postgresql_using='file_uuid::varchar',
        )
        batch_op.create_foreign_key('fk_chapter_page_file_uuid', 'file', ['file_uuid'], ['uuid'])
        batch_op.create_check_constraint('ck_chapter_page_process_status', 'process_status_id IN (1, 2)')

    op.create_table(
        'optimized_page',
        sa.Column('chapter_id', sa.Integer(), primary_key=True),
        sa.Column('source_uuid', sa.String(), primary_key=True),
        sa.Column('file_uuid', sa.String(), sa.ForeignKey('file.uuid'), primary_key=True),
        sa.Column('width', sa.Integer(), nullable=False),
        sa.Column('height', sa.Integer(), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['chapter_id', 'source_uuid'], ['chapter_page.chapter_id', 'chapter_page.file_uuid'],
            name='fk_optimized_page_source', ondelete='CASCADE',
        ),
    )

    with op.batch_alter_table('file', schema=None) as batch_op:
        batch_op.add_column(sa.Column('uploaded_by_profile_id', sa.Integer(), nullable=True))

    op.execute(
        """
        CREATE TEMP TABLE chapter_page_backfill ON COMMIT DROP AS
        SELECT
            p.*,
            CASE
                WHEN row_number() OVER (PARTITION BY p.chapter_id, p.path ORDER BY p."order", p.uuid) = 1
                THEN coalesce(upload.uuid, p.uuid)
                ELSE p.uuid
            END AS stored_file_uuid,
            p.path NOT LIKE 'chapters/optimized/%' AS is_orig
        FROM page AS p
        LEFT JOIN file AS upload
            ON upload.uuid = split_part(p.path, '/', 2)
            AND upload.path = p.path
        WHERE p.chapter_id IS NOT NULL AND p.is_deleted IS FALSE
            AND (p.path LIKE 'chapters/%' OR p.path LIKE 'chapter-originals/%')
        """
    )
    op.execute(
        """
        INSERT INTO file (uuid, path, filename, mimetype, created_at, is_deleted)
        SELECT DISTINCT ON (stored_file_uuid)
            stored_file_uuid, path, orig_filename,
            CASE
                WHEN NOT is_orig OR lower(orig_filename) LIKE '%.webp' THEN 'image/webp'
                WHEN lower(orig_filename) LIKE '%.png' THEN 'image/png'
                WHEN lower(orig_filename) LIKE '%.jpg' OR lower(orig_filename) LIKE '%.jpeg' THEN 'image/jpeg'
                WHEN lower(orig_filename) LIKE '%.gif' THEN 'image/gif'
                ELSE 'application/octet-stream'
            END,
            uploaded_at, false
        FROM chapter_page_backfill
        ORDER BY stored_file_uuid, uploaded_at, uuid
        ON CONFLICT (uuid) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO chapter_page (chapter_id, file_uuid, width, height, "order", is_orig, process_status_id)
        SELECT chapter_id, stored_file_uuid, width, height, "order", is_orig, CASE WHEN is_orig THEN 1 ELSE 2 END
        FROM chapter_page_backfill
        ON CONFLICT (chapter_id, file_uuid) DO NOTHING
        """
    )
    op.execute(
        """
        UPDATE chapter SET optimization_status_id = 1
        WHERE id IN (SELECT chapter_id FROM chapter_page_backfill WHERE is_orig)
        """
    )
    op.execute(
        """
        UPDATE page SET is_deleted = true
        WHERE uuid IN (SELECT uuid FROM chapter_page_backfill)
        """
    )


def downgrade():
    op.execute(
        """
        INSERT INTO page (uuid, chapter_id, path, orig_filename, width, height, "order", uploaded_at, is_deleted)
        SELECT gen_random_uuid()::varchar, part.chapter_id, file.path, file.filename,
            part.width, part.height, part."order", file.created_at, false
        FROM optimized_page AS part
        JOIN file ON file.uuid = part.file_uuid
        """
    )
    op.drop_table('optimized_page')

    op.execute(
        """
        UPDATE page AS p
        SET width = cp.width, height = cp.height, "order" = cp."order",
            is_deleted = cp.is_orig AND cp.process_status_id = 2
        FROM chapter_page AS cp
        JOIN file ON file.uuid = cp.file_uuid
        WHERE p.chapter_id = cp.chapter_id AND p.path = file.path AND p.is_deleted IS FALSE
        """
    )
    op.execute(
        """
        INSERT INTO page (uuid, chapter_id, path, orig_filename, width, height, "order", uploaded_at, is_deleted)
        SELECT gen_random_uuid()::varchar, cp.chapter_id, file.path, file.filename, cp.width, cp.height,
            cp."order", file.created_at, false
        FROM chapter_page AS cp
        JOIN file ON file.uuid = cp.file_uuid
        WHERE (NOT cp.is_orig OR cp.process_status_id = 1)
            AND NOT EXISTS (
                SELECT 1 FROM page AS p
                WHERE p.chapter_id = cp.chapter_id AND p.path = file.path AND p.is_deleted IS FALSE
            )
        """
    )
    op.execute("DELETE FROM chapter_page WHERE file_uuid !~ '^-?[0-9]+$'")

    with op.batch_alter_table('file', schema=None) as batch_op:
        batch_op.drop_column('uploaded_by_profile_id')

    with op.batch_alter_table('chapter_page', schema=None) as batch_op:
        batch_op.drop_constraint('ck_chapter_page_process_status', type_='check')
        batch_op.drop_constraint('fk_chapter_page_file_uuid', type_='foreignkey')
        batch_op.alter_column(
            'file_uuid',
            existing_type=sa.String(),
            type_=sa.Integer(),
            existing_nullable=False,
            postgresql_using='file_uuid::integer',
        )
        batch_op.drop_column('is_orig')
        batch_op.drop_column('process_status_id')

    with op.batch_alter_table('chapter', schema=None) as batch_op:
        batch_op.drop_constraint('ck_chapter_optimization_status', type_='check')
        batch_op.drop_column('optimization_status_id')
