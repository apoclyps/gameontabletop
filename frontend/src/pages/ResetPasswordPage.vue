<template>
  <div class="min-h-screen bg-gray-50 flex items-center justify-center">
    <div class="bg-white rounded-xl shadow-md p-10 max-w-md w-full">
      <h1 class="text-2xl font-bold text-gray-800 mb-6 text-center">Reset password</h1>
      <div v-if="!token" class="text-red-500 text-sm text-center">
        Invalid reset link. Please request a new one.
      </div>
      <div v-else-if="success" class="text-green-600 text-sm text-center">
        Password reset! <router-link to="/login" class="underline">Sign in</router-link>
      </div>
      <form v-else @submit.prevent="submit" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">New password</label>
          <input v-model="password" type="password" required autocomplete="new-password"
            class="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <p v-if="error" class="text-red-500 text-sm">{{ error }}</p>
        <button type="submit" :disabled="loading"
          class="w-full bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
          {{ loading ? "Resetting…" : "Reset password" }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRoute } from "vue-router";
import { resetPassword } from "../services/auth.js";

const route = useRoute();
const token = route.query.token || null;
const password = ref("");
const error = ref(null);
const loading = ref(false);
const success = ref(false);

async function submit() {
  error.value = null;
  loading.value = true;
  try {
    await resetPassword(token, password.value);
    success.value = true;
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}
</script>
