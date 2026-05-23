// Flux Barber — write-behind sync queue
// Operações de lançamento são salvas localmente e enviadas em lote ao servidor.
const FluxSync = (() => {
  const QUEUE_KEY = 'flux_queue';
  const DEBOUNCE_MS = 4000;
  let timer = null;
  let syncing = false;

  // ---------- queue ----------

  function load() {
    try { return JSON.parse(localStorage.getItem(QUEUE_KEY) || '[]'); }
    catch { return []; }
  }

  function save(ops) {
    localStorage.setItem(QUEUE_KEY, JSON.stringify(ops));
    _updateBadge(ops.length);
  }

  function enqueue(type, data) {
    const ops = load();
    ops.push({ id: crypto.randomUUID(), type, data, ts: new Date().toISOString() });
    save(ops);
    scheduleSync();
    return ops.length;
  }

  // ---------- sync ----------

  function scheduleSync() {
    clearTimeout(timer);
    timer = setTimeout(sync, DEBOUNCE_MS);
  }

  async function sync() {
    if (syncing) return;
    const ops = load();
    if (ops.length === 0) return;

    syncing = true;
    _setStatus('syncing');

    try {
      const res = await fetch('/api/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ operations: ops }),
        credentials: 'same-origin',
      });

      if (!res.ok) throw new Error('HTTP ' + res.status);

      const { synced = [], failed = [] } = await res.json();
      const remaining = load().filter(op => !synced.includes(op.id));
      save(remaining);

      if (failed.length > 0) {
        _setStatus('partial');
        showToast(`${failed.length} registro(s) nao puderam ser salvos — tentando novamente.`, 'error');
        timer = setTimeout(sync, 30000);
      } else {
        _setStatus('ok');
      }
    } catch {
      _setStatus('error');
      timer = setTimeout(sync, 30000);
    } finally {
      syncing = false;
    }
  }

  // ---------- UI ----------

  function _updateBadge(count) {
    const badge = document.getElementById('sync-badge');
    const wrap = document.getElementById('sync-indicator');
    if (!badge || !wrap) return;
    badge.textContent = count;
    wrap.classList.toggle('hidden', count === 0);
  }

  function _setStatus(state) {
    const el = document.getElementById('sync-status');
    if (!el) return;
    const map = {
      syncing: ['Sincronizando...', 'text-yellow-400'],
      ok:      ['Sincronizado',     'text-emerald-400'],
      error:   ['Falha ao sincronizar — retentando', 'text-red-400'],
      partial: ['Sync parcial',     'text-yellow-400'],
    };
    const [text, cls] = map[state] || ['', ''];
    el.textContent = text;
    el.className = 'text-xs transition-colors ' + cls;
    if (state === 'ok') setTimeout(() => { el.textContent = ''; }, 3000);
  }

  function showToast(msg, type) {
    const colors = {
      success: 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300',
      error:   'bg-red-500/20 border-red-500/40 text-red-300',
      info:    'bg-blue-500/20 border-blue-500/40 text-blue-300',
    };
    const cls = colors[type] || colors.info;
    const icon = type === 'error'
      ? '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>'
      : '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>';

    const toast = document.createElement('div');
    toast.className = `flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg text-sm font-medium border ${cls}`;
    toast.innerHTML = `<svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">${icon}</svg>${msg}`;

    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'fixed top-4 right-4 z-50 flex flex-col gap-2';
      document.body.appendChild(container);
    }
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.4s';
      setTimeout(() => toast.remove(), 400);
    }, 3000);
  }

  // ---------- lifecycle ----------

  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') sync();
  });
  window.addEventListener('beforeunload', () => sync());

  document.addEventListener('DOMContentLoaded', () => {
    _updateBadge(load().length);
    if (load().length > 0) scheduleSync();
  });

  return { enqueue, sync, showToast, load };
})();
