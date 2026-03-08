const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const getToken = () => sessionStorage.getItem("auth_token");
export const setToken = (token: string) => sessionStorage.setItem("auth_token", token);
export const clearToken = () => sessionStorage.removeItem("auth_token");

export async function apiFetch(path: string, options: RequestInit = {}) {
  const token = getToken();
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (res.status === 401) {
    clearToken();
  }
  return res;
}
