// Ponto de entrada da função serverless na Vercel.
// Todo o roteamento de fato acontece dentro do app Express em ../server.js;
// este arquivo só o expõe no formato que a Vercel espera encontrar em /api.
module.exports = require('./server');