<template>
  <div class="min-h-screen bg-slate-50 dark:bg-slate-900 flex flex-col items-center justify-center px-4 py-12">
    <!-- Logo -->
    <router-link to="/" class="flex items-center gap-3 mb-8 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 rounded-xl p-1">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" class="w-10 h-10" fill="none">
        <rect x="1" y="1" width="30" height="30" rx="6" fill="#0d9488"/>
        <circle cx="9" cy="10" r="2.5" fill="white"/>
        <circle cx="23" cy="10" r="2.5" fill="white"/>
        <circle cx="9" cy="22" r="2.5" fill="white"/>
        <circle cx="23" cy="22" r="2.5" fill="white"/>
        <circle cx="16" cy="16" r="2.5" fill="white"/>
      </svg>
      <span class="text-xl font-bold text-slate-900 dark:text-white tracking-tight">Game On Tabletop</span>
    </router-link>

    <!-- Card -->
    <div class="w-full max-w-md bg-white dark:bg-slate-800 rounded-2xl shadow-card border border-slate-200 dark:border-slate-700 p-8">
      <slot />
    </div>

    <!-- Dark mode toggle (bottom right) -->
    <button
      @click="toggle"
      class="mt-6 w-9 h-9 flex items-center justify-center rounded-xl text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
      :aria-label="scheme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'"
    >
      <SunIcon v-if="scheme === 'dark'" class="w-5 h-5" />
      <MoonIcon v-else class="w-5 h-5" />
    </button>

    <ToastNotification />
  </div>
</template>

<script setup>
import { MoonIcon, SunIcon } from "@heroicons/vue/24/outline";
import ToastNotification from "../components/ui/ToastNotification.vue";
import { useColorScheme } from "../composables/useColorScheme.js";

const { scheme, toggle } = useColorScheme();
</script>
