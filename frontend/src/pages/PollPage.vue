<template>
  <div class="max-w-2xl mx-auto px-4 sm:px-6 py-8">
    <nav class="text-sm text-slate-500 dark:text-slate-400 mb-6 flex items-center gap-2">
      <router-link to="/dashboard" class="hover:text-slate-800 dark:hover:text-slate-200">Dashboard</router-link>
      <span v-if="poll">/</span>
      <router-link v-if="poll" :to="`/series/${poll.series_id}`" class="hover:text-slate-800 dark:hover:text-slate-200">Series</router-link>
      <span>/</span>
      <span class="text-slate-800 dark:text-slate-200 font-medium">{{ poll?.title ?? "Poll" }}</span>
    </nav>

    <div v-if="loading" class="space-y-4">
      <SkeletonLoader height="h-8" width="w-56" />
      <SkeletonLoader height="h-4" width="w-40" />
    </div>
    <BaseAlert v-else-if="error" variant="error" :message="error" />

    <template v-else>
      <!-- Poll header -->
      <BaseCard class="mb-4">
        <div class="flex justify-between items-start gap-4">
          <div>
            <h1 class="text-xl font-bold text-slate-900 dark:text-white">{{ poll.title }}</h1>
            <p v-if="poll.description" class="text-sm text-slate-500 dark:text-slate-400 mt-1">{{ poll.description }}</p>
            <p v-if="poll.deadline" class="text-xs text-slate-400 dark:text-slate-500 mt-1">
              Closes {{ formatDatetime(poll.deadline) }}
            </p>
          </div>
          <span :class="statusClass(poll.status)" class="text-xs px-2 py-0.5 rounded-full capitalize flex-shrink-0">
            {{ poll.status }}
          </span>
        </div>

        <!-- Organiser actions -->
        <div v-if="isOrganiser" class="flex gap-2 flex-wrap mt-4 pt-4 border-t border-slate-100 dark:border-slate-700">
          <BaseButton v-if="poll.status === 'open'" @click="copyGuestLink" variant="secondary" size="sm">
            {{ guestLinkCopied ? "Copied!" : "Copy guest link" }}
          </BaseButton>
        </div>
      </BaseCard>

      <!-- Options -->
      <div class="space-y-3 mb-6">
        <div v-for="opt in poll.options" :key="opt.id"
          class="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl p-4">
          <div class="flex justify-between items-start gap-3">
            <div>
              <p class="font-medium text-slate-800 dark:text-slate-100">{{ formatDate(opt.proposed_date) }}</p>
              <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                {{ formatTime(opt.start_time) }}<span v-if="opt.end_time"> – {{ formatTime(opt.end_time) }}</span>
              </p>
            </div>
            <div class="flex items-center gap-1 flex-shrink-0">
              <span v-for="choice in ['yes', 'maybe', 'no']" :key="choice"
                :class="choiceCountClass(choice)"
                class="text-xs font-semibold px-1.5 py-0.5 rounded-full">
                {{ opt.response_counts[choice] ?? 0 }} {{ choice }}
              </span>
            </div>
          </div>

          <!-- My response buttons (open polls only) -->
          <div v-if="poll.status === 'open'" class="flex gap-2 mt-3">
            <button v-for="choice in ['yes', 'maybe', 'no']" :key="choice"
              @click="respond(opt.id, choice)"
              :disabled="submitting"
              :class="responseButtonClass(opt.id, choice)"
              class="flex-1 text-xs py-1.5 rounded-lg border transition-all disabled:opacity-50 font-medium capitalize focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500">
              {{ choice === "yes" ? "✓ Yes" : choice === "no" ? "✗ No" : "~ Maybe" }}
            </button>
          </div>

          <!-- Resolved badge -->
          <div v-if="poll.chosen_option_id === opt.id" class="mt-2 text-xs font-semibold text-emerald-600 dark:text-emerald-400">
            ✓ Selected date
          </div>
        </div>
      </div>

      <!-- Resolve (organiser, open poll) -->
      <BaseCard v-if="isOrganiser && poll.status === 'open'">
        <h2 class="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">Resolve poll</h2>
        <p class="text-xs text-slate-500 dark:text-slate-400 mb-3">
          Choose a date to create a confirmed occurrence and notify all members.
        </p>
        <div class="space-y-2">
          <label v-for="opt in poll.options" :key="opt.id" class="flex items-center gap-3 cursor-pointer">
            <input type="radio" v-model="resolveOptionId" :value="opt.id"
              class="text-primary-600 focus:ring-primary-500" />
            <span class="text-sm text-slate-700 dark:text-slate-200">
              {{ formatDate(opt.proposed_date) }} — {{ formatTime(opt.start_time) }}
            </span>
          </label>
        </div>
        <BaseButton @click="resolve" :loading="resolving" :disabled="!resolveOptionId" class="mt-4">
          Confirm date
        </BaseButton>
        <BaseAlert v-if="resolveError" variant="error" :message="resolveError" class="mt-3" />
      </BaseCard>
    </template>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import BaseAlert from "../components/ui/BaseAlert.vue";
import BaseButton from "../components/ui/BaseButton.vue";
import BaseCard from "../components/ui/BaseCard.vue";
import SkeletonLoader from "../components/ui/SkeletonLoader.vue";
import { request } from "../services/api.js";

const route = useRoute();
const pollId = route.params.id;

const poll = ref(null);
const loading = ref(true);
const error = ref(null);
const isOrganiser = ref(false);
const submitting = ref(false);
const resolveOptionId = ref(null);
const resolving = ref(false);
const resolveError = ref(null);
const guestLinkCopied = ref(false);

onMounted(async () => {
  try {
    const res = await request(`/api/polls/${pollId}`);
    if (!res.ok) throw new Error("Failed to load poll");
    poll.value = await res.json();

    const sRes = await request(`/api/series/${poll.value.series_id}`);
    if (sRes.ok) {
      const s = await sRes.json();
      const gRes = await request(`/api/groups/${s.group_id}`);
      if (gRes.ok) {
        const g = await gRes.json();
        isOrganiser.value = g.my_role === "organiser" || g.my_role === "owner";
      }
    }
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
});

async function respond(optionId, choice) {
  submitting.value = true;
  try {
    const res = await request(`/api/polls/${pollId}/respond`, {
      method: "POST",
      body: JSON.stringify({ responses: [{ option_id: optionId, response: choice }] }),
    });
    if (!res.ok) throw new Error("Failed to submit response");
    const updated = await res.json();
    poll.value = updated;
  } finally {
    submitting.value = false;
  }
}

async function resolve() {
  resolveError.value = null;
  if (!resolveOptionId.value) return;
  resolving.value = true;
  try {
    const res = await request(`/api/polls/${pollId}/resolve`, {
      method: "POST",
      body: JSON.stringify({ chosen_option_id: resolveOptionId.value }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || "Failed to resolve poll");
    }
    const updated = await res.json();
    poll.value = updated;
  } catch (err) {
    resolveError.value = err.message;
  } finally {
    resolving.value = false;
  }
}

async function copyGuestLink() {
  try {
    const res = await request(`/api/polls/${pollId}/guest-link`, { method: "POST" });
    if (!res.ok) throw new Error("Failed to generate link");
    const data = await res.json();
    await navigator.clipboard.writeText(window.location.origin + data.url);
    guestLinkCopied.value = true;
    setTimeout(() => { guestLinkCopied.value = false; }, 3000);
  } catch {
    // fallback: ignore clipboard error
  }
}

function formatDate(d) {
  return new Date(`${d}T00:00:00`).toLocaleDateString(undefined, { weekday: "long", year: "numeric", month: "long", day: "numeric" });
}
function formatTime(t) {
  if (!t) return "";
  const [h, m] = t.split(":");
  return new Date(0, 0, 0, h, m).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}
function formatDatetime(dt) {
  return new Date(dt).toLocaleString(undefined, { weekday: "short", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}
function statusClass(s) {
  return { open: "bg-primary-100 text-primary-700 dark:bg-primary-950 dark:text-primary-300", closed: "bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400", resolved: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300" }[s] ?? "bg-slate-100 text-slate-500";
}
function choiceCountClass(choice) {
  return { yes: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300", maybe: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300", no: "bg-red-100 text-red-600 dark:bg-red-950 dark:text-red-400" }[choice] ?? "bg-slate-100 text-slate-500";
}
function responseButtonClass(optionId, choice) {
  const myResponse = poll.value?.my_responses?.[optionId];
  const active = myResponse === choice;
  if (active) return { yes: "bg-emerald-600 border-emerald-600 text-white", maybe: "bg-amber-500 border-amber-500 text-white", no: "bg-red-500 border-red-500 text-white" }[choice];
  return "bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 border-slate-200 dark:border-slate-600 hover:border-slate-400 dark:hover:border-slate-400";
}
</script>
