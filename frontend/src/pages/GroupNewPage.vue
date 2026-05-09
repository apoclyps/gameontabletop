<template>
  <div class="min-h-screen bg-gray-50 flex items-center justify-center">
    <div class="bg-white rounded-xl shadow-md p-10 max-w-md w-full">
      <div class="flex items-center gap-3 mb-6">
        <router-link to="/dashboard" class="text-gray-400 hover:text-gray-600">← Back</router-link>
        <h1 class="text-2xl font-bold text-gray-800">New group</h1>
      </div>

      <form @submit.prevent="submit" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Group name <span class="text-red-500">*</span></label>
          <input v-model="form.name" type="text" required maxlength="100"
            class="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Description</label>
          <textarea v-model="form.description" rows="3"
            class="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="What kind of games do you play?" />
        </div>
        <div class="flex items-center gap-2">
          <input v-model="form.is_public" type="checkbox" id="is_public" class="rounded" />
          <label for="is_public" class="text-sm text-gray-700">Public group (discoverable)</label>
        </div>
        <p v-if="error" class="text-red-500 text-sm">{{ error }}</p>
        <button type="submit" :disabled="loading"
          class="w-full bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
          {{ loading ? "Creating…" : "Create group" }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { request } from "../services/api.js";

const router = useRouter();
const loading = ref(false);
const error = ref(null);
const form = reactive({ name: "", description: "", is_public: false });

async function submit() {
  error.value = null;
  loading.value = true;
  try {
    const res = await request("/api/groups", {
      method: "POST",
      body: JSON.stringify(form),
    });
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || "Failed to create group");
    }
    const group = await res.json();
    router.push(`/groups/${group.id}`);
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}
</script>
