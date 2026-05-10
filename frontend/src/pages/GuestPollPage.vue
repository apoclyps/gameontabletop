<template>
  <div class="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-start justify-center pt-16 px-4">
    <div class="w-full max-w-lg">
      <div class="text-center mb-8">
        <h1 class="text-2xl font-bold text-slate-900 dark:text-white">Game On Tabletop</h1>
        <p class="text-slate-500 dark:text-slate-400 text-sm mt-1">Availability poll</p>
      </div>

      <div v-if="loading" class="space-y-4">
        <SkeletonLoader height="h-32" />
        <SkeletonLoader height="h-48" />
      </div>
      <BaseAlert v-else-if="error" variant="error" :message="error" />

      <template v-else-if="submitted">
        <BaseCard class="text-center py-8">
          <p class="text-3xl mb-3">✓</p>
          <h2 class="text-lg font-semibold text-slate-900 dark:text-white mb-1">Thanks for responding!</h2>
          <p class="text-sm text-slate-500 dark:text-slate-400">
            Your availability has been recorded for <strong>{{ ctx.group_name }}</strong>.
          </p>
        </BaseCard>
      </template>

      <template v-else>
        <BaseCard class="mb-4">
          <h2 class="font-semibold text-slate-900 dark:text-white">{{ ctx.poll_title }}</h2>
          <p class="text-sm text-slate-500 dark:text-slate-400 mt-0.5">{{ ctx.group_name }} · {{ ctx.series_title }}</p>
        </BaseCard>

        <BaseCard class="mb-4">
          <BaseInput v-model="guestName" label="Your name" placeholder="Enter your name" />
        </BaseCard>

        <div class="space-y-3 mb-6">
          <div v-for="opt in ctx.options" :key="opt.id"
            class="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-4">
            <p class="font-medium text-slate-800 dark:text-slate-100 text-sm">{{ formatDate(opt.proposed_date) }}</p>
            <p class="text-xs text-slate-500 dark:text-slate-400 mb-3">
              {{ formatTime(opt.start_time) }}<span v-if="opt.end_time"> – {{ formatTime(opt.end_time) }}</span>
            </p>
            <div class="flex gap-2">
              <button v-for="choice in ['yes', 'maybe', 'no']" :key="choice"
                @click="setResponse(opt.id, choice)"
                :class="responseButtonClass(opt.id, choice)"
                class="flex-1 text-xs py-1.5 rounded-lg border transition-all font-medium capitalize focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500">
                {{ choice === "yes" ? "✓ Yes" : choice === "no" ? "✗ No" : "~ Maybe" }}
              </button>
            </div>
          </div>
        </div>

        <BaseButton @click="submit" :loading="submitting" :disabled="!guestName.trim() || Object.keys(responses).length === 0" class="w-full">
          Submit availability
        </BaseButton>
        <BaseAlert v-if="submitError" variant="error" :message="submitError" class="mt-3" />
      </template>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import { useRoute } from "vue-router";
import BaseAlert from "../components/ui/BaseAlert.vue";
import BaseButton from "../components/ui/BaseButton.vue";
import BaseCard from "../components/ui/BaseCard.vue";
import BaseInput from "../components/ui/BaseInput.vue";
import SkeletonLoader from "../components/ui/SkeletonLoader.vue";

const route = useRoute();
const token = route.params.token;

const ctx = ref(null);
const loading = ref(true);
const error = ref(null);
const guestName = ref("");
const responses = reactive({});
const submitting = ref(false);
const submitted = ref(false);
const submitError = ref(null);

const apiBase = import.meta.env.VITE_API_BASE_URL || "";

onMounted(async () => {
  try {
    const res = await fetch(`${apiBase}/api/guest/${token}`);
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || "Invalid or expired link");
    }
    const data = await res.json();
    if (data.type !== "poll") throw new Error("This link is not for a poll");
    ctx.value = data;
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
});

function setResponse(optionId, choice) {
  responses[optionId] = choice;
}

async function submit() {
  submitError.value = null;
  if (!guestName.value.trim()) return;
  submitting.value = true;
  try {
    const responseList = Object.entries(responses).map(([option_id, response]) => ({ option_id, response }));
    const res = await fetch(`${apiBase}/api/guest/${token}/poll`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ guest_name: guestName.value.trim(), responses: responseList }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || "Failed to submit responses");
    }
    submitted.value = true;
  } catch (err) {
    submitError.value = err.message;
  } finally {
    submitting.value = false;
  }
}

function formatDate(d) {
  if (!d) return "";
  return new Date(`${d}T00:00:00`).toLocaleDateString(undefined, { weekday: "long", year: "numeric", month: "long", day: "numeric" });
}
function formatTime(t) {
  if (!t) return "";
  const [h, m] = t.split(":");
  return new Date(0, 0, 0, h, m).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}
function responseButtonClass(optionId, choice) {
  const active = responses[optionId] === choice;
  if (active) return { yes: "bg-emerald-600 border-emerald-600 text-white", maybe: "bg-amber-500 border-amber-500 text-white", no: "bg-red-500 border-red-500 text-white" }[choice];
  return "bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-slate-600 hover:border-slate-400 dark:hover:border-slate-400";
}
</script>
