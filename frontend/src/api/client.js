/**
 * File: src/api/client.js

 *
 * Centralised API client for communicating with the FastAPI backend.
 * Provides real-time upload progress tracking for large policy documents.
 */

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const getToken = () => localStorage.getItem('access_token');

/** Generic fetch wrapper — automatically attaches Bearer token */
async function apiFetch(endpoint, options = {}) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  const response = await fetch(`${BASE_URL}${endpoint}`, { ...options, headers });

  if (response.status === 401) {
    localStorage.removeItem('access_token');
    window.location.reload(); // Redirect to login
    throw new Error("Session expired. Please log in again.");
  }

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(err.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

/** 
 * Enhanced Upload Wrapper using XMLHttpRequest for Real-time Progress Tracking 
 */
function xhrUpload(endpoint, file, additionalFields = {}, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    const token = getToken();

    formData.append('file', file);
    Object.keys(additionalFields).forEach(key => {
      formData.append(key, additionalFields[key]);
    });

    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable && onProgress) {
        const percent = Math.round((event.loaded / event.total) * 100);
        onProgress(percent);
      }
    });

    xhr.onreadystatechange = () => {
      if (xhr.readyState === 4) {
        if (xhr.status >= 200 && xhr.status < 300) {
          try { resolve(JSON.parse(xhr.responseText)); }
          catch (e) { resolve(xhr.responseText); }
        } else if (xhr.status === 401) {
          localStorage.removeItem('access_token');
          window.location.reload();
          reject(new Error("Session expired. Please log in again."));
        } else {
          try {
            const err = JSON.parse(xhr.responseText);
            reject(new Error(err.detail || 'Upload failed'));
          } catch (e) {
            reject(new Error(`HTTP ${xhr.status}: ${xhr.statusText}`));
          }
        }
      }
    };

    xhr.open('POST', `${BASE_URL}${endpoint}`);
    if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    xhr.send(formData);
  });
}

/* ── Auth Endpoints ──────────────────────────────────────────── */

export async function login(username, password) {
  const body = new URLSearchParams({ username, password });
  const response = await fetch(`${BASE_URL}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Login failed');
  }
  const data = await response.json();
  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('user_roles', JSON.stringify(data.roles));
  return data;
}

export async function register(username, email, password) {
  return apiFetch('/api/v1/auth/register', {
    method: 'POST',
    body: JSON.stringify({ username, email, password }),
  });
}

export function logout() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('user_roles');
}

export function getUserRoles() {
  try { return JSON.parse(localStorage.getItem('user_roles')) || []; }
  catch { return []; }
}

/* ── Query Endpoint ──────────────────────────────────────────── */

export const queryPolicy = async (question, inferenceMode = 'local', history = [], sessionId = null) => {
  const payload = {
    question,
    inference_mode: inferenceMode,
    history,
    session_id: sessionId
  };

  const result = await apiFetch('/api/v1/query', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  return result.data;
};

/* ── Session Endpoints ────────────────────────────────────────── */

export async function createChatSession(title = 'New Conversation') {
  return apiFetch('/api/v1/chat/sessions', {
    method: 'POST',
    body: JSON.stringify({ title }),
  });
}

export async function fetchChatSessions() {
  return apiFetch('/api/v1/chat/sessions');
}

export async function fetchSessionHistory(sessionId) {
  return apiFetch(`/api/v1/chat/sessions/${sessionId}`);
}

export async function deleteChatSession(sessionId) {
  return apiFetch(`/api/v1/chat/sessions/${sessionId}`, {
    method: 'DELETE',
  });
}

/* ── Admin Endpoints ─────────────────────────────────────────── */

/** Admin upload with progress support */
export async function uploadDocument(file, displayName, accessLevel = 'public', onProgress) {
  return xhrUpload('/api/v1/admin/documents', file, { display_name: displayName, access_level: accessLevel }, onProgress);
}

export async function fetchDocuments() {
  return apiFetch('/api/v1/admin/documents');
}

export async function deleteDocument(docId) {
  return apiFetch(`/api/v1/admin/documents/${docId}`, {
    method: 'DELETE',
  });
}

export async function fetchUsers() {
  return apiFetch('/api/v1/admin/users');
}

export async function diffDocuments(docAId, docBId, inferenceMode = 'cloud') {
  return apiFetch(`/api/v1/admin/diff?doc_a_id=${docAId}&doc_b_id=${docBId}&inference_mode=${inferenceMode}`, {
    method: 'POST',
  });
}

export async function updateUserRole(userId, role) {
  return apiFetch(`/api/v1/admin/users/${userId}/role`, {
    method: 'PUT',
    body: JSON.stringify({ role }),
  });
}

export async function healthCheck() {
  return apiFetch('/');
}

/* ── Chat Endpoints ──────────────────────────────────────────── */

/** Chat-based upload with progress support */
export async function uploadFromChat(file, displayName, sessionId, onProgress) {
  return xhrUpload('/api/v1/chat/upload', file, { display_name: displayName, session_id: sessionId }, onProgress);
}
