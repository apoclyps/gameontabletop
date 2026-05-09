<template>
  <div class="min-h-screen bg-gray-50">
    <nav class="bg-white shadow-sm px-6 py-3 flex gap-3 items-center text-sm text-gray-500">
      <router-link to="/dashboard" class="hover:text-gray-800">Dashboard</router-link>
      <span>/</span>
      <router-link v-if="series" :to="`/groups/${series.group_id}`" class="hover:text-gray-800">Group</router-link>
      <span>/</span>
      <span class="text-gray-800 font-medium">{{ series?.title ?? "Series" }}</span>
    </nav>

    <main class="max-w-3xl mx-auto px-4 py-8">
      <div v-if="loading" class="text-gray-400 animate-pulse text-center py-12">Loading…</div>
      <div v-else-if="error" class="text-red-500 text-sm text-center py-12">{{ error }}</div>
      <template v-else>
        <!-- Header -->
        <div class="flex justify-between items-start mb-6">
          <div>
            <div class="flex items-center gap-2 mb-1">
              <h1 class="text-2xl font-bold text-gray-800">{{ series.title }}</h1>
              <span :class="statusClass(series.status)" class="text-xs px-2 py-0.5 rounded-full capitalize">
                {{ series.status.replace("_", " ") }}
              </span>
            </div>
            <p v-if="series.description" class="text-sm text-gray-500">{{ series.description }}</p>
            <p class="text-xs text-gray-400 mt-1">{{ recurrenceLabel }}</p>
          </div>

          <div v-if="isOrganiser" class="flex flex-col gap-2 items-end">
            <div v-if="series.status === 'active'" class="flex gap-2">
              <button @click="updateStatus('on_hold')"
                class="text-xs border rounded px-2 py-1 hover:bg-gray-50">Pause</button>
              <button @click="updateStatus('cancelled')"
                class="text-xs border border-red-300 text-red-600 rounded px-2 py-1 hover:bg-red-50">Cancel</button>
            </div>
            <button v-if="series.status === 'on_hold'" @click="updateStatus('active')"
              class="text-xs bg-green-600 text-white rounded px-3 py-1 hover:bg-green-700">Resume</button>
          </div>
        </div>

        <!-- Occurrences -->
        <div class="flex justify-between items-center mb-3">
          <h2 class="font-semibold text-gray-700">Upcoming nights</h2>
          <button v-if="isOrganiser" @click="showAddOcc = !showAddOcc"
            class="text-sm text-blue-600 hover:underline">+ Add night</button>
        </div>

        <!-- Add occurrence form -->
        <div v-if="showAddOcc" class="bg-white border rounded-xl p-4 mb-4">
          <h3 class="text-sm font-medium text-gray-700 mb-3">Add one-off night</h3>
          <div class="grid grid-cols-2 gap-3 mb-3">
            <div>
              <label class="block text-xs text-gray-500 mb-1">Date</label>
              <input v-model="newOcc.date" type="date"
                class="w-full border rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">Time</label>
              <input v-model="newOcc.time" type="time"
                class="w-full border rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
          </div>
          <div class="flex gap-2">
            <button @click="addOccurrence" :disabled="addingOcc"
              class="text-sm bg-blue-600 text-white rounded px-3 py-1.5 hover:bg-blue-700 disabled:opacity-50">
              {{ addingOcc ? "Adding…" : "Add" }}
            </button>
            <button @click="showAddOcc = false" class="text-sm text-gray-500 hover:text-gray-700">Cancel</button>
          </div>
          <p v-if="addOccError" class="text-red-500 text-xs mt-2">{{ addOccError }}</p>
        </div>

        <div v-if="occurrences.length === 0" class="text-sm text-gray-400 text-center py-8 bg-white rounded-xl border">
          No upcoming nights scheduled.
        </div>
        <div v-else class="space-y-3">
          <router-link
            v-for="occ in occurrences"
            :key="occ.id"
            :to="`/occurrences/${occ.id}`"
            class="block bg-white rounded-xl p-4 border border-gray-100 hover:shadow-sm transition-shadow"
          >
            <div class="flex justify-between items-center">
              <div>
                <p class="font-medium text-gray-800">{{ formatDate(occ.occurrence_date) }}</p>
                <p class="text-xs text-gray-500">{{ formatTime(occ.start_time) }}</p>
              </div>
              <span :class="occStatusClass(occ.status)" class="text-xs px-2 py-0.5 rounded-full capitalize">
                {{ occ.status }}
              </span>
            </div>
          </router-link>
        </div>
      </template>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute } from "vue-router";
import { request } from "../services/api.js";

const route = useRoute();
const seriesId = route.params.id;

const series = ref(null);
const occurrences = ref([]);
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
      isOrganiser.value = g.my_role === "organiser";
    }
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
  if (!newOcc.date || !newOcc.time) {
    addOccError.value = "Date and time are required";
    return;
  }
  addingOcc.value = true;
  try {
    const res = await request(`/api/series/${seriesId}/occurrences`, {
      method: "POST",
      body: JSON.stringify({
        occurrence_date: newOcc.date,
        start_time: `${newOcc.time}:00`,
      }),
    });
    if (!res.ok) throw new Error("Failed to add occurrence");
    const occ = await res.json();
    occurrences.value = [...occurrences.value, occ].sort((a, b) =>
      a.occurrence_date.localeCompare(b.occurrence_date)
    );
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
  const labels = {
    once: "One-time event",
    weekly: `Every ${day}`,
    biweekly: `Every other ${day}`,
    monthly: "Monthly",
    custom: "Custom schedule",
  };
  return labels[series.value.recurrence] ?? series.value.recurrence;
});

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

function statusClass(s) {
  return { active: "bg-green-100 text-green-700", on_hold: "bg-yellow-100 text-yellow-700", cancelled: "bg-red-100 text-red-600", completed: "bg-gray-100 text-gray-500" }[s] ?? "bg-gray-100 text-gray-500";
}

function occStatusClass(s) {
  return { scheduled: "bg-blue-100 text-blue-700", postponed: "bg-yellow-100 text-yellow-700", cancelled: "bg-red-100 text-red-600" }[s] ?? "bg-gray-100 text-gray-500";
}
</script>
