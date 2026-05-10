<template>
  <div>
    <h1 class="text-2xl font-bold text-slate-900 dark:text-white mb-1">Forgot password</h1>
    <p class="text-sm text-slate-500 dark:text-slate-400 mb-6">We'll send a reset link to your email.</p>

    <BaseAlert v-if="sent" variant="success" message="If that email is registered, a reset link has been sent." />

    <form v-else @submit.prevent="submit" class="space-y-4">
      <BaseInput v-model="email" label="Email" type="email" required autocomplete="email" />

      <BaseAlert v-if="error" variant="error" :message="error" />

      <BaseButton type="submit" :loading="loading" block>Send reset link</BaseButton>
    </form>

    <p class="mt-5 text-center text-sm">
      <router-link to="/login" class="text-primary-600 hover:text-primary-700 dark:text-primary-400 hover:underline">
        ← Back to sign in
      </router-link>
    </p>
  </div>
</template>

<script setup>
import { ref } from "vue";
import BaseAlert from "../components/ui/BaseAlert.vue";
import BaseButton from "../components/ui/BaseButton.vue";
import BaseInput from "../components/ui/BaseInput.vue";
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
