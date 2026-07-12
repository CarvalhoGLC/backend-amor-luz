const { sql } = require('@vercel/postgres');

// Em ambiente serverless não há disco persistente, então o banco de dados
// vive em um Postgres hospedado (ex.: Vercel Postgres, Neon, Supabase).
// A criação da tabela e das colunas é idempotente (IF NOT EXISTS), o que
// permite evoluir o schema (como adicionar image_url) sem um passo de
// migração separado — o próprio código garante o estado mais atual.

let schemaReady = null;

async function ensureSchema() {
  if (!schemaReady) {
    schemaReady = (async () => {
      await sql`
        CREATE TABLE IF NOT EXISTS messages (
          id          SERIAL PRIMARY KEY,
          title       TEXT NOT NULL,
          content     TEXT NOT NULL,
          author      TEXT,
          spirit      TEXT,
          created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        );
      `;
      // Adicionado depois da versão original — coluna opcional para a URL
      // da imagem exibida no topo do card da mensagem.
      await sql`ALTER TABLE messages ADD COLUMN IF NOT EXISTS image_url TEXT;`;

      // Seção de vídeos do YouTube indicados pelo mantenedor.
      await sql`
        CREATE TABLE IF NOT EXISTS videos (
          id          SERIAL PRIMARY KEY,
          title       TEXT NOT NULL,
          video_id    TEXT NOT NULL,
          youtube_url TEXT NOT NULL,
          description TEXT,
          created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        );
      `;
    })();
  }
  await schemaReady;
}

module.exports = { sql, ensureSchema };