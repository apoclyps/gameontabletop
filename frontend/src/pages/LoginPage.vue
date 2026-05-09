<template>
  <div class="min-h-screen bg-gray-50 flex items-center justify-center">
    <div class="bg-white rounded-xl shadow-md p-10 max-w-md w-full">
      <h1 class="text-2xl font-bold text-gray-800 mb-6 text-center">Sign in</h1>
      <form @submit.prevent="submit" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Email</label>
          <input v-model="email" type="email" required autocomplete="email"
            class="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Password</label>
          <input v-model="password" type="password" required autocomplete="current-password"
            class="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <p v-if="error" class="text-red-500 text-sm">{{ error }}</p>
        <button type="submit" :disabled="loading"
          class="w-full bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
          {{ loading ? "Signing in…" : "Sign in" }}
        </button>
      </form>
      <div class="mt-4 text-center text-sm text-gray-500 space-y-1">
        <p><router-link to="/forgot-password" class="text-blue-600 hover:underline">Forgot password?</router-link></p>
        <p>No account? <router-link to="/register" class="text-blue-600 hover:underline">Register</router-link></p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { login } from "../services/auth.js";

const router = useRouter();
const email = ref("");
const password = ref("");
const error = ref(null);
const loading = ref(false);

async function submit() {
  error.value = null;
  loading.value = true;
  try {
    await login(email.value, password.value);
    router.push("/profile");
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}
</script>
