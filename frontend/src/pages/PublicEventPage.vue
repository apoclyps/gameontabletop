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
      <div v-if="loading" class="space-y-4">
        <div class="h-8 bg-slate-200 dark:bg-slate-700 rounded w-1/2 animate-pulse" />
        <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/3 animate-pulse" />
      </div>

      <div v-else-if="notFound" class="text-center py-20">
        <p class="text-slate-500 dark:text-slate-400 text-lg">Event not found or no longer public.</p>
        <router-link to="/explore" class="mt-4 inline-block text-primary-600 dark:text-primary-400 hover:underline text-sm">
          ← Back to explore
        </router-link>
      </div>

      <template v-else>
        <nav class="text-sm text-slate-500 dark:text-slate-400 mb-6 flex items-center gap-2">
          <router-link to="/explore" class="hover:text-slate-800 dark:hover:text-slate-200">Explore</router-link>
          <span>/</span>
          <span class="text-slate-800 dark:text-slate-200 font-medium">{{ event.group_name }}</span>
        </nav>

        <h1 class="text-2xl font-bold text-slate-900 dark:text-white">{{ event.series_title }}</h1>
        <p class="text-slate-500 dark:text-slate-400 mt-1">{{ event.group_name }}</p>

        <div class="mt-6 bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-6 space-y-4">
          <div class="flex items-center gap-3 text-slate-700 dark:text-slate-200">
            <CalendarIcon class="w-5 h-5 text-slate-400 flex-shrink-0" />
            <span class="font-medium">{{ formatDate(event.occurrence_date) }}</span>
          </div>
          <div class="flex items-center gap-3 text-slate-700 dark:text-slate-200">
            <ClockIcon class="w-5 h-5 text-slate-400 flex-shrink-0" />
            <span>
              {{ formatTime(event.start_time) }}
              <span v-if="event.end_time"> – {{ formatTime(event.end_time) }}</span>
            </span>
          </div>
          <div v-if="event.rsvp_yes_count > 0" class="flex items-center gap-3 text-emerald-600 dark:text-emerald-400">
            <UserGroupIcon class="w-5 h-5 flex-shrink-0" />
            <span class="font-medium">{{ event.rsvp_yes_count }} going</span>
          </div>
        </div>

        <div class="mt-8 bg-primary-50 dark:bg-primary-950 border border-primary-200 dark:border-primary-800 rounded-2xl p-6 text-center">
          <p class="text-slate-700 dark:text-slate-200 font-medium mb-3">Want to RSVP?</p>
          <div class="flex justify-center gap-3">
            <router-link to="/login" class="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium rounded-xl transition-colors">
              Sign in
            </router-link>
            <router-link to="/register" class="px-4 py-2 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 text-sm font-medium rounded-xl hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors">
              Create account
            </router-link>
          </div>
        </div>
      </template>
    </main>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { CalendarIcon, ClockIcon, UserGroupIcon } from "@heroicons/vue/24/outline";

const route = useRoute();
const event = ref(null);
const loading = ref(true);
const notFound = ref(false);

onMounted(async () => {
  try {
    const res = await fetch(`/api/public/events/${route.params.id}`);
    if (res.status === 404) { notFound.value = true; return; }
    if (!res.ok) throw new Error();
    event.value = await res.json();
  } catch {
    notFound.value = true;
  } finally {
    loading.value = false;
  }
});

function formatDate(iso) {
  return new Date(iso + "T00:00:00").toLocaleDateString(undefined, { weekday: "long", year: "numeric", month: "long", day: "numeric" });
}

function formatTime(t) {
  const [h, m] = t.split(":");
  const d = new Date();
  d.setHours(Number(h), Number(m));
  return d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}
</script>
