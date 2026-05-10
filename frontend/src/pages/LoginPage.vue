<template>
  <div>
    <h1 class="text-2xl font-bold text-slate-900 dark:text-white mb-1">Welcome back</h1>
    <p class="text-sm text-slate-500 dark:text-slate-400 mb-6">Sign in to your account</p>

    <form @submit.prevent="submit" class="space-y-4">
      <BaseInput v-model="email" label="Email" type="email" required autocomplete="email" :error="fieldErrors.email" />
      <BaseInput v-model="password" label="Password" type="password" required autocomplete="current-password" :error="fieldErrors.password" />

      <BaseAlert v-if="error" variant="error" :message="error" />

      <BaseButton type="submit" :loading="loading" block>Sign in</BaseButton>
    </form>

    <div class="mt-5 flex flex-col gap-2 text-center text-sm text-slate-500">
      <router-link to="/forgot-password" class="text-primary-600 hover:text-primary-700 dark:text-primary-400 hover:underline">
        Forgot password?
      </router-link>
      <span>No account? <router-link to="/register" class="text-primary-600 hover:text-primary-700 dark:text-primary-400 hover:underline">Create one</router-link></span>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import BaseAlert from "../components/ui/BaseAlert.vue";
import BaseButton from "../components/ui/BaseButton.vue";
import BaseInput from "../components/ui/BaseInput.vue";
import { login } from "../services/auth.js";

const router = useRouter();
const route = useRoute();

const email = ref("");
const password = ref("");
const error = ref(null);
const fieldErrors = reactive({});
const loading = ref(false);

async function submit() {
  error.value = null;
  loading.value = true;
  try {
    await login(email.value, password.value);
    const next = route.query.next || "/dashboard";
    router.push(next);
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}
</script>
