const { sql } = require('@vercel/postgres');

// Em ambiente serverless não há disco persistente, então o banco de dados
// vive em um Postgres hospedado (ex.: Vercel Postgres, Neon, Supabase).
// A criação da tabela é idempotente (IF NOT EXISTS) e é garantida antes de
// qualquer consulta, sem depender de um passo de migração separado.

let schemaReady = null;

async function ensureSchema() {
  if (!schemaReady) {
    schemaReady = sql`
      CREATE TABLE IF NOT EXISTS messages (
        id          SERIAL PRIMARY KEY,
        title       TEXT NOT NULL,
        content     TEXT NOT NULL,
        author      TEXT,
        spirit      TEXT,
        created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
      );
    `;
  }
  await schemaReady;
}

module.exports = { sql, ensureSchema };