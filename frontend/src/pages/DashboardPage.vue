<template>
  <div class="max-w-4xl mx-auto px-4 sm:px-6 py-8">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold text-slate-900 dark:text-white">My Groups</h1>
      <BaseButton to="/groups/new" size="sm">+ New group</BaseButton>
    </div>

    <div v-if="loading" class="space-y-3">
      <SkeletonLoader v-for="i in 3" :key="i" height="h-24" rounded="rounded-2xl" />
    </div>

    <BaseAlert v-else-if="error" variant="error" :message="error" />

    <div v-else-if="groups.length === 0" class="text-center py-20">
      <div class="w-16 h-16 mx-auto mb-4 rounded-2xl bg-primary-100 dark:bg-primary-950 flex items-center justify-center">
        <UserGroupIcon class="w-8 h-8 text-primary-600 dark:text-primary-400" />
      </div>
      <p class="text-slate-600 dark:text-slate-400 mb-4">No groups yet.</p>
      <BaseButton to="/groups/new">Create your first group</BaseButton>
    </div>

    <div v-else class="grid gap-4 sm:grid-cols-2">
      <router-link
        v-for="group in groups"
        :key="group.id"
        :to="`/groups/${group.id}`"
        class="block bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-card hover:shadow-card-hover transition-all p-5 group"
      >
        <div class="flex justify-between items-start gap-3">
          <div class="flex-1 min-w-0">
            <h3 class="font-semibold text-slate-900 dark:text-white truncate group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
              {{ group.name }}
            </h3>
            <p v-if="group.description" class="text-sm text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-2">
              {{ group.description }}
            </p>
          </div>
          <span :class="roleClasses(group.my_role)" class="text-xs px-2 py-0.5 rounded-full capitalize flex-shrink-0">
            {{ group.my_role }}
          </span>
        </div>
        <p class="text-xs text-slate-400 dark:text-slate-500 mt-3">
          {{ group.member_count }} {{ group.member_count === 1 ? "member" : "members" }}
        </p>
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { UserGroupIcon } from "@heroicons/vue/24/outline";
import BaseAlert from "../components/ui/BaseAlert.vue";
import BaseButton from "../components/ui/BaseButton.vue";
import SkeletonLoader from "../components/ui/SkeletonLoader.vue";
import { request } from "../services/api.js";

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

function roleClasses(role) {
  return {
    organiser: "bg-primary-100 text-primary-700 dark:bg-primary-950 dark:text-primary-300",
    owner: "bg-primary-100 text-primary-700 dark:bg-primary-950 dark:text-primary-300",
    member: "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300",
  }[role] ?? "bg-slate-100 text-slate-600";
}
</script>
