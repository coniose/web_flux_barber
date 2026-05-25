// Flux Barber — registro assíncrono direto (sem fila)
const FluxReg = (() => {

  // ---------- toast ----------

  function showToast(msg, type) {
    const colors = {
      success: 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300',
      error:   'bg-red-500/20 border-red-500/40 text-red-300',
      info:    'bg-blue-500/20 border-blue-500/40 text-blue-300',
    };
    const icon = type === 'error'
      ? '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>'
      : '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>';

    const toast = document.createElement('div');
    toast.className = `flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg text-sm font-medium border ${colors[type] || colors.info}`;
    toast.innerHTML = `<svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">${icon}</svg>${msg}`;

    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      container.className = 'fixed top-4 right-4 z-50 flex flex-col gap-2 pointer-events-none';
      document.body.appendChild(container);
    }
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.4s';
      setTimeout(() => toast.remove(), 400);
    }, 3000);
  }

  // ---------- registro ----------

  const _csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';

  async function registrar(type, data, btn) {
    const label = btn ? btn.textContent : '';
    if (btn) { btn.disabled = true; btn.textContent = 'Registrando...'; }

    try {
      const res = await fetch('/api/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': _csrf },
        body: JSON.stringify({ operations: [{ id: crypto.randomUUID(), type, data }] }),
        credentials: 'same-origin',
      });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const { failed = [] } = await res.json();
      if (failed.length > 0) throw new Error('falha no servidor');
      return true;
    } catch {
      return false;
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = label; }
    }
  }

  return { showToast, registrar };
})();
