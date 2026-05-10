<template>
  <div class="text-center">
    <div v-if="loading" class="space-y-3">
      <SkeletonLoader height="h-6" width="w-48" class="mx-auto" />
      <SkeletonLoader height="h-4" width="w-64" class="mx-auto" />
    </div>

    <BaseAlert v-else-if="error" variant="error" :message="error" class="text-left" />
    <div v-if="error" class="mt-4">
      <router-link to="/dashboard" class="text-primary-600 hover:underline text-sm">Go to dashboard</router-link>
    </div>

    <template v-else-if="preview">
      <div class="mb-1 flex justify-center">
        <div class="w-12 h-12 rounded-2xl bg-primary-100 dark:bg-primary-950 flex items-center justify-center">
          <UserGroupIcon class="w-6 h-6 text-primary-600 dark:text-primary-400" />
        </div>
      </div>
      <h1 class="text-2xl font-bold text-slate-900 dark:text-white mt-4 mb-1">You're invited!</h1>
      <p class="text-sm text-slate-500 dark:text-slate-400 mb-5">
        <strong class="text-slate-700 dark:text-slate-300">{{ preview.inviter_username }}</strong> has invited you to join
      </p>

      <div class="bg-slate-50 dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-700 p-4 mb-5 text-left">
        <p class="font-semibold text-slate-900 dark:text-white text-lg">{{ preview.group_name }}</p>
        <p v-if="preview.group_description" class="text-sm text-slate-500 dark:text-slate-400 mt-1">{{ preview.group_description }}</p>
        <p class="text-xs text-slate-400 dark:text-slate-500 mt-2 capitalize">Role: {{ preview.role }}</p>
      </div>

      <div v-if="joined">
        <BaseAlert variant="success" message="You've joined the group!" class="mb-4 text-left" />
        <BaseButton :to="`/groups/${preview.group_id}`" block>View group</BaseButton>
      </div>
      <template v-else-if="authed">
        <BaseButton @click="accept" :loading="accepting" block>Join group</BaseButton>
        <BaseAlert v-if="acceptError" variant="error" :message="acceptError" class="mt-3 text-left" />
      </template>
      <template v-else>
        <p class="text-sm text-slate-500 dark:text-slate-400 mb-4">Sign in to join this group.</p>
        <BaseButton :to="`/login?next=/invites/${token}`" block class="mb-2">Sign in</BaseButton>
        <BaseButton :to="`/register?next=/invites/${token}`" variant="secondary" block>Create account</BaseButton>
      </template>
    </template>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { UserGroupIcon } from "@heroicons/vue/24/outline";
import BaseAlert from "../components/ui/BaseAlert.vue";
import BaseButton from "../components/ui/BaseButton.vue";
import SkeletonLoader from "../components/ui/SkeletonLoader.vue";
import { isAuthenticated } from "../services/auth.js";
import { request } from "../services/api.js";

const route = useRoute();
const token = route.params.token;

const preview = ref(null);
const loading = ref(true);
const error = ref(null);
const accepting = ref(false);
const acceptError = ref(null);
const joined = ref(false);
const authed = isAuthenticated();

const apiBase = import.meta.env.VITE_API_BASE_URL || "";

onMounted(async () => {
  try {
    const res = await fetch(`${apiBase}/api/invites/${token}`);
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || "Invite not found or expired");
    }
    preview.value = await res.json();
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
});

async function accept() {
  accepting.value = true;
  acceptError.value = null;
  try {
    const res = await request(`/api/invites/${token}/accept`, { method: "POST" });
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || "Failed to join group");
    }
    joined.value = true;
  } catch (err) {
    acceptError.value = err.message;
  } finally {
    accepting.value = false;
  }
}
</script>
