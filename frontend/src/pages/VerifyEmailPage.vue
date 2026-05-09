<template>
  <div class="min-h-screen bg-gray-50 flex items-center justify-center">
    <div class="bg-white rounded-xl shadow-md p-10 max-w-md w-full text-center">
      <h1 class="text-2xl font-bold text-gray-800 mb-6">Email verification</h1>
      <div v-if="loading" class="text-gray-400 animate-pulse">Verifying…</div>
      <div v-else-if="success" class="text-green-600">
        <p class="mb-4">Your email has been verified!</p>
        <router-link to="/login" class="text-blue-600 hover:underline">Sign in</router-link>
      </div>
      <div v-else class="text-red-500">
        <p class="mb-4">{{ error }}</p>
        <router-link to="/login" class="text-blue-600 hover:underline">Back to sign in</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { request } from "../services/api.js";

const route = useRoute();
const loading = ref(true);
const success = ref(false);
const error = ref(null);

const apiBase = import.meta.env.VITE_API_BASE_URL || "";

onMounted(async () => {
  const token = route.query.token;
  if (!token) {
    error.value = "Missing verification token.";
    loading.value = false;
    return;
  }
  try {
    const res = await fetch(`${apiBase}/api/auth/verify-email?token=${encodeURIComponent(token)}`);
    if (res.ok) {
      success.value = true;
    } else {
      const data = await res.json();
      error.value = data.detail || "Verification failed.";
    }
  } catch {
    error.value = "Network error. Please try again.";
  } finally {
    loading.value = false;
  }
});
</script>
