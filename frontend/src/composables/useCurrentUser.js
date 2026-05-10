import { onMounted, ref } from "vue";
import { request } from "../services/api.js";
import { isAuthenticated } from "../services/auth.js";

const user = ref(null);

export function useCurrentUser() {
  onMounted(async () => {
    if (!isAuthenticated() || user.value) return;
    try {
      const res = await request("/api/users/me");
      if (res.ok) user.value = await res.json();
    } catch {
      // silently ignore — nav will just show initials fallback
    }
  });

  function clearUser() {
    user.value = null;
  }

  return { user, clearUser };
}
