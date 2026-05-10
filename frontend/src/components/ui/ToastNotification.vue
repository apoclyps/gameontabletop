<template>
  <Teleport to="body">
    <div class="fixed top-4 right-4 z-[9999] flex flex-col gap-2 w-80 pointer-events-none">
      <TransitionGroup
        enter-active-class="transition-all duration-300 ease-out"
        enter-from-class="translate-x-full opacity-0"
        enter-to-class="translate-x-0 opacity-100"
        leave-active-class="transition-all duration-200 ease-in"
        leave-from-class="translate-x-0 opacity-100"
        leave-to-class="translate-x-full opacity-0"
      >
        <div
          v-for="toast in toasts"
          :key="toast.id"
          :class="toastClasses(toast.variant)"
          class="pointer-events-auto flex items-start gap-3 px-4 py-3 rounded-xl shadow-lg"
        >
          <component :is="toastIcon(toast.variant)" class="w-5 h-5 flex-shrink-0 mt-0.5" />
          <p class="text-sm flex-1">{{ toast.message }}</p>
          <button @click="dismiss(toast.id)" class="flex-shrink-0 opacity-60 hover:opacity-100 focus-visible:outline-none focus-visible:ring-2 rounded" aria-label="Dismiss">
            <XMarkIcon class="w-4 h-4" />
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup>
import {
  CheckCircleIcon,
  ExclamationCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  XMarkIcon,
} from "@heroicons/vue/20/solid";
import { useToast } from "../../composables/useToast.js";

const { toasts, dismiss } = useToast();

function toastClasses(variant) {
  return {
    success: "bg-emerald-600 text-white",
    error: "bg-red-600 text-white",
    warning: "bg-amber-500 text-white",
    info: "bg-primary-600 text-white",
  }[variant] ?? "bg-slate-800 text-white";
}

function toastIcon(variant) {
  return {
    success: CheckCircleIcon,
    error: ExclamationCircleIcon,
    warning: ExclamationTriangleIcon,
    info: InformationCircleIcon,
  }[variant] ?? InformationCircleIcon;
}
</script>
