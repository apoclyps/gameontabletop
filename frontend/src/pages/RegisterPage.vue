<template>
  <div>
    <h1 class="text-2xl font-bold text-slate-900 dark:text-white mb-1">Create account</h1>
    <p class="text-sm text-slate-500 dark:text-slate-400 mb-6">Join the tabletop community</p>

    <BaseAlert v-if="success" variant="success" message="Registration successful! Check your email to verify your account." />

    <form v-else @submit.prevent="submit" class="space-y-4">
      <BaseInput v-model="email" label="Email" type="email" required autocomplete="email" />
      <BaseInput v-model="username" label="Username" type="text" required autocomplete="username" />
      <BaseInput v-model="password" label="Password" type="password" required autocomplete="new-password" />

      <BaseAlert v-if="error" variant="error" :message="error" />

      <BaseButton type="submit" :loading="loading" block>Create account</BaseButton>
    </form>

    <p class="mt-5 text-center text-sm text-slate-500">
      Already have an account?
      <router-link to="/login" class="text-primary-600 hover:text-primary-700 dark:text-primary-400 hover:underline">Sign in</router-link>
    </p>
  </div>
</template>

<script setup>
import { ref } from "vue";
import BaseAlert from "../components/ui/BaseAlert.vue";
import BaseButton from "../components/ui/BaseButton.vue";
import BaseInput from "../components/ui/BaseInput.vue";
import { register } from "../services/auth.js";

const email = ref("");
const username = ref("");
const password = ref("");
const error = ref(null);
const loading = ref(false);
const success = ref(false);

async function submit() {
  error.value = null;
  loading.value = true;
  try {
    await register(email.value, username.value, password.value);
    success.value = true;
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}
</script>
