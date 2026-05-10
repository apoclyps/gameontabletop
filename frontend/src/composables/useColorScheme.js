import { ref, watchEffect } from "vue";

const STORAGE_KEY = "color-scheme";
const prefersDark = typeof window !== "undefined" && window.matchMedia?.("(prefers-color-scheme: dark)").matches;
const scheme = ref(localStorage.getItem(STORAGE_KEY) ?? (prefersDark ? "dark" : "light"));

watchEffect(() => {
  const html = document.documentElement;
  if (scheme.value === "dark") {
    html.classList.add("dark");
  } else {
    html.classList.remove("dark");
  }
  localStorage.setItem(STORAGE_KEY, scheme.value);
});

export function useColorScheme() {
  function toggle() {
    scheme.value = scheme.value === "dark" ? "light" : "dark";
  }
  return { scheme, toggle };
}
