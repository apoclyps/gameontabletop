<template>
  <div class="min-h-screen bg-gray-50 flex items-center justify-center">
    <div class="bg-white rounded-xl shadow-md p-10 max-w-md w-full text-center">
      <h1 class="text-3xl font-bold text-gray-800 mb-6">Game On Tabletop</h1>

      <div v-if="loading" class="text-gray-400 animate-pulse">Loading…</div>

      <div v-else-if="error" class="text-red-500 text-sm">
        Failed to reach API: {{ error }}
      </div>

      <div v-else class="text-green-600 text-xl font-medium">
        {{ message }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";

const message = ref("");
const loading = ref(true);
const error = ref(null);

const apiBase = import.meta.env.VITE_API_BASE_URL || "";

onMounted(async () => {
  try {
    const response = await fetch(`${apiBase}/api/`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    message.value = data.message;
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
});
</script>
