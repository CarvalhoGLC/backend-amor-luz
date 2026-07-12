CREATE TABLE IF NOT EXISTS messages (
  id          SERIAL PRIMARY KEY,
  title       TEXT NOT NULL,
  content     TEXT NOT NULL,
  author      TEXT,
  spirit      TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);