// Centralized API Client and Utilities

const API = {
  baseUrl: '/api',

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers
    };

    try {
      const response = await fetch(url, { ...options, headers });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || `HTTP error ${response.status}`);
      }
      return data;
    } catch (err) {
      console.error(`API Request failed for ${endpoint}:`, err);
      throw err;
    }
  },

  get(endpoint) {
    return this.request(endpoint, { method: 'GET' });
  },

  post(endpoint, body) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(body)
    });
  },

  put(endpoint, body) {
    return this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(body)
    });
  },

  delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  },

  async updateDbStatusPill() {
    try {
      const data = await this.get('/health');
      const badge = document.getElementById('nav-db-status');
      if (badge && data.database) {
        if (data.database.mode === 'mongodb_live') {
          badge.className = 'db-status-pill live';
          badge.innerHTML = '<i class="bi bi-check-circle-fill"></i> MongoDB Live';
          badge.title = data.database.details;
        } else {
          badge.className = 'db-status-pill fallback';
          badge.innerHTML = '<i class="bi bi-hdd-stack-fill"></i> Mock MongoDB';
          badge.title = data.database.details;
        }
      }
    } catch (e) {
      const badge = document.getElementById('nav-db-status');
      if (badge) {
        badge.className = 'db-status-pill bg-danger text-white';
        badge.innerHTML = '<i class="bi bi-exclamation-triangle-fill"></i> Backend Offline';
      }
    }
  }
};

// UI Notification Toast
function showToast(title, message, type = 'info') {
  let toastContainer = document.getElementById('toast-container');
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.id = 'toast-container';
    toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    toastContainer.style.zIndex = '9999';
    document.body.appendChild(toastContainer);
  }

  const bgClasses = {
    success: 'bg-success text-white',
    danger: 'bg-danger text-white',
    warning: 'bg-warning text-dark',
    info: 'bg-primary text-white'
  };

  const toastId = 'toast-' + Date.now();
  const html = `
    <div id="${toastId}" class="toast align-items-center ${bgClasses[type] || bgClasses.info} border-0 shadow" role="alert" aria-live="assertive" aria-atomic="true">
      <div class="d-flex">
        <div class="toast-body">
          <strong>${title}:</strong> ${message}
        </div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
    </div>
  `;
  toastContainer.insertAdjacentHTML('beforeend', html);

  const toastEl = document.getElementById(toastId);
  if (window.bootstrap && bootstrap.Toast) {
    const toast = new bootstrap.Toast(toastEl, { delay: 4500 });
    toast.show();
    toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
  }
}

// Auto-check DB status on page load
document.addEventListener('DOMContentLoaded', () => {
  API.updateDbStatusPill();
});
