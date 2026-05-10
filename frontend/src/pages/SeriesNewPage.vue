<template>
  <div class="max-w-lg mx-auto px-4 sm:px-6 py-8">
    <div class="flex items-center gap-3 mb-6">
      <router-link :to="`/groups/${groupId}`" class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 rounded-lg p-0.5">
        <ArrowLeftIcon class="w-5 h-5" />
      </router-link>
      <h1 class="text-2xl font-bold text-slate-900 dark:text-white">New game night</h1>
    </div>

    <BaseCard>
      <form @submit.prevent="submit" class="space-y-4">
        <BaseInput v-model="form.title" label="Title" required maxlength="200" placeholder="Friday Night Board Games" />
        <BaseInput v-model="form.description" label="Description" type="textarea" :rows="2" />

        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
            Recurrence <span class="text-red-500">*</span>
          </label>
          <select v-model="form.recurrence" required
            class="w-full border border-slate-300 dark:border-slate-600 rounded-xl px-3 py-2 text-sm text-slate-900 dark:text-slate-100 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-primary-500">
            <option value="once">One-time event</option>
            <option value="weekly">Weekly</option>
            <option value="biweekly">Every two weeks</option>
            <option value="monthly">Monthly</option>
          </select>
        </div>

        <div v-if="form.recurrence !== 'once'">
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Day of week</label>
          <select v-model.number="form.default_day_of_week"
            class="w-full border border-slate-300 dark:border-slate-600 rounded-xl px-3 py-2 text-sm text-slate-900 dark:text-slate-100 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-primary-500">
            <option :value="null">— not specified —</option>
            <option v-for="(d, i) in DAYS" :key="i" :value="i">{{ d }}</option>
          </select>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <BaseInput v-model="form.series_start_date" label="Start date" type="date" />
          <BaseInput v-model="form.default_start_time" label="Start time" type="time" />
        </div>

        <BaseInput v-model.number="form.default_duration_minutes" label="Duration (minutes)" type="number" hint="Leave blank for open-ended" />

        <BaseAlert v-if="error" variant="error" :message="error" />

        <BaseButton type="submit" :loading="loading" block>Create game night</BaseButton>
      </form>
    </BaseCard>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ArrowLeftIcon } from "@heroicons/vue/24/outline";
import BaseAlert from "../components/ui/BaseAlert.vue";
import BaseButton from "../components/ui/BaseButton.vue";
import BaseCard from "../components/ui/BaseCard.vue";
import BaseInput from "../components/ui/BaseInput.vue";
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
