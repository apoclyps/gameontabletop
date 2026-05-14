<template>
  <div class="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-6">
    <div class="flex items-center gap-3">
      <router-link
        to="/admin"
        class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
        aria-label="Back to admin"
      >
        <ChevronLeftIcon class="w-5 h-5" />
      </router-link>
      <h1 class="text-2xl font-bold text-slate-900 dark:text-white">Users</h1>
    </div>

    <div v-if="loading" class="space-y-2">
      <div
        v-for="i in 8"
        :key="i"
        class="h-14 bg-slate-100 dark:bg-slate-800 rounded-xl animate-pulse"
      />
    </div>

    <div v-else-if="error" class="text-center py-12 text-red-500 dark:text-red-400 text-sm">
      {{ error }}
    </div>

    <div v-else>
      <div class="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 overflow-hidden">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-slate-200 dark:border-slate-700 text-left">
              <th class="px-4 py-3 font-medium text-slate-500 dark:text-slate-400">User</th>
              <th class="px-4 py-3 font-medium text-slate-500 dark:text-slate-400 hidden sm:table-cell">Email</th>
              <th class="px-4 py-3 font-medium text-slate-500 dark:text-slate-400 hidden md:table-cell">Joined</th>
              <th class="px-4 py-3 font-medium text-slate-500 dark:text-slate-400 text-center">Status</th>
              <th class="px-4 py-3 font-medium text-slate-500 dark:text-slate-400 text-center">Admin</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 dark:divide-slate-700">
            <tr
              v-for="u in page.users"
              :key="u.id"
              class="hover:bg-slate-50 dark:hover:bg-slate-750 transition-colors"
            >
              <td class="px-4 py-3">
                <div class="font-medium text-slate-900 dark:text-white">{{ u.display_name || u.username }}</div>
                <div class="text-xs text-slate-400">@{{ u.username }}</div>
              </td>
              <td class="px-4 py-3 text-slate-600 dark:text-slate-300 hidden sm:table-cell">{{ u.email }}</td>
              <td class="px-4 py-3 text-slate-400 hidden md:table-cell">{{ formatDate(u.created_at) }}</td>
              <td class="px-4 py-3 text-center">
                <span
                  :class="u.is_active
                    ? 'bg-green-100 dark:bg-green-950 text-green-700 dark:text-green-300'
                    : 'bg-red-100 dark:bg-red-950 text-red-700 dark:text-red-300'"
                  class="inline-block px-2 py-0.5 rounded-full text-xs font-medium"
                >
                  {{ u.is_active ? "Active" : "Disabled" }}
                </span>
              </td>
              <td class="px-4 py-3 text-center">
                <button
                  @click="toggleAdmin(u)"
                  :disabled="u.id === currentUserId || updating === u.id"
                  :title="u.id === currentUserId ? 'Cannot change your own role' : ''"
                  :class="[
                    'relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500',
                    u.is_admin ? 'bg-primary-600' : 'bg-slate-200 dark:bg-slate-600',
                    (u.id === currentUserId || updating === u.id) ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer',
                  ]"
                  role="switch"
                  :aria-checked="u.is_admin"
                >
                  <span
                    :class="u.is_admin ? 'translate-x-4' : 'translate-x-0.5'"
                    class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform shadow-sm"
                  />
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="page.total > page.page_size" class="flex items-center justify-between pt-2 text-sm text-slate-500 dark:text-slate-400">
        <span>{{ page.total }} users total</span>
        <div class="flex gap-2">
          <button
            @click="changePage(page.page - 1)"
            :disabled="page.page <= 1"
            class="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Previous
          </button>
          <button
            @click="changePage(page.page + 1)"
            :disabled="page.page * page.page_size >= page.total"
            class="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { ChevronLeftIcon } from "@heroicons/vue/24/outline";
import { useCurrentUser } from "../composables/useCurrentUser.js";
import { request } from "../services/api.js";

const { user } = useCurrentUser();
const currentUserId = ref(null);
const loading = ref(true);
const error = ref(null);
const updating = ref(null);
const page = ref({ users: [], total: 0, page: 1, page_size: 20 });

onMounted(async () => {
  if (user.value) currentUserId.value = user.value.id;
  await loadPage(1);
});

async function loadPage(p) {
  loading.value = true;
  error.value = null;
  try {
    const res = await request(`/api/admin/users?page=${p}&page_size=20`);
    if (!res.ok) throw new Error("Failed to load users");
    page.value = await res.json();
    if (user.value) currentUserId.value = user.value.id;
  } catch (e) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
}

async function changePage(p) {
  await loadPage(p);
}

async function toggleAdmin(u) {
  if (u.id === currentUserId.value) return;
  updating.value = u.id;
  try {
    const res = await request(`/api/admin/users/${u.id}/role`, {
      method: "PATCH",
      body: JSON.stringify({ is_admin: !u.is_admin }),
    });
    if (!res.ok) throw new Error("Update failed");
    const updated = await res.json();
    const idx = page.value.users.findIndex((x) => x.id === u.id);
    if (idx !== -1) page.value.users[idx] = updated;
  } catch {
    // silently restore
  } finally {
    updating.value = null;
  }
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}
</script>
