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
          <UserPlusIcon class="w-6 h-6 text-primary-600 dark:text-primary-400" />
        </div>
      </div>
      <h1 class="text-2xl font-bold text-slate-900 dark:text-white mt-4 mb-1">Friend invite</h1>
      <p class="text-sm text-slate-500 dark:text-slate-400 mb-5">
        <strong class="text-slate-700 dark:text-slate-300">{{ preview.inviter_display_name || preview.inviter_username }}</strong>
        has invited you to connect on Game On Tabletop
      </p>

      <div v-if="connected">
        <BaseAlert variant="success" message="You're now friends!" class="mb-4 text-left" />
        <BaseButton to="/friends" block>View friends</BaseButton>
      </div>
      <template v-else-if="authed">
        <BaseButton @click="accept" :loading="accepting" block>Add as friend</BaseButton>
        <BaseAlert v-if="acceptError" variant="error" :message="acceptError" class="mt-3 text-left" />
      </template>
      <template v-else>
        <p class="text-sm text-slate-500 dark:text-slate-400 mb-4">
          Sign in to connect with {{ preview.inviter_display_name || preview.inviter_username }}.
        </p>
        <BaseButton :to="`/login?next=${encodedPath}`" block class="mb-2">Sign in</BaseButton>
        <BaseButton :to="`/register?next=${encodedPath}`" variant="secondary" block>Create account</BaseButton>
      </template>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { UserPlusIcon } from "@heroicons/vue/24/outline";
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
const connected = ref(false);
const authed = isAuthenticated();

const encodedPath = computed(() => encodeURIComponent(`/friend-invite/${token}`));

const apiBase = import.meta.env.VITE_API_BASE_URL || "";

onMounted(async () => {
  try {
    const res = await fetch(`${apiBase}/api/friends/invite/${token}`);
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
    const res = await request(`/api/friends/invite/${token}/accept`, { method: "POST" });
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || "Failed to add friend");
    }
    connected.value = true;
  } catch (err) {
    acceptError.value = err.message;
  } finally {
    accepting.value = false;
  }
}
</script>
