// Gera o hash bcrypt de uma senha para colocar em MAINTAINER_PASSWORD_HASH no .env
//
// Uso:
//   node scripts/hash-password.js "minha-senha-secreta"
 
const bcrypt = require('bcryptjs');
 
const password = process.argv[2];
 
if (!password) {
  console.error('Uso: node scripts/hash-password.js "sua-senha"');
  process.exit(1);
}
 
const hash = bcrypt.hashSync(password, 12);
console.log('\nAdicione esta linha ao seu arquivo .env:\n');
console.log(`MAINTAINER_PASSWORD_HASH=${hash}\n`);