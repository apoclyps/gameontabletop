<template>
  <div class="max-w-3xl mx-auto px-4 sm:px-6 py-8">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-slate-900 dark:text-white">Game Nights</h1>

      <!-- Upcoming / Past toggle -->
      <div class="flex rounded-lg border border-slate-200 dark:border-slate-700 overflow-hidden text-sm">
        <button
          @click="switchTab('upcoming')"
          :class="tab === 'upcoming'
            ? 'bg-primary-600 text-white'
            : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'"
          class="px-4 py-1.5 font-medium transition-colors"
        >
          Upcoming
        </button>
        <button
          @click="switchTab('past')"
          :class="tab === 'past'
            ? 'bg-primary-600 text-white'
            : 'bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700'"
          class="px-4 py-1.5 font-medium transition-colors border-l border-slate-200 dark:border-slate-700"
        >
          Past
        </button>
      </div>
    </div>

    <div v-if="loading" class="space-y-3">
      <SkeletonLoader v-for="i in 5" :key="i" height="h-20" rounded="rounded-2xl" />
    </div>

    <BaseAlert v-else-if="error" variant="error" :message="error" />

    <div v-else-if="grouped.length === 0" class="text-center py-20">
      <CalendarDaysIcon class="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
      <p class="text-slate-500 dark:text-slate-400 mb-4">
        {{ tab === 'past' ? 'No past game nights found.' : 'No upcoming game nights across any of your groups.' }}
      </p>
      <router-link v-if="tab === 'upcoming'" to="/groups/new" class="text-sm text-primary-600 dark:text-primary-400 hover:underline">
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
                <template v-if="tab === 'past' && night.notes">
                  <span class="text-slate-300 dark:text-slate-600">·</span>
                  <span class="text-xs text-slate-400 dark:text-slate-500 truncate max-w-[120px]">{{ night.notes }}</span>
                </template>
              </div>
            </div>
          </div>

          <div class="flex items-center gap-2 flex-shrink-0 ml-3">
            <span v-if="tab === 'past'" class="text-xs px-2 py-0.5 rounded-full font-medium whitespace-nowrap bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400">
              Past
            </span>
            <span v-else :class="seqLabel(night._seqIdx).class" class="text-xs px-2 py-0.5 rounded-full font-medium whitespace-nowrap">
              {{ seqLabel(night._seqIdx).text }}
            </span>
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
const tab = ref("upcoming");

async function fetchNights() {
  loading.value = true;
  error.value = null;
  try {
    const url = tab.value === "past" ? "/api/me/occurrences?past=true" : "/api/me/occurrences";
    const res = await request(url);
    if (!res.ok) throw new Error("Failed to load game nights");
    nights.value = await res.json();
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

function switchTab(t) {
  tab.value = t;
  fetchNights();
}

const grouped = computed(() => {
  const map = new Map();
  for (const night of nights.value) {
    if (!map.has(night.occurrence_date)) map.set(night.occurrence_date, []);
    map.get(night.occurrence_date).push(night);
  }
  let idx = 0;
  return [...map.entries()].map(([date, items]) => ({
    date,
    nights: items.map((n) => ({ ...n, _seqIdx: idx++ })),
  }));
});

function seqLabel(idx) {
  if (idx === 0) return { text: "Next up", class: "bg-primary-100 text-primary-700 dark:bg-primary-950 dark:text-primary-300" };
  if (idx === 1) return { text: "Scheduled", class: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300" };
  return { text: "Upcoming", class: "bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400" };
}

onMounted(fetchNights);

function formatDateHeading(iso) {
  const d = new Date(iso + "T00:00:00");
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const tomorrow = new Date(today);
  tomorrow.setDate(today.getDate() + 1);
  if (tab.value === "upcoming") {
    if (d.getTime() === today.getTime()) return "Today";
    if (d.getTime() === tomorrow.getTime()) return "Tomorrow";
  }
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
