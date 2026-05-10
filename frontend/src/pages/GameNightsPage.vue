<template>
  <div class="max-w-3xl mx-auto px-4 sm:px-6 py-8">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-slate-900 dark:text-white">Game Nights</h1>
    </div>

    <div v-if="loading" class="space-y-3">
      <SkeletonLoader v-for="i in 5" :key="i" height="h-20" rounded="rounded-2xl" />
    </div>

    <BaseAlert v-else-if="error" variant="error" :message="error" />

    <div v-else-if="nights.length === 0" class="text-center py-20">
      <CalendarDaysIcon class="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
      <p class="text-slate-500 dark:text-slate-400 mb-4">No upcoming game nights across any of your groups.</p>
      <router-link to="/groups/new" class="text-sm text-primary-600 dark:text-primary-400 hover:underline">
        Create a group to get started
      </router-link>
    </div>

    <div v-else class="space-y-2">
      <template v-for="(group, idx) in grouped" :key="group.date">
        <!-- Date separator -->
        <div
          :class="idx > 0 ? 'mt-6' : ''"
          class="flex items-center gap-3 mb-2"
        >
          <div class="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide whitespace-nowrap">
            {{ formatDateHeading(group.date) }}
          </div>
          <div class="flex-1 h-px bg-slate-200 dark:bg-slate-700" />
        </div>

        <router-link
          v-for="night in group.nights"
          :key="night.id"
          :to="`/occurrences/${night.id}`"
          class="flex items-center justify-between bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-card hover:shadow-card-hover transition-all p-4 group"
        >
          <div class="flex items-center gap-4 min-w-0">
            <div class="min-w-0">
              <p class="font-medium text-slate-800 dark:text-slate-100 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors truncate">
                {{ night.series_title }}
              </p>
              <div class="flex items-center gap-2 mt-0.5">
                <router-link
                  :to="`/groups/${night.group_id}`"
                  @click.stop
                  class="text-xs text-slate-500 dark:text-slate-400 hover:text-primary-600 dark:hover:text-primary-400 hover:underline truncate"
                >
                  {{ night.group_name }}
                </router-link>
                <span class="text-slate-300 dark:text-slate-600">·</span>
                <span class="text-xs text-slate-400 dark:text-slate-500">{{ formatTime(night.start_time) }}</span>
              </div>
            </div>
          </div>

          <div class="flex items-center gap-2 flex-shrink-0 ml-3">
            <RsvpBadge :rsvp="night.my_rsvp" />
          </div>
        </router-link>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { CalendarDaysIcon } from "@heroicons/vue/24/outline";
import BaseAlert from "../components/ui/BaseAlert.vue";
import SkeletonLoader from "../components/ui/SkeletonLoader.vue";
import { request } from "../services/api.js";

const nights = ref([]);
const loading = ref(true);
const error = ref(null);

const grouped = computed(() => {
  const map = new Map();
  for (const night of nights.value) {
    if (!map.has(night.occurrence_date)) map.set(night.occurrence_date, []);
    map.get(night.occurrence_date).push(night);
  }
  return [...map.entries()].map(([date, items]) => ({ date, nights: items }));
});

onMounted(async () => {
  try {
    const res = await request("/api/me/occurrences");
    if (!res.ok) throw new Error("Failed to load game nights");
    nights.value = await res.json();
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
});

function formatDateHeading(iso) {
  const d = new Date(iso + "T00:00:00");
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const tomorrow = new Date(today);
  tomorrow.setDate(today.getDate() + 1);
  if (d.getTime() === today.getTime()) return "Today";
  if (d.getTime() === tomorrow.getTime()) return "Tomorrow";
  return d.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" });
}

function formatTime(t) {
  if (!t) return "";
  const [h, m] = t.split(":");
  return new Date(0, 0, 0, +h, +m).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

const RsvpBadge = {
  props: { rsvp: { type: String, default: null } },
  template: `
    <span v-if="rsvp" :class="{
      'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300': rsvp === 'yes',
      'bg-red-100 text-red-600 dark:bg-red-950 dark:text-red-400': rsvp === 'no',
      'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300': rsvp === 'maybe',
    }" class="text-xs px-2 py-0.5 rounded-full capitalize font-medium">{{ rsvp }}</span>
    <span v-else class="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-400 dark:bg-slate-700 dark:text-slate-500">No RSVP</span>
  `,
};
</script>
