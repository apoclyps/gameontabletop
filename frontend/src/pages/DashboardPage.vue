<template>
  <div class="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-8">

    <!-- Welcome -->
    <div>
      <h1 class="text-2xl font-bold text-slate-900 dark:text-white">
        Welcome back{{ user?.display_name ? ', ' + user.display_name : '' }}!
      </h1>
      <p class="text-slate-500 dark:text-slate-400 text-sm mt-1">Here's what's coming up.</p>
    </div>

    <!-- Stats row -->
    <div class="grid grid-cols-3 gap-4">
      <div class="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-4 text-center">
        <p class="text-2xl font-bold text-slate-900 dark:text-white">{{ groups.length }}</p>
        <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">{{ groups.length === 1 ? 'Group' : 'Groups' }}</p>
      </div>
      <div class="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-4 text-center">
        <p class="text-2xl font-bold text-slate-900 dark:text-white">{{ upcomingCount }}</p>
        <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">Upcoming nights</p>
      </div>
      <div class="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-4 text-center" title="Coming soon">
        <p class="text-2xl font-bold text-slate-300 dark:text-slate-600">—</p>
        <p class="text-xs text-slate-400 dark:text-slate-600 mt-1">Nights played</p>
      </div>
    </div>

    <!-- Next up -->
    <section>
      <div class="flex items-center justify-between mb-3">
        <h2 class="font-semibold text-slate-700 dark:text-slate-300">Next up</h2>
        <router-link
          v-if="upcomingCount > 3"
          to="/game-nights"
          class="text-sm text-primary-600 dark:text-primary-400 hover:underline font-medium"
        >
          See all {{ upcomingCount }} →
        </router-link>
      </div>

      <div v-if="loadingNights" class="space-y-3">
        <SkeletonLoader v-for="i in 3" :key="i" height="h-20" rounded="rounded-2xl" />
      </div>

      <div v-else-if="nextNights.length === 0" class="text-center py-10 bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700">
        <CalendarDaysIcon class="w-8 h-8 text-slate-300 dark:text-slate-600 mx-auto mb-2" />
        <p class="text-sm text-slate-400 dark:text-slate-500">No upcoming game nights.</p>
        <p class="text-xs text-slate-400 dark:text-slate-500 mt-1">
          <router-link to="/groups/new" class="text-primary-600 dark:text-primary-400 hover:underline">Create a group</router-link>
          to get started.
        </p>
      </div>

      <div v-else class="space-y-3">
        <router-link
          v-for="night in nextNights"
          :key="night.id"
          :to="`/occurrences/${night.id}`"
          class="flex items-center justify-between bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-card hover:shadow-card-hover transition-all p-4 group"
        >
          <div class="flex items-center gap-4 min-w-0">
            <div class="w-12 text-center flex-shrink-0">
              <p class="text-xs font-medium text-slate-400 dark:text-slate-500 uppercase">{{ monthAbbr(night.occurrence_date) }}</p>
              <p class="text-xl font-bold text-slate-900 dark:text-white leading-none">{{ dayNum(night.occurrence_date) }}</p>
            </div>
            <div class="min-w-0">
              <p class="font-medium text-slate-800 dark:text-slate-100 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors truncate">
                {{ night.series_title }}
              </p>
              <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5 truncate">
                {{ night.group_name }} · {{ formatTime(night.start_time) }}
              </p>
            </div>
          </div>
          <RsvpBadge :rsvp="night.my_rsvp" class="flex-shrink-0 ml-3" />
        </router-link>

        <router-link
          v-if="upcomingCount > 3"
          to="/game-nights"
          class="flex items-center justify-center gap-2 text-sm text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 font-medium py-3 bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 hover:shadow-card transition-all"
        >
          View all game nights <ArrowRightIcon class="w-4 h-4" />
        </router-link>
      </div>
    </section>

    <!-- My groups -->
    <section>
      <div class="flex items-center justify-between mb-3">
        <h2 class="font-semibold text-slate-700 dark:text-slate-300">My groups</h2>
        <router-link to="/groups/new" class="text-sm text-primary-600 dark:text-primary-400 hover:underline font-medium">+ New group</router-link>
      </div>

      <div v-if="loadingGroups" class="grid gap-3 sm:grid-cols-2">
        <SkeletonLoader v-for="i in 2" :key="i" height="h-16" rounded="rounded-2xl" />
      </div>

      <div v-else-if="groups.length === 0" class="text-center py-10 bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700">
        <UserGroupIcon class="w-8 h-8 text-slate-300 dark:text-slate-600 mx-auto mb-2" />
        <p class="text-sm text-slate-400 dark:text-slate-500 mb-3">No groups yet.</p>
        <router-link to="/groups/new" class="text-sm text-primary-600 dark:text-primary-400 hover:underline">Create your first group</router-link>
      </div>

      <div v-else class="grid gap-3 sm:grid-cols-2">
        <router-link
          v-for="group in groups"
          :key="group.id"
          :to="`/groups/${group.id}`"
          class="flex items-center justify-between bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-card hover:shadow-card-hover transition-all px-4 py-3 group"
        >
          <div class="min-w-0">
            <p class="font-medium text-sm text-slate-800 dark:text-slate-100 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors truncate">
              {{ group.name }}
            </p>
            <p class="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
              {{ group.member_count }} {{ group.member_count === 1 ? 'member' : 'members' }}
            </p>
          </div>
          <span :class="roleClasses(group.my_role)" class="text-xs px-2 py-0.5 rounded-full capitalize flex-shrink-0 ml-3">
            {{ group.my_role }}
          </span>
        </router-link>
      </div>
    </section>

  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { ArrowRightIcon, CalendarDaysIcon, UserGroupIcon } from "@heroicons/vue/24/outline";
import SkeletonLoader from "../components/ui/SkeletonLoader.vue";
import { useCurrentUser } from "../composables/useCurrentUser.js";
import { request } from "../services/api.js";

const { user } = useCurrentUser();

const groups = ref([]);
const nights = ref([]);
const loadingGroups = ref(true);
const loadingNights = ref(true);

const nextNights = computed(() => nights.value.slice(0, 3));
const upcomingCount = computed(() => nights.value.length);

onMounted(async () => {
  const [gRes, nRes] = await Promise.all([
    request("/api/groups"),
    request("/api/me/occurrences"),
  ]);
  if (gRes.ok) groups.value = await gRes.json();
  loadingGroups.value = false;
  if (nRes.ok) nights.value = await nRes.json();
  loadingNights.value = false;
});

function roleClasses(role) {
  return {
    organiser: "bg-primary-100 text-primary-700 dark:bg-primary-950 dark:text-primary-300",
    owner: "bg-primary-100 text-primary-700 dark:bg-primary-950 dark:text-primary-300",
    member: "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300",
  }[role] ?? "bg-slate-100 text-slate-600";
}

function monthAbbr(iso) {
  return new Date(iso + "T00:00:00").toLocaleDateString(undefined, { month: "short" }).toUpperCase();
}
function dayNum(iso) {
  return new Date(iso + "T00:00:00").getDate();
}
function formatTime(t) {
  if (!t) return "";
  const [h, m] = t.split(":");
  return new Date(0, 0, 0, +h, +m).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

const RsvpBadge = {
  props: { rsvp: { type: String, default: null } },
  template: `
    <span v-if="rsvp" :class="{
      'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300': rsvp === 'yes',
      'bg-red-100 text-red-600 dark:bg-red-950 dark:text-red-400': rsvp === 'no',
      'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300': rsvp === 'maybe',
    }" class="text-xs px-2 py-0.5 rounded-full capitalize font-medium">{{ rsvp }}</span>
    <span v-else class="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-400 dark:bg-slate-700 dark:text-slate-500">No RSVP</span>
  `,
};
</script>
