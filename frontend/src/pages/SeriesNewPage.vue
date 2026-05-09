<template>
  <div class="min-h-screen bg-gray-50 flex items-center justify-center">
    <div class="bg-white rounded-xl shadow-md p-10 max-w-lg w-full">
      <div class="flex items-center gap-3 mb-6">
        <router-link :to="`/groups/${groupId}`" class="text-gray-400 hover:text-gray-600">← Back</router-link>
        <h1 class="text-2xl font-bold text-gray-800">New series</h1>
      </div>

      <form @submit.prevent="submit" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Title <span class="text-red-500">*</span></label>
          <input v-model="form.title" type="text" required maxlength="200"
            class="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Description</label>
          <textarea v-model="form.description" rows="2"
            class="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Recurrence <span class="text-red-500">*</span></label>
          <select v-model="form.recurrence" required
            class="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
            <option value="once">One-time event</option>
            <option value="weekly">Weekly</option>
            <option value="biweekly">Every two weeks</option>
            <option value="monthly">Monthly</option>
          </select>
        </div>

        <div v-if="form.recurrence !== 'once'">
          <label class="block text-sm font-medium text-gray-700 mb-1">Day of week</label>
          <select v-model.number="form.default_day_of_week"
            class="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
            <option :value="null">— not specified —</option>
            <option v-for="(d, i) in DAYS" :key="i" :value="i">{{ d }}</option>
          </select>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Start date</label>
            <input v-model="form.series_start_date" type="date"
              class="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Start time</label>
            <input v-model="form.default_start_time" type="time"
              class="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">Duration (minutes)</label>
          <input v-model.number="form.default_duration_minutes" type="number" min="15" max="720"
            class="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
        </div>

        <p v-if="error" class="text-red-500 text-sm">{{ error }}</p>
        <button type="submit" :disabled="loading"
          class="w-full bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
          {{ loading ? "Creating…" : "Create series" }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { request } from "../services/api.js";

const route = useRoute();
const router = useRouter();
const groupId = route.params.id;

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

const loading = ref(false);
const error = ref(null);
const form = reactive({
  title: "",
  description: "",
  recurrence: "weekly",
  default_day_of_week: null,
  series_start_date: "",
  default_start_time: "19:00",
  default_duration_minutes: null,
});

async function submit() {
  error.value = null;
  loading.value = true;
  try {
    const payload = {
      title: form.title,
      description: form.description || null,
      recurrence: form.recurrence,
      default_day_of_week: form.default_day_of_week,
      series_start_date: form.series_start_date || null,
      default_start_time: form.default_start_time ? `${form.default_start_time}:00` : null,
      default_duration_minutes: form.default_duration_minutes || null,
    };
    const res = await request(`/api/groups/${groupId}/series`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || "Failed to create series");
    }
    const series = await res.json();
    router.push(`/series/${series.id}`);
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}
</script>
