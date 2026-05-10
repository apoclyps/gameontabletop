const apiBase = import.meta.env.VITE_API_BASE_URL || "";

function getTokens() {
  return {
    access: localStorage.getItem("access_token"),
    refresh: localStorage.getItem("refresh_token"),
  };
}

function setTokens(access, refresh) {
  localStorage.setItem("access_token", access);
  if (refresh) localStorage.setItem("refresh_token", refresh);
}

function clearTokens() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

async function refreshAccessToken() {
  const { refresh } = getTokens();
  if (!refresh) throw new Error("No refresh token");
  const res = await fetch(`${apiBase}/api/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!res.ok) {
    clearTokens();
    throw new Error("Session expired");
  }
  const data = await res.json();
  setTokens(data.access_token, data.refresh_token);
  return data.access_token;
}

async function request(path, options = {}) {
  const { access } = getTokens();
  const isFormData = options.body instanceof FormData;
  const headers = isFormData ? { ...options.headers } : { "Content-Type": "application/json", ...options.headers };
  if (access) headers["Authorization"] = `Bearer ${access}`;

  let res = await fetch(`${apiBase}${path}`, { ...options, headers });

  if (res.status === 401 && access) {
    try {
      const newAccess = await refreshAccessToken();
      headers["Authorization"] = `Bearer ${newAccess}`;
      res = await fetch(`${apiBase}${path}`, { ...options, headers });
    } catch {
      clearTokens();
      window.location.href = "/login";
      throw new Error("Session expired");
    }
  }

  return res;
}

export { clearTokens, getTokens, request, setTokens };
