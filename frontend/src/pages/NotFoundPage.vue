<template>
  <div class="text-center">
    <div class="text-6xl font-bold text-slate-200 dark:text-slate-700 mb-2">404</div>
    <div class="w-16 h-16 mx-auto mb-4 rounded-2xl bg-slate-100 dark:bg-slate-700 flex items-center justify-center">
      <FaceFrownIcon class="w-8 h-8 text-slate-400 dark:text-slate-500" />
    </div>
    <h1 class="text-2xl font-bold text-slate-900 dark:text-white mb-2">Page not found</h1>
    <p class="text-sm text-slate-500 dark:text-slate-400 mb-6">The page you're looking for has wandered off the table.</p>
    <BaseButton to="/dashboard">Back to Dashboard</BaseButton>
  </div>
</template>

<script setup>
import { FaceFrownIcon } from "@heroicons/vue/24/outline";
import BaseButton from "../components/ui/BaseButton.vue";
</script>
