<template>
  <div class="min-h-screen bg-gray-50 flex items-center justify-center">
    <div class="bg-white rounded-xl shadow-md p-10 max-w-md w-full">
      <h1 class="text-2xl font-bold text-gray-800 mb-2 text-center">Forgot password</h1>
      <p class="text-sm text-gray-500 text-center mb-6">Enter your email and we'll send a reset link.</p>
      <div v-if="sent" class="text-green-600 text-sm text-center">
        If that email is registered, a reset link has been sent.
      </div>
      <form v-else @submit.prevent="submit" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Email</label>
          <input v-model="email" type="email" required autocomplete="email"
            class="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <p v-if="error" class="text-red-500 text-sm">{{ error }}</p>
        <button type="submit" :disabled="loading"
          class="w-full bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
          {{ loading ? "Sending…" : "Send reset link" }}
        </button>
      </form>
      <p class="mt-4 text-center text-sm">
        <router-link to="/login" class="text-blue-600 hover:underline">Back to sign in</router-link>
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { forgotPassword } from "../services/auth.js";

const email = ref("");
const error = ref(null);
const loading = ref(false);
const sent = ref(false);

async function submit() {
  error.value = null;
  loading.value = true;
  try {
    await forgotPassword(email.value);
    sent.value = true;
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}
</script>
