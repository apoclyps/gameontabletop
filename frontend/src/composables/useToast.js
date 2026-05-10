import { reactive } from "vue";

const toasts = reactive([]);

let nextId = 0;

export function useToast() {
  function show(message, variant = "info", duration = 4000) {
    const id = ++nextId;
    toasts.push({ id, message, variant });
    if (duration > 0) setTimeout(() => dismiss(id), duration);
    return id;
  }

  function dismiss(id) {
    const idx = toasts.findIndex((t) => t.id === id);
    if (idx !== -1) toasts.splice(idx, 1);
  }

  return {
    toasts,
    show,
    dismiss,
    success: (msg, dur) => show(msg, "success", dur),
    error: (msg, dur) => show(msg, "error", dur),
    warning: (msg, dur) => show(msg, "warning", dur),
    info: (msg, dur) => show(msg, "info", dur),
  };
}
