<template>
  <div class="min-h-screen bg-slate-50 dark:bg-slate-900">
    <!-- Minimal header -->
    <header class="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
      <div class="max-w-3xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        <router-link to="/explore" class="flex items-center gap-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 rounded-lg">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" class="w-8 h-8" fill="none">
            <rect x="1" y="1" width="30" height="30" rx="6" fill="#0d9488"/>
            <circle cx="9" cy="10" r="2.5" fill="white"/>
            <circle cx="23" cy="10" r="2.5" fill="white"/>
            <circle cx="9" cy="22" r="2.5" fill="white"/>
            <circle cx="23" cy="22" r="2.5" fill="white"/>
            <circle cx="16" cy="16" r="2.5" fill="white"/>
          </svg>
          <span class="font-bold text-base text-slate-900 dark:text-white hidden sm:block tracking-tight">Game On Tabletop</span>
        </router-link>
        <div class="flex items-center gap-2">
          <router-link to="/login" class="text-sm font-medium text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white px-3 py-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors">
            Sign in
          </router-link>
          <router-link to="/register" class="text-sm font-medium bg-primary-600 hover:bg-primary-700 text-white px-3 py-1.5 rounded-lg transition-colors">
            Create account
          </router-link>
        </div>
      </div>
    </header>

    <main class="max-w-3xl mx-auto px-4 sm:px-6 py-10">
      <div v-if="loading" class="flex items-center gap-4">
        <div class="w-24 h-24 rounded-full bg-slate-200 dark:bg-slate-700 animate-pulse flex-shrink-0" />
        <div class="flex-1 space-y-3">
          <div class="h-6 bg-slate-200 dark:bg-slate-700 rounded w-1/2 animate-pulse" />
          <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/3 animate-pulse" />
        </div>
      </div>

      <div v-else-if="notFound" class="text-center py-20">
        <p class="text-slate-500 dark:text-slate-400 text-lg">This profile is private or does not exist.</p>
      </div>

      <template v-else>
        <div class="flex items-start gap-5">
          <BaseAvatar :src="profile.avatar_url || ''" :name="profile.display_name || profile.username" size="2xl" />
          <div class="flex-1 min-w-0">
            <h1 class="text-2xl font-bold text-slate-900 dark:text-white">
              {{ profile.display_name || profile.username }}
            </h1>
            <p class="text-sm text-slate-500 dark:text-slate-400">@{{ profile.username }}</p>
            <p class="text-xs text-slate-400 dark:text-slate-500 mt-1">
              Member since {{ formatDate(profile.member_since) }}
            </p>
            <p v-if="profile.bio" class="text-sm text-slate-600 dark:text-slate-300 mt-3 max-w-prose">{{ profile.bio }}</p>

            <div v-if="isOwnProfile" class="mt-3">
              <router-link to="/profile" class="text-xs text-primary-600 dark:text-primary-400 hover:underline">
                This is you — edit profile →
              </router-link>
            </div>
          </div>
        </div>

        <div v-if="profile.stats_public" class="mt-8 grid grid-cols-3 gap-4">
          <div class="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-4 text-center">
            <p class="text-2xl font-bold text-slate-900 dark:text-white">{{ profile.stats.total_plays }}</p>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">Total plays</p>
          </div>
          <div class="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-4 text-center">
            <p class="text-2xl font-bold text-slate-900 dark:text-white">{{ profile.stats.total_games_played }}</p>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">Games played</p>
          </div>
          <div class="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-4 text-center">
            <p class="text-2xl font-bold text-slate-900 dark:text-white">{{ profile.stats.games_owned }}</p>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">Games owned</p>
          </div>
        </div>
      </template>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import BaseAvatar from "../components/ui/BaseAvatar.vue";
import { isAuthenticated } from "../services/auth.js";
import { request } from "../services/api.js";

const route = useRoute();
const profile = ref(null);
const loading = ref(true);
const notFound = ref(false);
const currentUsername = ref(null);

onMounted(async () => {
  if (isAuthenticated()) {
    try {
      const res = await request("/api/users/me");
      if (res.ok) {
        const me = await res.json();
        currentUsername.value = me.username;
      }
    } catch { /* ignore */ }
  }

  try {
    const res = await fetch(`/api/public/profile/${route.params.username}`);
    if (res.status === 404) { notFound.value = true; return; }
    if (!res.ok) throw new Error();
    profile.value = await res.json();
  } catch {
    notFound.value = true;
  } finally {
    loading.value = false;
  }
});

const isOwnProfile = computed(
  () => currentUsername.value && profile.value && currentUsername.value === profile.value.username
);

function formatDate(iso) {
  return new Date(iso + "T00:00:00").toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
}
</script>
