<template>
  <div class="max-w-5xl mx-auto px-4 sm:px-6 py-8">
    <!-- Breadcrumb -->
    <nav class="text-sm text-slate-500 dark:text-slate-400 mb-6 flex items-center gap-2">
      <router-link to="/friends" class="hover:text-slate-800 dark:hover:text-slate-200">Friends</router-link>
      <span>/</span>
      <span class="text-slate-800 dark:text-slate-200 font-medium">
        {{ profile ? (profile.display_name || profile.username) : "Collection" }}
      </span>
    </nav>

    <!-- Profile header -->
    <div v-if="profile" class="flex items-center gap-4 mb-6">
      <BaseAvatar :name="profile.display_name || profile.username" :src="profile.avatar_url" size="lg" />
      <div>
        <h1 class="text-2xl font-bold text-slate-900 dark:text-white">
          {{ profile.display_name || profile.username }}'s collection
        </h1>
        <p class="text-sm text-slate-500 dark:text-slate-400">@{{ profile.username }}</p>
      </div>
    </div>

    <!-- Status tabs -->
    <div v-if="!loading && entries.length > 0" class="flex gap-1 mb-6 bg-slate-100 dark:bg-slate-800 rounded-xl p-1 w-fit">
      <button
        v-for="tab in TABS"
        :key="tab.value"
        @click="activeTab = tab.value"
        :class="activeTab === tab.value
          ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
          : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'"
        class="px-3 py-1.5 text-sm font-medium rounded-lg transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <SkeletonLoader v-for="i in 6" :key="i" height="h-40" rounded="rounded-2xl" />
    </div>

    <BaseAlert v-else-if="error" variant="error" :message="error" />

    <div v-else-if="filteredEntries.length === 0" class="text-center py-20 text-slate-500 dark:text-slate-400">
      <PuzzlePieceIcon class="w-10 h-10 mx-auto mb-3 text-slate-300 dark:text-slate-600" />
      <p>No games visible in this collection.</p>
    </div>

    <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <div v-for="entry in filteredEntries" :key="entry.id"
        class="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-card overflow-hidden">
        <div class="h-32 bg-slate-100 dark:bg-slate-700 flex items-center justify-center overflow-hidden">
          <img v-if="entry.game_thumbnail_url" :src="entry.game_thumbnail_url" :alt="entry.game_title" class="w-full h-full object-cover" />
          <PuzzlePieceIcon v-else class="w-10 h-10 text-slate-300 dark:text-slate-600" />
        </div>
        <div class="p-4">
          <div class="flex justify-between items-start gap-2">
            <h3 class="font-semibold text-slate-900 dark:text-white text-sm leading-tight">{{ entry.game_title }}</h3>
            <span :class="statusClass(entry.status)" class="text-xs px-2 py-0.5 rounded-full capitalize flex-shrink-0 whitespace-nowrap">
              {{ entry.status.replace('_', ' ') }}
            </span>
          </div>
          <p v-if="entry.min_players || entry.max_players" class="text-xs text-slate-400 dark:text-slate-500 mt-1">
            {{ entry.min_players }}–{{ entry.max_players }} players
          </p>
          <p v-if="entry.notes" class="text-xs text-slate-500 dark:text-slate-400 mt-2 line-clamp-2">{{ entry.notes }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { PuzzlePieceIcon } from "@heroicons/vue/24/outline";
import BaseAlert from "../components/ui/BaseAlert.vue";
import BaseAvatar from "../components/ui/BaseAvatar.vue";
import SkeletonLoader from "../components/ui/SkeletonLoader.vue";
import { request } from "../services/api.js";

const route = useRoute();
const userId = route.params.userId;

const TABS = [
  { label: "All", value: "all" },
  { label: "Owned", value: "own" },
  { label: "Wishlist", value: "wishlist" },
  { label: "Want to play", value: "want_to_play" },
];

const profile = ref(null);
const entries = ref([]);
const loading = ref(true);
const error = ref(null);
const activeTab = ref("all");

const filteredEntries = computed(() =>
  activeTab.value === "all" ? entries.value : entries.value.filter((e) => e.status === activeTab.value)
);

onMounted(async () => {
  try {
    const [pRes, cRes] = await Promise.all([
      request(`/api/users/${userId}/profile`),
      request(`/api/users/${userId}/collection`),
    ]);
    if (pRes.ok) profile.value = await pRes.json();
    entries.value = cRes.ok ? await cRes.json() : [];
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
});

function statusClass(s) {
  return {
    own: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
    wishlist: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
    want_to_play: "bg-primary-100 text-primary-700 dark:bg-primary-950 dark:text-primary-300",
    previously_owned: "bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400",
  }[s] ?? "bg-slate-100 text-slate-500";
}
</script>
