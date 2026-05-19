/**
 * hospitalLite.js — mode detection, local clinician profile, queue + audit
 * persistence for Hospital Lite. Everything lives in localStorage so the
 * app works offline on iPad / iOS Safari.
 */

export const APP_MODE = (import.meta.env.VITE_APP_MODE || 'standard').toLowerCase();
export const IS_HOSPITAL_LITE = APP_MODE === 'hospital_lite';

const KEYS = {
    queue:     'safeTriage.hl.queue',
    clinician: 'safeTriage.hl.clinician',
    counter:   'safeTriage.hl.idCounter',
};

// ---------- Clinician profile ----------

export function getClinician() {
    try {
        const raw = localStorage.getItem(KEYS.clinician);
        if (!raw) return null;
        const parsed = JSON.parse(raw);
        return parsed && parsed.name ? parsed : null;
    } catch {
        return null;
    }
}

export function setClinician(profile) {
    const safe = {
        name: (profile?.name || '').toString().slice(0, 60).trim(),
        role: profile?.role || 'nurse',
        loggedInAt: new Date().toISOString(),
    };
    localStorage.setItem(KEYS.clinician, JSON.stringify(safe));
    return safe;
}

export function clearClinician() {
    localStorage.removeItem(KEYS.clinician);
}

// ---------- Patient ID generation ----------

function nextCounter() {
    let n = 0;
    try {
        n = parseInt(localStorage.getItem(KEYS.counter) || '0', 10) || 0;
    } catch {}
    n += 1;
    try { localStorage.setItem(KEYS.counter, String(n)); } catch {}
    return n;
}

export function generatePatientId() {
    const now = new Date();
    const yyyy = now.getFullYear();
    const mm = String(now.getMonth() + 1).padStart(2, '0');
    const dd = String(now.getDate()).padStart(2, '0');
    const seq = String(nextCounter()).padStart(4, '0');
    return `HL-${yyyy}${mm}${dd}-${seq}`;
}

// ---------- Queue + audit ----------

function readQueue() {
    try {
        const raw = localStorage.getItem(KEYS.queue);
        const parsed = raw ? JSON.parse(raw) : [];
        return Array.isArray(parsed) ? parsed : [];
    } catch {
        return [];
    }
}

function writeQueue(items) {
    localStorage.setItem(KEYS.queue, JSON.stringify(items));
}

export function getQueue() { return readQueue(); }

export function getQueueCount() { return readQueue().length; }

export function addQueueEntry(entry) {
    const items = readQueue();
    const record = {
        id: entry.id || `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
        created_at: entry.created_at || new Date().toISOString(),
        ...entry,
    };
    items.unshift(record);
    // Keep the queue bounded — the UI doesn't need years of history.
    writeQueue(items.slice(0, 200));
    return record;
}

export function updateQueueEntry(id, patch) {
    const items = readQueue();
    const idx = items.findIndex((p) => p.id === id);
    if (idx === -1) return null;
    items[idx] = { ...items[idx], ...patch };
    writeQueue(items);
    return items[idx];
}

export function getQueueEntry(id) {
    return readQueue().find((p) => p.id === id) || null;
}

export function appendAudit(id, event) {
    const items = readQueue();
    const idx = items.findIndex((p) => p.id === id);
    if (idx === -1) return null;
    const audit = Array.isArray(items[idx].audit) ? items[idx].audit.slice() : [];
    audit.push({
        at: new Date().toISOString(),
        ...event,
    });
    items[idx] = { ...items[idx], audit };
    writeQueue(items);
    return items[idx];
}

// ---------- Export ----------

export function exportEntryAsJson(entry) {
    const blob = new Blob([JSON.stringify(entry, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `triage-${entry.patient_id || entry.id}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}
