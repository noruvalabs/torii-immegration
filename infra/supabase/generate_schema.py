import re
import pathlib

src = pathlib.Path("C:/Users/Hasib/AppData/Local/Temp/claude/d--tech-torii-immegration/0c645708-da18-4652-8fc7-ed61e1b2e68a/scratchpad/torii_schema.sql").read_text(encoding="utf-8")

# 1. psql meta-commands are not SQL; the Supabase SQL editor sends raw SQL and chokes.
src = re.sub(r"^\\(restrict|unrestrict).*$\n?", "", src, flags=re.M)

# 2. transaction_timeout is PostgreSQL 17+; a failing SET aborts the whole paste.
src = re.sub(r"^SET transaction_timeout = 0;$\n?", "", src, flags=re.M)

# 3. Supabase keeps extensions in the `extensions` schema, not `public`.
src = src.replace(
    "CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;",
    "CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions;",
)
src = src.replace("public.vector", "extensions.vector")

header = r"""-- Torii schema for Supabase  (GENERATED -- do not hand-edit)
--
-- Source of truth is Alembic: apps/api/src/torii_api/db/migrations/versions/*.py at
-- revision 0019. This file was produced by running all 19 migrations against a clean
-- PostgreSQL 17 + pgvector database and dumping the result with:
--
--   pg_dump --schema-only --no-owner --no-privileges --no-comments
--
-- then adjusting exactly three things for Supabase (see infra/supabase/README.md):
--   * removed the \restrict / \unrestrict psql meta-commands (they are not SQL)
--   * removed `SET transaction_timeout` (PostgreSQL 17+ only; Supabase may be older)
--   * moved pgvector into the `extensions` schema, where Supabase keeps extensions
--
-- Regenerate rather than edit -- see the README for the one command that rebuilds it.
--
-- The alembic_version INSERT at the end is load-bearing: pg_dump --schema-only emits the
-- table but not its row, and an unstamped database makes the API replay all 19 migrations
-- over the schema above and fail on the first CREATE TABLE.
--
-- 22 tables, 64 indexes, 39 foreign keys.

"""

# pg_dump --schema-only creates the alembic_version TABLE but not its ROW, because that
# row is data. Without it Alembic sees an unstamped database, concludes nothing has been
# applied, and tries to replay all 19 migrations over a schema that already exists --
# failing on the first CREATE TABLE. Stamping it here is what makes the API's
# `migrate_on_startup` a no-op against this database.
src += """

--
-- Stamp Alembic at the revision this schema was generated from. Without this row the API
-- would attempt to replay every migration over the tables created above.
--

INSERT INTO public.alembic_version (version_num) VALUES ('0019')
    ON CONFLICT (version_num) DO NOTHING;
"""

out = pathlib.Path("infra/supabase/schema.sql")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(header + src, encoding="utf-8")
print(f"wrote {out} ({len(header + src)} bytes)")
