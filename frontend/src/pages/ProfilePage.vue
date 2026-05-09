<template>
  <div class="min-h-screen bg-gray-50 flex items-center justify-center">
    <div class="bg-white rounded-xl shadow-md p-10 max-w-md w-full">
      <div class="flex justify-between items-center mb-6">
        <h1 class="text-2xl font-bold text-gray-800">Profile</h1>
        <button @click="handleLogout" class="text-sm text-gray-500 hover:text-red-500">Sign out</button>
      </div>

      <div v-if="loading" class="text-gray-400 animate-pulse text-center">Loading…</div>
      <div v-else-if="fetchError" class="text-red-500 text-sm text-center">{{ fetchError }}</div>
      <template v-else>
        <div class="mb-6 text-sm text-gray-600 space-y-1">
          <p><span class="font-medium">Email:</span> {{ user.email }}</p>
          <p><span class="font-medium">Username:</span> {{ user.username }}</p>
          <p><span class="font-medium">Member since:</span> {{ new Date(user.created_at).toLocaleDateString() }}</p>
        </div>

        <form @submit.prevent="save" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Display name</label>
            <input v-model="form.display_name" type="text"
              class="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Bio</label>
            <textarea v-model="form.bio" rows="3"
              class="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Avatar URL</label>
            <input v-model="form.avatar_url" type="url"
              class="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <p v-if="saveError" class="text-red-500 text-sm">{{ saveError }}</p>
          <p v-if="saved" class="text-green-600 text-sm">Saved!</p>
          <button type="submit" :disabled="saving"
            class="w-full bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
            {{ saving ? "Saving…" : "Save changes" }}
          </button>
        </form>
      </template>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { request } from "../services/api.js";
import { logout } from "../services/auth.js";

const router = useRouter();
const user = ref(null);
const loading = ref(true);
const fetchError = ref(null);
const saving = ref(false);
const saveError = ref(null);
const saved = ref(false);
const form = reactive({ display_name: "", bio: "", avatar_url: "" });

onMounted(async () => {
  try {
    const res = await request("/api/users/me");
    if (!res.ok) throw new Error("Failed to load profile");
    user.value = await res.json();
    form.display_name = user.value.display_name || "";
    form.bio = user.value.bio || "";
    form.avatar_url = user.value.avatar_url || "";
  } catch (err) {
    fetchError.value = err.message;
  } finally {
    loading.value = false;
  }
});

async function save() {
  saveError.value = null;
  saved.value = false;
  saving.value = true;
  try {
    const res = await request("/api/users/me", {
      method: "PATCH",
      body: JSON.stringify(form),
    });
    if (!res.ok) throw new Error("Save failed");
    user.value = await res.json();
    saved.value = true;
    setTimeout(() => (saved.value = false), 3000);
  } catch (err) {
    saveError.value = err.message;
  } finally {
    saving.value = false;
  }
}

async function handleLogout() {
  await logout();
  router.push("/login");
}
</script>
