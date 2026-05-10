<template>
  <div class="min-h-screen bg-slate-50 dark:bg-slate-900 flex items-start justify-center pt-16 px-4">
    <div class="w-full max-w-md">
      <div class="text-center mb-8">
        <h1 class="text-2xl font-bold text-slate-900 dark:text-white">Game On Tabletop</h1>
        <p class="text-slate-500 dark:text-slate-400 text-sm mt-1">Guest RSVP</p>
      </div>

      <div v-if="loading" class="space-y-4">
        <SkeletonLoader height="h-32" />
        <SkeletonLoader height="h-24" />
      </div>
      <BaseAlert v-else-if="error" variant="error" :message="error" />

      <template v-else-if="submitted">
        <BaseCard class="text-center py-8">
          <p class="text-3xl mb-3">{{ submittedChoice === 'yes' ? '✓' : submittedChoice === 'maybe' ? '~' : '✗' }}</p>
          <h2 class="text-lg font-semibold text-slate-900 dark:text-white mb-1">
            {{ submittedChoice === 'yes' ? "You're in!" : submittedChoice === 'maybe' ? "Maybe see you there!" : "Thanks for letting us know." }}
          </h2>
          <p class="text-sm text-slate-500 dark:text-slate-400">
            RSVP recorded for <strong>{{ ctx.group_name }}</strong> on {{ formatDate(ctx.occurrence_date) }}.
          </p>
        </BaseCard>
      </template>

      <template v-else>
        <BaseCard class="mb-4">
          <h2 class="font-semibold text-slate-900 dark:text-white mb-1">{{ ctx.group_name }}</h2>
          <p class="text-sm text-slate-500 dark:text-slate-400">{{ ctx.series_title }}</p>
          <div class="mt-3 pt-3 border-t border-slate-100 dark:border-slate-700">
            <p class="text-base font-medium text-slate-800 dark:text-slate-100">{{ formatDate(ctx.occurrence_date) }}</p>
            <p class="text-sm text-slate-500 dark:text-slate-400">{{ formatTime(ctx.occurrence_start_time) }}</p>
          </div>
        </BaseCard>

        <BaseCard>
          <h2 class="font-semibold text-slate-700 dark:text-slate-300 mb-4">Are you coming?</h2>

          <BaseInput v-model="guestName" label="Your name" placeholder="Enter your name" class="mb-4" />

          <div class="flex gap-3 mb-4">
            <button v-for="choice in ['yes', 'maybe', 'no']" :key="choice"
              @click="submitRsvp(choice)"
              :disabled="!guestName.trim() || submitting"
              :class="activeChoice === choice ? activeButtonClass(choice) : inactiveButtonClass"
              class="flex-1 rounded-xl py-2.5 text-sm font-semibold border-2 transition-all disabled:opacity-40 capitalize focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-primary-500">
              {{ choice === "yes" ? "✓ Yes" : choice === "no" ? "✗ No" : "~ Maybe" }}
            </button>
          </div>

          <BaseAlert v-if="submitError" variant="error" :message="submitError" />
        </BaseCard>
      </template>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import BaseAlert from "../components/ui/BaseAlert.vue";
import BaseCard from "../components/ui/BaseCard.vue";
import BaseInput from "../components/ui/BaseInput.vue";
import SkeletonLoader from "../components/ui/SkeletonLoader.vue";

const route = useRoute();
const token = route.params.token;

const ctx = ref(null);
const loading = ref(true);
const error = ref(null);
const guestName = ref("");
const submitting = ref(false);
const submitted = ref(false);
const submittedChoice = ref(null);
const submitError = ref(null);
const activeChoice = ref(null);

const apiBase = import.meta.env.VITE_API_BASE_URL || "";

onMounted(async () => {
  try {
    const res = await fetch(`${apiBase}/api/guest/${token}`);
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || "Invalid or expired link");
    }
    const data = await res.json();
    if (data.type !== "rsvp") throw new Error("This link is not for an RSVP");
    ctx.value = data;
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
});

async function submitRsvp(choice) {
  submitError.value = null;
  if (!guestName.value.trim()) return;
  submitting.value = true;
  activeChoice.value = choice;
  try {
    const res = await fetch(`${apiBase}/api/guest/${token}/rsvp`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ guest_name: guestName.value.trim(), response: choice }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || "Failed to submit RSVP");
    }
    submittedChoice.value = choice;
    submitted.value = true;
  } catch (err) {
    submitError.value = err.message;
    activeChoice.value = null;
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
function activeButtonClass(choice) {
  return { yes: "bg-emerald-600 border-emerald-600 text-white", maybe: "bg-amber-500 border-amber-500 text-white", no: "bg-red-500 border-red-500 text-white" }[choice];
}
const inactiveButtonClass = "bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-slate-600 hover:border-slate-400 dark:hover:border-slate-400";
</script>
