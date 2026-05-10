<template>
  <div class="max-w-2xl mx-auto px-4 sm:px-6 py-8">
    <!-- Breadcrumb -->
    <nav class="text-sm text-slate-500 dark:text-slate-400 mb-6 flex items-center gap-2">
      <router-link to="/dashboard" class="hover:text-slate-800 dark:hover:text-slate-200">Dashboard</router-link>
      <span>/</span>
      <router-link v-if="occurrence" :to="`/series/${occurrence.series_id}`" class="hover:text-slate-800 dark:hover:text-slate-200">Series</router-link>
      <span>/</span>
      <span class="text-slate-800 dark:text-slate-200 font-medium">{{ occurrence ? formatDate(occurrence.occurrence_date) : "Night" }}</span>
    </nav>

    <div v-if="loading" class="space-y-4">
      <SkeletonLoader height="h-8" width="w-64" />
      <SkeletonLoader height="h-4" width="w-32" />
    </div>
    <BaseAlert v-else-if="error" variant="error" :message="error" />

    <template v-else>
      <!-- Details -->
      <BaseCard class="mb-4">
        <div class="flex justify-between items-start mb-4">
          <div>
            <h1 class="text-2xl font-bold text-slate-900 dark:text-white">{{ formatDate(occurrence.occurrence_date) }}</h1>
            <p class="text-slate-500 dark:text-slate-400 text-sm mt-1">
              {{ formatTime(occurrence.start_time) }}
              <span v-if="occurrence.end_time"> – {{ formatTime(occurrence.end_time) }}</span>
            </p>
            <p v-if="occurrence.notes" class="text-sm text-slate-600 dark:text-slate-300 mt-2">{{ occurrence.notes }}</p>
            <p v-if="occurrence.postponed_from_date" class="text-xs text-amber-600 dark:text-amber-400 mt-1">
              Moved from {{ formatDate(occurrence.postponed_from_date) }}
            </p>
          </div>
          <span :class="occStatusClass(occurrence.status)" class="text-xs px-2 py-0.5 rounded-full capitalize flex-shrink-0">
            {{ occurrence.status }}
          </span>
        </div>

        <!-- Organiser controls -->
        <div v-if="isOrganiser && occurrence.status === 'scheduled'" class="flex gap-2 flex-wrap pt-2 border-t border-slate-100 dark:border-slate-700">
          <div class="flex gap-2 items-center">
            <input v-model="postponeDate" type="date"
              class="border border-slate-300 dark:border-slate-600 rounded-lg px-2 py-1 text-xs bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-primary-500" />
            <BaseButton @click="postpone" :disabled="!postponeDate" variant="secondary" size="sm">Postpone</BaseButton>
          </div>
          <BaseButton @click="cancel" variant="danger" size="sm">Cancel night</BaseButton>
        </div>
      </BaseCard>

      <!-- RSVP section -->
      <BaseCard class="mb-4">
        <h2 class="font-semibold text-slate-700 dark:text-slate-300 mb-4">Are you coming?</h2>

        <div v-if="occurrence.status === 'cancelled'" class="text-sm text-slate-500 dark:text-slate-400">
          This night has been cancelled.
        </div>
        <template v-else>
          <div class="flex gap-3 mb-4">
            <button v-for="choice in ['yes', 'maybe', 'no']" :key="choice"
              @click="submitRsvp(choice)"
              :disabled="submittingRsvp"
              :class="rsvpButtonClass(choice)"
              class="flex-1 rounded-xl py-2.5 text-sm font-semibold border-2 transition-all disabled:opacity-50 capitalize focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-primary-500"
            >
              {{ choice === "yes" ? "✓ Yes" : choice === "no" ? "✗ No" : "~ Maybe" }}
            </button>
          </div>
          <p v-if="myRsvp" class="text-xs text-slate-500 dark:text-slate-400">
            Your RSVP: <span class="font-medium capitalize">{{ myRsvp.response }}</span>
            <span v-if="myRsvp.note"> — "{{ myRsvp.note }}"</span>
          </p>
        </template>

        <!-- Counts -->
        <div class="flex gap-6 mt-4 pt-4 border-t border-slate-100 dark:border-slate-700">
          <div v-for="(count, label) in occurrence.rsvp_counts" :key="label" class="text-center">
            <p class="text-xl font-bold" :class="countColor(label)">{{ count }}</p>
            <p class="text-xs text-slate-500 dark:text-slate-400 capitalize">{{ label }}</p>
          </div>
        </div>
      </BaseCard>

      <!-- Who's coming -->
      <BaseCard v-if="rsvps.length > 0" padding="none" flush>
        <div class="px-6 py-4 border-b border-slate-100 dark:border-slate-700">
          <h2 class="font-semibold text-slate-700 dark:text-slate-300">Who's coming</h2>
        </div>
        <div class="divide-y divide-slate-100 dark:divide-slate-700">
          <div v-for="r in rsvps" :key="r.id" class="flex justify-between items-center px-6 py-3">
            <div class="flex items-center gap-3">
              <BaseAvatar :name="r.username" size="sm" />
              <span class="text-sm text-slate-700 dark:text-slate-200">{{ r.username }}</span>
            </div>
            <span :class="responseColor(r.response)" class="capitalize font-medium text-xs">{{ r.response }}</span>
          </div>
        </div>
      </BaseCard>
    </template>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import BaseAlert from "../components/ui/BaseAlert.vue";
import BaseAvatar from "../components/ui/BaseAvatar.vue";
import BaseButton from "../components/ui/BaseButton.vue";
import BaseCard from "../components/ui/BaseCard.vue";
import SkeletonLoader from "../components/ui/SkeletonLoader.vue";
import { request } from "../services/api.js";

const route = useRoute();
const occurrenceId = route.params.id;

const occurrence = ref(null);
const rsvps = ref([]);
const myRsvp = ref(null);
const loading = ref(true);
const error = ref(null);
const isOrganiser = ref(false);
const submittingRsvp = ref(false);
const postponeDate = ref("");

onMounted(async () => {
  try {
    const [oRes, rRes] = await Promise.all([
      request(`/api/occurrences/${occurrenceId}`),
      request(`/api/occurrences/${occurrenceId}/rsvps`),
    ]);
    if (!oRes.ok) throw new Error("Failed to load occurrence");
    occurrence.value = await oRes.json();
    rsvps.value = rRes.ok ? await rRes.json() : [];

    const seriesRes = await request(`/api/series/${occurrence.value.series_id}`);
    if (seriesRes.ok) {
      const s = await seriesRes.json();
      const gRes = await request(`/api/groups/${s.group_id}`);
      if (gRes.ok) {
        const g = await gRes.json();
        isOrganiser.value = g.my_role === "organiser" || g.my_role === "owner";
      }
    }

    const me = await (await request("/api/users/me")).json();
    myRsvp.value = rsvps.value.find((r) => r.username === me.username) ?? null;
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
});

async function submitRsvp(choice) {
  submittingRsvp.value = true;
  try {
    const res = await request(`/api/occurrences/${occurrenceId}/rsvp`, {
      method: "POST",
      body: JSON.stringify({ response: choice }),
    });
    if (!res.ok) throw new Error("RSVP failed");
    const updated = await res.json();
    myRsvp.value = updated;
    const existing = rsvps.value.findIndex((r) => r.id === updated.id);
    if (existing >= 0) rsvps.value[existing] = updated;
    else rsvps.value = [...rsvps.value, updated];
    const oRes = await request(`/api/occurrences/${occurrenceId}`);
    if (oRes.ok) occurrence.value = await oRes.json();
  } finally {
    submittingRsvp.value = false;
  }
}

async function postpone() {
  const res = await request(`/api/occurrences/${occurrenceId}`, {
    method: "PATCH",
    body: JSON.stringify({ status: "postponed", occurrence_date: postponeDate.value }),
  });
  if (res.ok) occurrence.value = await res.json();
}

async function cancel() {
  const res = await request(`/api/occurrences/${occurrenceId}`, {
    method: "PATCH",
    body: JSON.stringify({ status: "cancelled" }),
  });
  if (res.ok) occurrence.value = await res.json();
}

function formatDate(d) {
  return new Date(`${d}T00:00:00`).toLocaleDateString(undefined, { weekday: "long", year: "numeric", month: "long", day: "numeric" });
}
function formatTime(t) {
  if (!t) return "";
  const [h, m] = t.split(":");
  return new Date(0, 0, 0, h, m).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}
function occStatusClass(s) {
  return { scheduled: "bg-primary-100 text-primary-700 dark:bg-primary-950 dark:text-primary-300", postponed: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300", cancelled: "bg-red-100 text-red-600 dark:bg-red-950 dark:text-red-400" }[s] ?? "bg-slate-100 text-slate-500";
}
function rsvpButtonClass(choice) {
  const active = myRsvp.value?.response === choice;
  if (active) return { yes: "bg-emerald-600 border-emerald-600 text-white", maybe: "bg-amber-500 border-amber-500 text-white", no: "bg-red-500 border-red-500 text-white" }[choice];
  return "bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-slate-600 hover:border-slate-400 dark:hover:border-slate-400";
}
function countColor(label) {
  return { yes: "text-emerald-600 dark:text-emerald-400", maybe: "text-amber-600 dark:text-amber-400", no: "text-red-500 dark:text-red-400" }[label] ?? "text-slate-700";
}
function responseColor(r) {
  return { yes: "text-emerald-600 dark:text-emerald-400", maybe: "text-amber-600 dark:text-amber-400", no: "text-red-500 dark:text-red-400" }[r] ?? "text-slate-500";
}
</script>
