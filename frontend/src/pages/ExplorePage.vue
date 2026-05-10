<template>
  <div class="min-h-screen bg-slate-50 dark:bg-slate-900">
    <!-- Minimal header -->
    <header class="bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
      <div class="max-w-5xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        <router-link to="/" class="flex items-center gap-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 rounded-lg">
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
          <router-link
            to="/login"
            class="text-sm font-medium text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white px-3 py-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
          >
            Sign in
          </router-link>
          <router-link
            to="/register"
            class="text-sm font-medium bg-primary-600 hover:bg-primary-700 text-white px-3 py-1.5 rounded-lg transition-colors"
          >
            Create account
          </router-link>
        </div>
      </div>
    </header>

    <main class="max-w-5xl mx-auto px-4 sm:px-6 py-10">
      <div class="mb-8">
        <h1 class="text-3xl font-bold text-slate-900 dark:text-white">Upcoming games nights</h1>
        <p class="text-slate-500 dark:text-slate-400 mt-2">Browse public games nights from groups near you.</p>
      </div>

      <div v-if="loading" class="grid sm:grid-cols-2 gap-4">
        <div v-for="i in 4" :key="i" class="bg-white dark:bg-slate-800 rounded-2xl p-5 border border-slate-200 dark:border-slate-700 animate-pulse">
          <div class="h-4 bg-slate-200 dark:bg-slate-700 rounded w-3/4 mb-3" />
          <div class="h-3 bg-slate-200 dark:bg-slate-700 rounded w-1/2 mb-2" />
          <div class="h-3 bg-slate-200 dark:bg-slate-700 rounded w-1/3" />
        </div>
      </div>

      <div v-else-if="events.length === 0" class="text-center py-20">
        <p class="text-slate-500 dark:text-slate-400 text-lg mb-4">No public games nights scheduled yet.</p>
        <router-link
          to="/register"
          class="inline-block bg-primary-600 hover:bg-primary-700 text-white font-medium px-5 py-2.5 rounded-xl transition-colors"
        >
          Organise your own → Sign up
        </router-link>
      </div>

      <div v-else class="grid sm:grid-cols-2 gap-4">
        <router-link
          v-for="event in events"
          :key="event.id"
          :to="`/events/${event.id}`"
          class="bg-white dark:bg-slate-800 rounded-2xl p-5 border border-slate-200 dark:border-slate-700 shadow-sm hover:shadow-md transition-all group block"
        >
          <p class="font-semibold text-slate-900 dark:text-white group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
            {{ event.group_name }}
          </p>
          <p class="text-sm text-slate-500 dark:text-slate-400 mt-0.5">{{ event.series_title }}</p>
          <div class="mt-3 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
            <span>{{ formatDate(event.occurrence_date) }} · {{ formatTime(event.start_time) }}</span>
            <span v-if="event.rsvp_yes_count > 0" class="text-emerald-600 dark:text-emerald-400 font-medium">
              {{ event.rsvp_yes_count }} going
            </span>
          </div>
        </router-link>
      </div>

      <div v-if="hasMore" class="mt-8 text-center">
        <button
          @click="loadMore"
          :disabled="loadingMore"
          class="px-5 py-2.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-sm font-medium text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors disabled:opacity-50"
        >
          {{ loadingMore ? "Loading…" : "Load more" }}
        </button>
      </div>
    </main>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";

const events = ref([]);
const loading = ref(true);
const loadingMore = ref(false);
const page = ref(1);
const perPage = 20;
const hasMore = ref(false);

onMounted(() => fetchEvents());

async function fetchEvents() {
  try {
    const res = await fetch(`/api/public/events?page=1&per_page=${perPage}`);
    if (!res.ok) throw new Error("Failed to load events");
    const data = await res.json();
    events.value = data;
    hasMore.value = data.length === perPage;
  } finally {
    loading.value = false;
  }
}

async function loadMore() {
  loadingMore.value = true;
  try {
    page.value++;
    const res = await fetch(`/api/public/events?page=${page.value}&per_page=${perPage}`);
    if (!res.ok) return;
    const data = await res.json();
    events.value.push(...data);
    hasMore.value = data.length === perPage;
  } finally {
    loadingMore.value = false;
  }
}

function formatDate(iso) {
  return new Date(iso + "T00:00:00").toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
}

function formatTime(t) {
  const [h, m] = t.split(":");
  const d = new Date();
  d.setHours(Number(h), Number(m));
  return d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}
</script>
