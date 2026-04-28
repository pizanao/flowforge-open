/**
 * Hooks customizados do FlowForge.
 * useApi — fetch genérico com loading/error.
 */

import { useCallback, useEffect, useState } from "react";

const BASE = import.meta.env.VITE_API_BASE || "/api";

export function getAuthHeaders() {
  const token = localStorage.getItem("flowforge_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function clearAuthAndReload() {
  localStorage.removeItem("flowforge_token");
  localStorage.removeItem("flowforge_refresh");
  localStorage.removeItem("flowforge_user");
  window.location.reload();
}

async function refreshAccessToken() {
  const refresh = localStorage.getItem("flowforge_refresh");
  if (!refresh) return "";

  const response = await fetch("/api/auth/token/refresh/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });
  if (!response.ok) return "";

  const payload = await response.json();
  if (!payload.access) return "";
  localStorage.setItem("flowforge_token", payload.access);
  return payload.access;
}

export async function apiFetch(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
      ...(options.headers || {}),
    },
  });

  if (response.status !== 401) {
    return response;
  }

  const refreshedAccess = await refreshAccessToken();
  if (!refreshedAccess) {
    clearAuthAndReload();
    return response;
  }

  const retryResponse = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${refreshedAccess}`,
      ...(options.headers || {}),
    },
  });

  if (retryResponse.status === 401) {
    clearAuthAndReload();
  }

  return retryResponse;
}

export function useApi(endpoint, options = {}) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { immediate = true } = options;

  const fetchData = useCallback(async (params = "") => {
    setLoading(true);
    setError(null);
    try {
      const url = `${BASE}/${endpoint}/${params ? "?" + params : ""}`;
      const res = await apiFetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json.results || json);
      return json.results || json;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setLoading(false);
    }
  }, [endpoint]);

  useEffect(() => {
    if (immediate) fetchData();
  }, [immediate, fetchData]);

  return { data, loading, error, refetch: fetchData };
}

export async function postAction(endpoint, body = {}) {
  const res = await apiFetch(`${BASE}/${endpoint}`, {
    method: "POST",
    body: JSON.stringify(body),
    credentials: "include",
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export function useApiAction() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const execute = useCallback(async (endpoint, body = {}) => {
    setLoading(true);
    setError(null);
    try {
      const data = await postAction(endpoint, body);
      return data;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return { execute, loading, error };
}
