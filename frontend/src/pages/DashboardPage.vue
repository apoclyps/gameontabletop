<template>
  <div class="min-h-screen bg-gray-50">
    <nav class="bg-white shadow-sm px-6 py-3 flex justify-between items-center">
      <h1 class="text-lg font-bold text-gray-800">Game On Tabletop</h1>
      <div class="flex gap-4 text-sm">
        <router-link to="/profile" class="text-gray-500 hover:text-gray-800">Profile</router-link>
        <button @click="handleLogout" class="text-gray-500 hover:text-red-500">Sign out</button>
      </div>
    </nav>

    <main class="max-w-3xl mx-auto px-4 py-8">
      <div class="flex justify-between items-center mb-6">
        <h2 class="text-xl font-bold text-gray-800">My Groups</h2>
        <router-link
          to="/groups/new"
          class="bg-blue-600 text-white text-sm px-4 py-2 rounded-lg hover:bg-blue-700"
        >+ New group</router-link>
      </div>

      <div v-if="loading" class="text-gray-400 animate-pulse text-center py-12">Loading…</div>
      <div v-else-if="error" class="text-red-500 text-sm text-center py-12">{{ error }}</div>
      <div v-else-if="groups.length === 0" class="text-center py-16 text-gray-500">
        <p class="mb-4 text-lg">No groups yet.</p>
        <router-link to="/groups/new" class="text-blue-600 hover:underline">Create your first group</router-link>
      </div>

      <div v-else class="space-y-4">
        <router-link
          v-for="group in groups"
          :key="group.id"
          :to="`/groups/${group.id}`"
          class="block bg-white rounded-xl shadow-sm p-5 hover:shadow-md transition-shadow border border-gray-100"
        >
          <div class="flex justify-between items-start">
            <div>
              <h3 class="font-semibold text-gray-800">{{ group.name }}</h3>
              <p v-if="group.description" class="text-sm text-gray-500 mt-0.5">{{ group.description }}</p>
            </div>
            <span class="text-xs text-gray-400 bg-gray-100 rounded-full px-2 py-0.5 capitalize">
              {{ group.my_role }}
            </span>
          </div>
          <p class="text-xs text-gray-400 mt-3">
            {{ group.member_count }} {{ group.member_count === 1 ? 'member' : 'members' }}
          </p>
        </router-link>
      </div>
    </main>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { request } from "../services/api.js";
import { logout } from "../services/auth.js";

const router = useRouter();
const groups = ref([]);
const loading = ref(true);
const error = ref(null);

onMounted(async () => {
  try {
    const res = await request("/api/groups");
    if (!res.ok) throw new Error("Failed to load groups");
    groups.value = await res.json();
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
});

async function handleLogout() {
  await logout();
  router.push("/login");
}
</script>
