import { clearTokens, getTokens, request, setTokens } from "./api.js";

export function isAuthenticated() {
  return !!getTokens().access;
}

export function isAdmin() {
  const { access } = getTokens();
  if (!access) return false;
  try {
    const payload = JSON.parse(atob(access.split(".")[1]));
    return payload.is_admin === true;
  } catch {
    return false;
  }
}

export async function register(email, username, password) {
  const res = await request("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, username, password }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Registration failed");
  }
  return res.json();
}

export async function login(email, password) {
  const res = await request("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Login failed");
  }
  const data = await res.json();
  setTokens(data.access_token, data.refresh_token);
  return data;
}

export async function logout() {
  await request("/api/auth/logout", { method: "POST" }).catch(() => {});
  clearTokens();
}

export async function forgotPassword(email) {
  const res = await request("/api/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
  if (!res.ok) throw new Error("Request failed");
  return res.json();
}

export async function resetPassword(token, newPassword) {
  const res = await request("/api/auth/reset-password", {
    method: "POST",
    body: JSON.stringify({ token, new_password: newPassword }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Reset failed");
  }
  return res.json();
}
