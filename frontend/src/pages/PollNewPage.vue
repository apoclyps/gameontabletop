<template>
  <div class="max-w-2xl mx-auto px-4 sm:px-6 py-8">
    <nav class="text-sm text-slate-500 dark:text-slate-400 mb-6 flex items-center gap-2">
      <router-link to="/dashboard" class="hover:text-slate-800 dark:hover:text-slate-200">Dashboard</router-link>
      <span>/</span>
      <router-link v-if="seriesId" :to="`/series/${seriesId}`" class="hover:text-slate-800 dark:hover:text-slate-200">Series</router-link>
      <span>/</span>
      <span class="text-slate-800 dark:text-slate-200 font-medium">New poll</span>
    </nav>

    <h1 class="text-2xl font-bold text-slate-900 dark:text-white mb-6">Create availability poll</h1>

    <BaseAlert v-if="error" variant="error" :message="error" class="mb-4" />

    <BaseCard class="mb-4">
      <h2 class="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-4">Poll details</h2>
      <div class="space-y-4">
        <BaseInput v-model="form.title" label="Title" placeholder="e.g. When can everyone make it in June?" required />
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Description <span class="text-slate-400 font-normal">(optional)</span></label>
          <textarea v-model="form.description" rows="2"
            class="w-full rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 px-3 py-2 text-sm placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            placeholder="Any additional context…" />
        </div>
        <BaseInput v-model="form.deadline" label="Deadline" type="datetime-local" />
      </div>
    </BaseCard>

    <BaseCard class="mb-6">
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-sm font-semibold text-slate-700 dark:text-slate-300">Date options</h2>
        <BaseButton @click="addOption" variant="ghost" size="sm">+ Add option</BaseButton>
      </div>

      <div v-if="options.length === 0" class="text-sm text-slate-400 dark:text-slate-500 text-center py-4">
        Add at least one date option for people to vote on.
      </div>

      <div class="space-y-3">
        <div v-for="(opt, i) in options" :key="i"
          class="border border-slate-200 dark:border-slate-700 rounded-xl p-4 space-y-3">
          <div class="flex justify-between items-center">
            <span class="text-xs font-medium text-slate-500 dark:text-slate-400">Option {{ i + 1 }}</span>
            <button @click="removeOption(i)" class="text-xs text-red-500 hover:text-red-600 dark:hover:text-red-400">Remove</button>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <BaseInput v-model="opt.proposed_date" label="Date" type="date" required />
            <BaseInput v-model="opt.start_time" label="Start time" type="time" required />
            <BaseInput v-model="opt.end_time" label="End time" type="time" />
          </div>
        </div>
      </div>
    </BaseCard>

    <div class="flex gap-3">
      <BaseButton @click="submit" :loading="submitting" :disabled="options.length === 0 || !form.title">
        Create poll
      </BaseButton>
      <BaseButton @click="$router.back()" variant="ghost">Cancel</BaseButton>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import BaseAlert from "../components/ui/BaseAlert.vue";
import BaseButton from "../components/ui/BaseButton.vue";
import BaseCard from "../components/ui/BaseCard.vue";
import BaseInput from "../components/ui/BaseInput.vue";
import { request } from "../services/api.js";

const route = useRoute();
const router = useRouter();
const seriesId = route.params.id;

const form = reactive({ title: "", description: "", deadline: "" });
const options = ref([]);
const submitting = ref(false);
const error = ref(null);

function addOption() {
  options.value.push({ proposed_date: "", start_time: "19:00", end_time: "" });
}

function removeOption(i) {
  options.value.splice(i, 1);
}

async function submit() {
  error.value = null;
  if (!form.title.trim()) { error.value = "Title is required"; return; }
  if (options.value.length === 0) { error.value = "Add at least one date option"; return; }
  for (const opt of options.value) {
    if (!opt.proposed_date || !opt.start_time) { error.value = "Every option needs a date and start time"; return; }
  }

  submitting.value = true;
  try {
    const payload = {
      title: form.title.trim(),
      description: form.description.trim() || null,
      deadline: form.deadline ? new Date(form.deadline).toISOString() : null,
      options: options.value.map((opt, i) => ({
        proposed_date: opt.proposed_date,
        start_time: `${opt.start_time}:00`,
        end_time: opt.end_time ? `${opt.end_time}:00` : null,
        display_order: i,
      })),
    };
    const res = await request(`/api/series/${seriesId}/polls`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || "Failed to create poll");
    }
    const poll = await res.json();
    router.push(`/polls/${poll.id}`);
  } catch (err) {
    error.value = err.message;
  } finally {
    submitting.value = false;
  }
}
</script>
