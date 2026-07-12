require('dotenv').config();

const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');

const { sql, ensureSchema } = require('./db');

const {
  JWT_SECRET,
  TOKEN_EXPIRES_IN = '12h',
  MAINTAINER_PASSWORD_HASH,
  CORS_ORIGIN,
} = process.env;

const app = express();

app.use(helmet());
app.use(express.json({ limit: '100kb' }));
app.use(
  cors({
    origin: CORS_ORIGIN ? CORS_ORIGIN.split(',').map((s) => s.trim()) : '*',
  })
);

// Garante que as variáveis obrigatórias existam antes de atender qualquer
// rota. Em vez de derrubar o processo com `process.exit` (o que crasha a
// função serverless de forma abrupta), respondemos com um 500 controlado e
// uma mensagem clara nos logs — mais fácil de diagnosticar na Vercel.
app.use((req, res, next) => {
  if (!JWT_SECRET || !MAINTAINER_PASSWORD_HASH) {
    console.error(
      'Configuração ausente: defina JWT_SECRET e MAINTAINER_PASSWORD_HASH nas variáveis de ambiente do projeto na Vercel.'
    );
    return res.status(500).json({
      error: 'Configuração do servidor incompleta. Verifique as variáveis de ambiente.',
    });
  }
  next();
});

/* ---------------------------------------------------------
   Middleware de autenticação — protege rotas de escrita
--------------------------------------------------------- */
function requireAuth(req, res, next) {
  const header = req.headers.authorization || '';
  const token = header.startsWith('Bearer ') ? header.slice(7) : null;

  if (!token) {
    return res.status(401).json({ error: 'Token ausente.' });
  }

  try {
    req.auth = jwt.verify(token, JWT_SECRET);
    next();
  } catch (err) {
    return res.status(401).json({ error: 'Token inválido ou expirado.' });
  }
}

/* ---------------------------------------------------------
   Validação simples dos campos da mensagem
--------------------------------------------------------- */
function validateMessage(body) {
  const errors = [];
  const title = (body.title || '').trim();
  const content = (body.content || '').trim();
  const author = (body.author || '').trim();
  const spirit = (body.spirit || '').trim();

  if (!title) errors.push('O título é obrigatório.');
  if (title.length > 120) errors.push('O título deve ter até 120 caracteres.');
  if (!content) errors.push('A mensagem é obrigatória.');
  if (content.length > 4000) errors.push('A mensagem deve ter até 4000 caracteres.');
  if (author.length > 60) errors.push('O nome do autor deve ter até 60 caracteres.');
  if (spirit.length > 60) errors.push('O nome do mentor espiritual deve ter até 60 caracteres.');

  return { errors, data: { title, content, author, spirit } };
}

// Middleware auxiliar para não repetir try/catch em toda rota assíncrona.
function asyncRoute(handler) {
  return (req, res, next) => handler(req, res, next).catch(next);
}

/* ---------------------------------------------------------
   Rotas públicas
--------------------------------------------------------- */

// Lista todas as mensagens, mais recentes primeiro.
app.get(
  '/api/messages',
  asyncRoute(async (req, res) => {
    await ensureSchema();
    const { rows } = await sql`
      SELECT * FROM messages ORDER BY created_at DESC
    `;
    res.json(rows);
  })
);

// Login do mantenedor — limitado a 5 tentativas a cada 10 minutos por IP.
// Observação: em ambiente serverless, o estado desse limitador vive em
// memória de cada instância da função, então o limite é "best effort" (uma
// nova instância fria reseta a contagem). Para um limite garantido entre
// instâncias, use um contador externo, ex.: Upstash Redis com @upstash/ratelimit.
const loginLimiter = rateLimit({
  windowMs: 10 * 60 * 1000,
  max: 5,
  message: { error: 'Muitas tentativas. Aguarde alguns minutos e tente novamente.' },
});

app.post('/api/auth/login', loginLimiter, (req, res) => {
  const { password } = req.body || {};

  if (!password) {
    return res.status(400).json({ error: 'Informe a senha.' });
  }

  const valid = bcrypt.compareSync(password, MAINTAINER_PASSWORD_HASH);
  if (!valid) {
    return res.status(401).json({ error: 'Senha incorreta.' });
  }

  const token = jwt.sign({ role: 'maintainer' }, JWT_SECRET, {
    expiresIn: TOKEN_EXPIRES_IN,
  });

  res.json({ token });
});

/* ---------------------------------------------------------
   Rotas protegidas (requerem o token do mantenedor)
--------------------------------------------------------- */

app.post(
  '/api/messages',
  requireAuth,
  asyncRoute(async (req, res) => {
    const { errors, data } = validateMessage(req.body || {});
    if (errors.length) {
      return res.status(400).json({ error: errors.join(' ') });
    }

    await ensureSchema();
    const { rows } = await sql`
      INSERT INTO messages (title, content, author, spirit)
      VALUES (${data.title}, ${data.content}, ${data.author}, ${data.spirit})
      RETURNING *
    `;
    res.status(201).json(rows[0]);
  })
);

app.put(
  '/api/messages/:id',
  requireAuth,
  asyncRoute(async (req, res) => {
    const { id } = req.params;
    await ensureSchema();

    const existing = await sql`SELECT * FROM messages WHERE id = ${id}`;
    if (existing.rows.length === 0) {
      return res.status(404).json({ error: 'Mensagem não encontrada.' });
    }

    const { errors, data } = validateMessage(req.body || {});
    if (errors.length) {
      return res.status(400).json({ error: errors.join(' ') });
    }

    const { rows } = await sql`
      UPDATE messages
      SET title = ${data.title}, content = ${data.content},
          author = ${data.author}, spirit = ${data.spirit}
      WHERE id = ${id}
      RETURNING *
    `;
    res.json(rows[0]);
  })
);

app.delete(
  '/api/messages/:id',
  requireAuth,
  asyncRoute(async (req, res) => {
    const { id } = req.params;
    await ensureSchema();

    const existing = await sql`SELECT * FROM messages WHERE id = ${id}`;
    if (existing.rows.length === 0) {
      return res.status(404).json({ error: 'Mensagem não encontrada.' });
    }

    await sql`DELETE FROM messages WHERE id = ${id}`;
    res.status(204).send();
  })
);

// Handler de erro genérico — evita que uma exceção não tratada derrube a
// função sem responder nada ao cliente (o que aparece como 500 sem corpo).
app.use((err, req, res, next) => {
  console.error('Erro não tratado:', err);
  res.status(500).json({ error: 'Erro interno do servidor.' });
});

/* ---------------------------------------------------------
   Exportação e execução local
--------------------------------------------------------- */
// Na Vercel, este módulo é importado por api/index.js e tratado como uma
// função serverless — não chamamos app.listen() nesse caso. Localmente
// (`npm start`), rodamos como um servidor Express comum de sempre.
if (!process.env.VERCEL) {
  const PORT = process.env.PORT || 3000;
  app.listen(PORT, () => {
    console.log(`Backend do Amor & Luz rodando em http://localhost:${PORT}`);
  });
}

module.exports = app;