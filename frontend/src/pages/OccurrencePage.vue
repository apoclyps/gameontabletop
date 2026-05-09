<template>
  <div class="min-h-screen bg-gray-50">
    <nav class="bg-white shadow-sm px-6 py-3 flex gap-3 items-center text-sm text-gray-500">
      <router-link to="/dashboard" class="hover:text-gray-800">Dashboard</router-link>
      <span>/</span>
      <router-link v-if="occurrence" :to="`/series/${occurrence.series_id}`" class="hover:text-gray-800">Series</router-link>
      <span>/</span>
      <span class="text-gray-800 font-medium">{{ occurrence ? formatDate(occurrence.occurrence_date) : "Night" }}</span>
    </nav>

    <main class="max-w-2xl mx-auto px-4 py-8">
      <div v-if="loading" class="text-gray-400 animate-pulse text-center py-12">Loading…</div>
      <div v-else-if="error" class="text-red-500 text-sm text-center py-12">{{ error }}</div>
      <template v-else>
        <!-- Details -->
        <div class="bg-white rounded-xl shadow-sm p-6 mb-6">
          <div class="flex justify-between items-start mb-4">
            <div>
              <h1 class="text-2xl font-bold text-gray-800">{{ formatDate(occurrence.occurrence_date) }}</h1>
              <p class="text-gray-500 text-sm mt-1">
                {{ formatTime(occurrence.start_time) }}
                <span v-if="occurrence.end_time"> – {{ formatTime(occurrence.end_time) }}</span>
              </p>
              <p v-if="occurrence.notes" class="text-sm text-gray-600 mt-2">{{ occurrence.notes }}</p>
              <p v-if="occurrence.postponed_from_date" class="text-xs text-yellow-600 mt-1">
                Moved from {{ formatDate(occurrence.postponed_from_date) }}
              </p>
            </div>
            <span :class="occStatusClass(occurrence.status)" class="text-xs px-2 py-0.5 rounded-full capitalize">
              {{ occurrence.status }}
            </span>
          </div>

          <!-- Organiser controls -->
          <div v-if="isOrganiser && occurrence.status === 'scheduled'" class="flex gap-2 flex-wrap">
            <div class="flex gap-2 items-center">
              <input v-model="postponeDate" type="date" class="border rounded px-2 py-1 text-xs" />
              <button @click="postpone" :disabled="!postponeDate"
                class="text-xs border border-yellow-400 text-yellow-700 rounded px-2 py-1 hover:bg-yellow-50 disabled:opacity-50">
                Postpone
              </button>
            </div>
            <button @click="cancel"
              class="text-xs border border-red-300 text-red-600 rounded px-2 py-1 hover:bg-red-50">
              Cancel night
            </button>
          </div>
        </div>

        <!-- RSVP section -->
        <div class="bg-white rounded-xl shadow-sm p-6 mb-6">
          <h2 class="font-semibold text-gray-700 mb-4">Are you coming?</h2>

          <div v-if="occurrence.status === 'cancelled'" class="text-sm text-gray-500">
            This night has been cancelled.
          </div>
          <template v-else>
            <div class="flex gap-3 mb-4">
              <button
                v-for="choice in ['yes', 'maybe', 'no']"
                :key="choice"
                @click="submitRsvp(choice)"
                :disabled="submittingRsvp"
                :class="rsvpButtonClass(choice)"
                class="flex-1 rounded-lg py-2 text-sm font-medium border transition-colors disabled:opacity-50 capitalize"
              >
                {{ choice === 'yes' ? '✓ Yes' : choice === 'no' ? '✗ No' : '~ Maybe' }}
              </button>
            </div>
            <p v-if="myRsvp" class="text-xs text-gray-500">
              Your RSVP: <span class="font-medium capitalize">{{ myRsvp.response }}</span>
              <span v-if="myRsvp.note"> — "{{ myRsvp.note }}"</span>
            </p>
          </template>

          <!-- RSVP counts -->
          <div class="flex gap-6 mt-4 pt-4 border-t">
            <div v-for="(count, label) in occurrence.rsvp_counts" :key="label" class="text-center">
              <p class="text-lg font-bold" :class="countColor(label)">{{ count }}</p>
              <p class="text-xs text-gray-500 capitalize">{{ label }}</p>
            </div>
          </div>
        </div>

        <!-- Attendee list -->
        <div v-if="rsvps.length > 0" class="bg-white rounded-xl shadow-sm p-6">
          <h2 class="font-semibold text-gray-700 mb-3">Who's coming</h2>
          <div class="space-y-2">
            <div v-for="r in rsvps" :key="r.id" class="flex justify-between items-center text-sm">
              <span class="text-gray-700">{{ r.username }}</span>
              <span :class="responseColor(r.response)" class="capitalize font-medium text-xs">{{ r.response }}</span>
            </div>
          </div>
        </div>
      </template>
    </main>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
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
        isOrganiser.value = g.my_role === "organiser";
      }
    }

    const me = (await (await request("/api/users/me")).json());
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
  return new Date(`${d}T00:00:00`).toLocaleDateString(undefined, {
    weekday: "long", year: "numeric", month: "long", day: "numeric",
  });
}

function formatTime(t) {
  if (!t) return "";
  const [h, m] = t.split(":");
  return new Date(0, 0, 0, h, m).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

function occStatusClass(s) {
  return { scheduled: "bg-blue-100 text-blue-700", postponed: "bg-yellow-100 text-yellow-700", cancelled: "bg-red-100 text-red-600" }[s] ?? "bg-gray-100 text-gray-500";
}

function rsvpButtonClass(choice) {
  const active = myRsvp.value?.response === choice;
  if (active) {
    return { yes: "bg-green-600 text-white border-green-600", maybe: "bg-yellow-500 text-white border-yellow-500", no: "bg-red-500 text-white border-red-500" }[choice];
  }
  return "bg-white text-gray-700 border-gray-300 hover:bg-gray-50";
}

function countColor(label) {
  return { yes: "text-green-600", maybe: "text-yellow-600", no: "text-red-500" }[label] ?? "text-gray-700";
}

function responseColor(r) {
  return { yes: "text-green-600", maybe: "text-yellow-600", no: "text-red-400" }[r] ?? "text-gray-500";
}
</script>
