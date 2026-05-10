<template>
  <div class="text-center">
    <h1 class="text-2xl font-bold text-slate-900 dark:text-white mb-6">Email verification</h1>

    <div v-if="loading" class="space-y-3">
      <SkeletonLoader height="h-4" width="w-3/4" class="mx-auto" />
      <SkeletonLoader height="h-4" width="w-1/2" class="mx-auto" />
    </div>

    <BaseAlert v-else-if="success" variant="success" message="Your email has been verified!" />
    <div v-if="success" class="mt-4">
      <router-link to="/login" class="text-primary-600 hover:underline text-sm">Sign in to your account</router-link>
    </div>

    <template v-else-if="!loading">
      <BaseAlert variant="error" :message="error" />
      <p class="mt-4">
        <router-link to="/login" class="text-primary-600 hover:underline text-sm">Back to sign in</router-link>
      </p>
    </template>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import BaseAlert from "../components/ui/BaseAlert.vue";
import SkeletonLoader from "../components/ui/SkeletonLoader.vue";
import { request } from "../services/api.js";

const route = useRoute();
const loading = ref(true);
const success = ref(false);
const error = ref("Verification failed.");

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
