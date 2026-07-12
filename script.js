// ATENÇÃO: troque pela URL do seu backend na Vercel (o domínio da API, não o do site).
const API_BASE_URL = 'https://amor-luz.vercel.app';

// Token do mantenedor, guardado só em memória — some ao recarregar a página,
// exigindo login novamente (comportamento intencional).
let authToken = null;

const featured = [
  { text: '“Fora da caridade não há salvação.”', attr: 'Allan Kardec — O Evangelho Segundo o Espiritismo' },
  { text: '“Amai-vos e instrui-vos.”', attr: 'O Evangelho Segundo o Espiritismo' },
  { text: '“O tempo é o senhor absoluto, o lapidador supremo das arestas mais duras.”', attr: 'Espírito Emmanuel, por Chico Xavier' },
];
document.getElementById('featuredText').textContent = featured[Math.floor(Math.random()*featured.length)].text;
document.getElementById('featuredAttr').textContent = featured.find(f=>f.text===document.getElementById('featuredText').textContent).attr;

function escapeHtml(str){
  return str.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function formatDate(iso){
  try{
    const d = new Date(iso);
    return d.toLocaleDateString('pt-BR', { day:'2-digit', month:'long', year:'numeric' });
  }catch(e){ return ''; }
}

async function loadMessages(){
  try{
    const res = await fetch(`${API_BASE_URL}/api/messages`);
    if(!res.ok) return [];
    const arr = await res.json();
    return Array.isArray(arr) ? arr : [];
  }catch(e){
    return [];
  }
}

let carouselIndex = 0;

function renderMural(list){
  const container = document.getElementById('muralContent');
  const count = document.getElementById('muralCount');
  count.textContent = list.length === 0 ? '' :
    (list.length === 1 ? '1 mensagem' : list.length + ' mensagens');

  if(list.length === 0){
    container.innerHTML = '<div class="empty-state"><p>Ainda não há mensagens neste mural. Em breve o mantenedor publicará a primeira palavra de luz.</p></div>';
    return;
  }

  // A API já devolve as mensagens mais recentes primeiro.
  const sorted = list;
  if(carouselIndex > sorted.length - 1) carouselIndex = 0;

  const slides = sorted.map(m => `
    <div class="carousel-slide">
      <article class="msg-card">
        <h3 class="msg-title">${escapeHtml(m.title)}</h3>
        <p class="msg-body">${escapeHtml(m.content)}</p>
        <div class="msg-meta">
          <span class="who">De <b>${escapeHtml(m.author || 'Anônimo')}</b><br>${formatDate(m.created_at)}</span>
          ${m.spirit ? `<span class="spirit">${escapeHtml(m.spirit)}</span>` : ''}
        </div>
      </article>
    </div>
  `).join('');

  const dots = sorted.map((_, i) => `<button class="carousel-dot${i===carouselIndex?' active':''}" data-index="${i}" aria-label="Ir para mensagem ${i+1}"></button>`).join('');

  container.innerHTML = `
    <div class="carousel">
      <button class="carousel-btn prev" id="carPrev" aria-label="Mensagem anterior">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 6l-6 6 6 6"/></svg>
      </button>
      <div class="carousel-viewport">
        <div class="carousel-track" id="carTrack">${slides}</div>
      </div>
      <button class="carousel-btn next" id="carNext" aria-label="Próxima mensagem">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 6l6 6-6 6"/></svg>
      </button>
    </div>
    <div class="carousel-dots" id="carDots">${dots}</div>
  `;

  applyCarouselPosition(sorted.length);

  document.getElementById('carPrev').addEventListener('click', () => moveCarousel(-1, sorted.length));
  document.getElementById('carNext').addEventListener('click', () => moveCarousel(1, sorted.length));
  document.getElementById('carDots').querySelectorAll('.carousel-dot').forEach(btn => {
    btn.addEventListener('click', () => {
      carouselIndex = parseInt(btn.dataset.index, 10);
      applyCarouselPosition(sorted.length);
    });
  });
}

function applyCarouselPosition(total){
  const track = document.getElementById('carTrack');
  if(!track) return;
  track.style.transform = `translateX(-${carouselIndex * 100}%)`;
  document.getElementById('carPrev').disabled = carouselIndex === 0;
  document.getElementById('carNext').disabled = carouselIndex === total - 1;
  document.querySelectorAll('.carousel-dot').forEach((d, i) => d.classList.toggle('active', i === carouselIndex));
}

function moveCarousel(delta, total){
  carouselIndex = Math.max(0, Math.min(total - 1, carouselIndex + delta));
  applyCarouselPosition(total);
}

async function refreshMural(){
  const list = await loadMessages();
  renderMural(list);
  return list;
}

document.getElementById('msgForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const title = document.getElementById('f-title').value.trim();
  const content = document.getElementById('f-content').value.trim();
  const author = document.getElementById('f-author').value.trim();
  const spirit = document.getElementById('f-spirit').value.trim();
  const btn = document.getElementById('submitBtn');
  const formMsg = document.getElementById('formMsg');

  if(!title || !content){
    formMsg.textContent = 'Preencha ao menos o título e a mensagem.';
    formMsg.className = 'form-msg err';
    return;
  }

  if(!authToken){
    formMsg.textContent = 'Sua sessão expirou. Saia e entre novamente na área do mantenedor.';
    formMsg.className = 'form-msg err';
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Publicando...';
  formMsg.textContent = '';
  formMsg.className = 'form-msg';

  try{
    const res = await fetch(`${API_BASE_URL}/api/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`,
      },
      body: JSON.stringify({ title, content, author, spirit }),
    });

    if(!res.ok){
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || 'Falha ao publicar.');
    }

    const list = await loadMessages();
    renderMural(list);
    document.getElementById('msgForm').reset();
    formMsg.textContent = 'Mensagem publicada no mural. Que ela traga conforto a quem a ler.';
    formMsg.className = 'form-msg ok';
  }catch(err){
    formMsg.textContent = err.message || 'Não foi possível publicar agora. Tente novamente em instantes.';
    formMsg.className = 'form-msg err';
  }finally{
    btn.disabled = false;
    btn.textContent = 'Publicar mensagem';
  }
});

refreshMural();

/* ---------- Área do mantenedor ---------- */
const gateToggle = document.getElementById('gateToggle');
const gateAuth = document.getElementById('gateAuth');
const gatePassword = document.getElementById('gatePassword');
const gateSubmit = document.getElementById('gateSubmit');
const gateError = document.getElementById('gateError');
const gateCard = document.getElementById('gateCard');
const publishCard = document.getElementById('publishCard');
const logoutLink = document.getElementById('logoutLink');

gateToggle.addEventListener('click', () => {
  gateAuth.classList.toggle('open');
  if(gateAuth.classList.contains('open')) gatePassword.focus();
});

async function tryUnlock(){
  gateError.style.display = 'none';
  const password = gatePassword.value;
  if(!password) return;

  gateSubmit.disabled = true;
  gateSubmit.textContent = 'Entrando...';

  try{
    const res = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    });
    const data = await res.json().catch(() => ({}));

    if(!res.ok){
      gateError.textContent = data.error || 'Senha incorreta.';
      gateError.style.display = 'block';
      return;
    }

    authToken = data.token;
    gateCard.style.display = 'none';
    publishCard.style.display = 'block';
    gatePassword.value = '';
  }catch(err){
    gateError.textContent = 'Não foi possível conectar ao servidor. Tente novamente.';
    gateError.style.display = 'block';
  }finally{
    gateSubmit.disabled = false;
    gateSubmit.textContent = 'Entrar';
  }
}

gateSubmit.addEventListener('click', tryUnlock);
gatePassword.addEventListener('keydown', (e) => {
  if(e.key === 'Enter'){ e.preventDefault(); tryUnlock(); }
});

logoutLink.addEventListener('click', () => {
  authToken = null;
  publishCard.style.display = 'none';
  gateCard.style.display = 'flex';
  gateAuth.classList.remove('open');
});