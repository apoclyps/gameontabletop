<template>
  <div>
    <h1 class="text-2xl font-bold text-slate-900 dark:text-white mb-6">Reset password</h1>

    <BaseAlert v-if="!token" variant="error" message="Invalid reset link. Please request a new one." />

    <BaseAlert v-else-if="success" variant="success" message="Password reset successfully!" />
    <div v-if="success" class="mt-4 text-center">
      <router-link to="/login" class="text-primary-600 hover:underline text-sm">Sign in with your new password</router-link>
    </div>

    <form v-else-if="token" @submit.prevent="submit" class="space-y-4">
      <BaseInput v-model="password" label="New password" type="password" required autocomplete="new-password" />

      <BaseAlert v-if="error" variant="error" :message="error" />

      <BaseButton type="submit" :loading="loading" block>Reset password</BaseButton>
    </form>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRoute } from "vue-router";
import BaseAlert from "../components/ui/BaseAlert.vue";
import BaseButton from "../components/ui/BaseButton.vue";
import BaseInput from "../components/ui/BaseInput.vue";
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
