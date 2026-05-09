<template>
  <div class="min-h-screen bg-gray-50 flex items-center justify-center">
    <div class="bg-white rounded-xl shadow-md p-10 max-w-md w-full text-center">
      <div v-if="loading" class="text-gray-400 animate-pulse">Loading…</div>

      <div v-else-if="error" class="text-red-500">
        <p class="mb-4">{{ error }}</p>
        <router-link to="/dashboard" class="text-blue-600 hover:underline">Go to dashboard</router-link>
      </div>

      <template v-else-if="preview">
        <h1 class="text-2xl font-bold text-gray-800 mb-2">You're invited!</h1>
        <p class="text-gray-500 text-sm mb-6">
          <strong>{{ preview.inviter_username }}</strong> has invited you to join
        </p>
        <div class="bg-gray-50 rounded-xl p-4 mb-6 text-left">
          <p class="font-semibold text-gray-800 text-lg">{{ preview.group_name }}</p>
          <p v-if="preview.group_description" class="text-sm text-gray-500 mt-1">{{ preview.group_description }}</p>
          <p class="text-xs text-gray-400 mt-2 capitalize">Role: {{ preview.role }}</p>
        </div>

        <div v-if="joined" class="text-green-600">
          <p class="mb-4 font-medium">You've joined the group!</p>
          <router-link :to="`/groups/${preview.group_id}`" class="text-blue-600 hover:underline">View group</router-link>
        </div>
        <template v-else-if="authed">
          <button @click="accept" :disabled="accepting"
            class="w-full bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50 mb-3">
            {{ accepting ? "Joining…" : "Join group" }}
          </button>
          <p v-if="acceptError" class="text-red-500 text-sm">{{ acceptError }}</p>
        </template>
        <template v-else>
          <p class="text-sm text-gray-500 mb-4">Sign in to join this group.</p>
          <router-link :to="`/login?next=/invites/${token}`"
            class="block w-full bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 mb-2">
            Sign in
          </router-link>
          <router-link :to="`/register?next=/invites/${token}`"
            class="block w-full border rounded-lg py-2 text-sm text-gray-700 hover:bg-gray-50">
            Create account
          </router-link>
        </template>
      </template>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
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
