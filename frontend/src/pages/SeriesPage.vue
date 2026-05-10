<template>
  <div class="max-w-3xl mx-auto px-4 sm:px-6 py-8">
    <!-- Breadcrumb -->
    <nav class="text-sm text-slate-500 dark:text-slate-400 mb-6 flex items-center gap-2">
      <router-link to="/game-nights" class="hover:text-slate-800 dark:hover:text-slate-200">Game Nights</router-link>
      <span>/</span>
      <router-link v-if="series" :to="`/groups/${series.group_id}`" class="hover:text-slate-800 dark:hover:text-slate-200">Group</router-link>
      <span>/</span>
      <span class="text-slate-800 dark:text-slate-200 font-medium">{{ series?.title ?? "Game Night" }}</span>
    </nav>

    <div v-if="loading" class="space-y-4">
      <SkeletonLoader height="h-8" width="w-56" />
      <SkeletonLoader height="h-4" width="w-40" />
    </div>
    <BaseAlert v-else-if="error" variant="error" :message="error" />

    <template v-else>
      <!-- Header -->
      <div class="flex justify-between items-start mb-6 gap-4">
        <div>
          <div class="flex items-center gap-2 mb-1">
            <h1 class="text-2xl font-bold text-slate-900 dark:text-white">{{ series.title }}</h1>
            <span :class="statusClass(series.status)" class="text-xs px-2 py-0.5 rounded-full capitalize">
              {{ series.status.replace("_", " ") }}
            </span>
          </div>
          <p v-if="series.description" class="text-sm text-slate-500 dark:text-slate-400">{{ series.description }}</p>
          <p class="text-xs text-slate-400 dark:text-slate-500 mt-1">{{ recurrenceLabel }}</p>
        </div>

        <div v-if="isOrganiser" class="flex gap-2 flex-shrink-0 flex-wrap justify-end">
          <template v-if="series.status === 'active'">
            <BaseButton @click="updateStatus('on_hold')" variant="secondary" size="sm">Pause</BaseButton>
            <BaseButton @click="updateStatus('cancelled')" variant="danger" size="sm">Cancel</BaseButton>
          </template>
          <BaseButton v-if="series.status === 'on_hold'" @click="updateStatus('active')" variant="primary" size="sm">Resume</BaseButton>
        </div>
      </div>

      <!-- Occurrences -->
      <div class="flex justify-between items-center mb-3">
        <h2 class="font-semibold text-slate-700 dark:text-slate-300">Upcoming nights</h2>
        <BaseButton v-if="isOrganiser" @click="showAddOcc = !showAddOcc" variant="ghost" size="sm">+ Add night</BaseButton>
      </div>

      <!-- Add occurrence form -->
      <BaseCard v-if="showAddOcc" class="mb-4">
        <h3 class="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">Add one-off night</h3>
        <div class="grid grid-cols-2 gap-3 mb-3">
          <BaseInput v-model="newOcc.date" label="Date" type="date" />
          <BaseInput v-model="newOcc.time" label="Time" type="time" />
        </div>
        <div class="flex gap-2">
          <BaseButton @click="addOccurrence" :loading="addingOcc" size="sm">Add</BaseButton>
          <BaseButton @click="showAddOcc = false" variant="ghost" size="sm">Cancel</BaseButton>
        </div>
        <BaseAlert v-if="addOccError" variant="error" :message="addOccError" class="mt-2" />
      </BaseCard>

      <div v-if="upcomingOccurrences.length === 0" class="text-sm text-slate-400 dark:text-slate-500 text-center py-10 bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700">
        No upcoming nights scheduled.
      </div>
      <div v-else class="space-y-3">
        <router-link v-for="occ in upcomingOccurrences" :key="occ.id" :to="`/occurrences/${occ.id}`"
          class="flex justify-between items-center bg-white dark:bg-slate-800 rounded-2xl p-4 border border-slate-200 dark:border-slate-700 shadow-card hover:shadow-card-hover transition-all group">
          <div>
            <p class="font-medium text-slate-800 dark:text-slate-100 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
              {{ formatDate(occ.occurrence_date) }}
            </p>
            <p class="text-xs text-slate-500 dark:text-slate-400">{{ formatTime(occ.start_time) }}</p>
          </div>
          <span :class="occStatusClass(occ.status)" class="text-xs px-2 py-0.5 rounded-full capitalize">{{ occ.status }}</span>
        </router-link>
        <button v-if="hiddenCount > 0 && !showAllOccurrences" @click="showAllOccurrences = true"
          class="w-full text-sm text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 py-2 text-center font-medium">
          Show {{ hiddenCount }} more upcoming night{{ hiddenCount !== 1 ? "s" : "" }}
        </button>
      </div>

      <!-- Availability polls -->
      <div class="flex justify-between items-center mt-8 mb-3">
        <h2 class="font-semibold text-slate-700 dark:text-slate-300">Availability polls</h2>
        <router-link v-if="isOrganiser" :to="`/series/${seriesId}/poll/new`"
          class="text-sm text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 font-medium">
          + New poll
        </router-link>
      </div>

      <div v-if="polls.length === 0" class="text-sm text-slate-400 dark:text-slate-500 text-center py-10 bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700">
        No polls yet.
        <template v-if="isOrganiser">
          <router-link :to="`/series/${seriesId}/poll/new`" class="block mt-1 text-primary-600 dark:text-primary-400 hover:underline">Create one</router-link>
        </template>
      </div>
      <div v-else class="space-y-3">
        <router-link v-for="poll in polls" :key="poll.id" :to="`/polls/${poll.id}`"
          class="flex justify-between items-center bg-white dark:bg-slate-800 rounded-2xl p-4 border border-slate-200 dark:border-slate-700 shadow-card hover:shadow-card-hover transition-all group">
          <div>
            <p class="font-medium text-slate-800 dark:text-slate-100 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
              {{ poll.title }}
            </p>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              {{ poll.options.length }} option{{ poll.options.length !== 1 ? "s" : "" }}
              <span v-if="poll.deadline"> · closes {{ formatDate(poll.deadline.slice(0, 10)) }}</span>
            </p>
          </div>
          <span :class="pollStatusClass(poll.status)" class="text-xs px-2 py-0.5 rounded-full capitalize flex-shrink-0">{{ poll.status }}</span>
        </router-link>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute } from "vue-router";
import BaseAlert from "../components/ui/BaseAlert.vue";
import BaseButton from "../components/ui/BaseButton.vue";
import BaseCard from "../components/ui/BaseCard.vue";
import BaseInput from "../components/ui/BaseInput.vue";
import SkeletonLoader from "../components/ui/SkeletonLoader.vue";
import { request } from "../services/api.js";

const route = useRoute();
const seriesId = route.params.id;

const series = ref(null);
const occurrences = ref([]);
const polls = ref([]);
const showAllOccurrences = ref(false);

const upcomingOccurrences = computed(() => {
  const today = new Date().toISOString().slice(0, 10);
  const upcoming = occurrences.value.filter((o) => o.occurrence_date >= today && o.status !== "cancelled");
  return showAllOccurrences.value ? upcoming : upcoming.slice(0, 5);
});
const hiddenCount = computed(() => {
  const today = new Date().toISOString().slice(0, 10);
  const upcoming = occurrences.value.filter((o) => o.occurrence_date >= today && o.status !== "cancelled");
  return Math.max(0, upcoming.length - 5);
});
const loading = ref(true);
const error = ref(null);
const isOrganiser = ref(false);
const showAddOcc = ref(false);
const addingOcc = ref(false);
const addOccError = ref(null);
const newOcc = reactive({ date: "", time: "19:00" });

onMounted(async () => {
  try {
    const [sRes, oRes] = await Promise.all([
      request(`/api/series/${seriesId}`),
      request(`/api/series/${seriesId}/occurrences`),
    ]);
    if (!sRes.ok) throw new Error("Failed to load series");
    series.value = await sRes.json();
    occurrences.value = oRes.ok ? await oRes.json() : [];

    const gRes = await request(`/api/groups/${series.value.group_id}`);
    if (gRes.ok) {
      const g = await gRes.json();
      isOrganiser.value = g.my_role === "organiser" || g.my_role === "owner";
    }

    const pRes = await request(`/api/series/${seriesId}/polls`);
    polls.value = pRes.ok ? await pRes.json() : [];
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
});

async function updateStatus(status) {
  const res = await request(`/api/series/${seriesId}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
  if (res.ok) series.value = await res.json();
}

async function addOccurrence() {
  addOccError.value = null;
  if (!newOcc.date || !newOcc.time) { addOccError.value = "Date and time are required"; return; }
  addingOcc.value = true;
  try {
    const res = await request(`/api/series/${seriesId}/occurrences`, {
      method: "POST",
      body: JSON.stringify({ occurrence_date: newOcc.date, start_time: `${newOcc.time}:00` }),
    });
    if (!res.ok) throw new Error("Failed to add occurrence");
    const occ = await res.json();
    occurrences.value = [...occurrences.value, occ].sort((a, b) => a.occurrence_date.localeCompare(b.occurrence_date));
    showAddOcc.value = false;
    newOcc.date = "";
    newOcc.time = "19:00";
  } catch (err) {
    addOccError.value = err.message;
  } finally {
    addingOcc.value = false;
  }
}

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const recurrenceLabel = computed(() => {
  if (!series.value) return "";
  const day = series.value.default_day_of_week != null ? DAYS[series.value.default_day_of_week] : "";
  return { once: "One-time event", weekly: `Every ${day}`, biweekly: `Every other ${day}`, monthly: "Monthly", custom: "Custom schedule" }[series.value.recurrence] ?? series.value.recurrence;
});

function formatDate(d) {
  return new Date(`${d}T00:00:00`).toLocaleDateString(undefined, { weekday: "long", year: "numeric", month: "long", day: "numeric" });
}
function formatTime(t) {
  if (!t) return "";
  const [h, m] = t.split(":");
  return new Date(0, 0, 0, h, m).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}
function statusClass(s) {
  return { active: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300", on_hold: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300", cancelled: "bg-red-100 text-red-600 dark:bg-red-950 dark:text-red-400", completed: "bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400" }[s] ?? "bg-slate-100 text-slate-500";
}
function occStatusClass(s) {
  return { scheduled: "bg-primary-100 text-primary-700 dark:bg-primary-950 dark:text-primary-300", postponed: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300", cancelled: "bg-red-100 text-red-600 dark:bg-red-950 dark:text-red-400" }[s] ?? "bg-slate-100 text-slate-500";
}
function pollStatusClass(s) {
  return { open: "bg-primary-100 text-primary-700 dark:bg-primary-950 dark:text-primary-300", closed: "bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400", resolved: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300" }[s] ?? "bg-slate-100 text-slate-500";
}
</script>
