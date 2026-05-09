<template>
  <div class="min-h-screen bg-gray-50">
    <nav class="bg-white shadow-sm px-6 py-3 flex gap-3 items-center text-sm text-gray-500">
      <router-link to="/dashboard" class="hover:text-gray-800">Dashboard</router-link>
      <span>/</span>
      <span class="text-gray-800 font-medium">{{ group?.name ?? "Group" }}</span>
    </nav>

    <main class="max-w-3xl mx-auto px-4 py-8">
      <div v-if="loading" class="text-gray-400 animate-pulse text-center py-12">Loading…</div>
      <div v-else-if="error" class="text-red-500 text-sm text-center py-12">{{ error }}</div>
      <template v-else>
        <!-- Header -->
        <div class="flex justify-between items-start mb-8">
          <div>
            <h1 class="text-2xl font-bold text-gray-800">{{ group.name }}</h1>
            <p v-if="group.description" class="text-gray-500 mt-1 text-sm">{{ group.description }}</p>
            <p class="text-xs text-gray-400 mt-1">
              {{ group.member_count }} {{ group.member_count === 1 ? 'member' : 'members' }} · {{ group.my_role }}
            </p>
          </div>
          <div v-if="isOrganiser" class="flex gap-2">
            <button @click="showInviteModal = true"
              class="text-sm border border-gray-300 rounded-lg px-3 py-1.5 hover:bg-gray-50">
              Invite
            </button>
          </div>
        </div>

        <!-- Invite modal -->
        <div v-if="showInviteModal" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div class="bg-white rounded-xl shadow-xl p-6 max-w-sm w-full mx-4">
            <h3 class="font-semibold text-gray-800 mb-4">Invite link</h3>
            <div v-if="inviteLink" class="space-y-3">
              <p class="text-sm text-gray-600 break-all font-mono bg-gray-50 p-2 rounded">{{ inviteLink }}</p>
              <button @click="copyInviteLink"
                class="w-full text-sm border rounded-lg px-3 py-2 hover:bg-gray-50">
                {{ copied ? "Copied!" : "Copy link" }}
              </button>
            </div>
            <button v-else @click="createInvite" :disabled="creatingInvite"
              class="w-full bg-blue-600 text-white rounded-lg py-2 text-sm hover:bg-blue-700 disabled:opacity-50">
              {{ creatingInvite ? "Generating…" : "Generate invite link" }}
            </button>
            <button @click="showInviteModal = false; inviteLink = null; copied = false"
              class="mt-3 w-full text-sm text-gray-500 hover:text-gray-700">Close</button>
          </div>
        </div>

        <!-- Series -->
        <section class="mb-8">
          <div class="flex justify-between items-center mb-3">
            <h2 class="font-semibold text-gray-700">Series</h2>
            <router-link v-if="isOrganiser" :to="`/groups/${groupId}/series/new`"
              class="text-sm text-blue-600 hover:underline">+ New series</router-link>
          </div>
          <div v-if="series.length === 0" class="text-sm text-gray-400 text-center py-6 bg-white rounded-xl border">
            No series yet.
            <span v-if="isOrganiser">
              <router-link :to="`/groups/${groupId}/series/new`" class="text-blue-600 hover:underline ml-1">Create one</router-link>
            </span>
          </div>
          <div v-else class="space-y-3">
            <router-link
              v-for="s in series"
              :key="s.id"
              :to="`/series/${s.id}`"
              class="block bg-white rounded-xl p-4 border border-gray-100 hover:shadow-sm transition-shadow"
            >
              <div class="flex justify-between items-center">
                <span class="font-medium text-gray-800">{{ s.title }}</span>
                <span :class="statusClass(s.status)" class="text-xs px-2 py-0.5 rounded-full capitalize">
                  {{ s.status.replace('_', ' ') }}
                </span>
              </div>
              <p class="text-xs text-gray-500 mt-1">{{ recurrenceLabel(s) }}</p>
            </router-link>
          </div>
        </section>

        <!-- Members -->
        <section class="mb-8">
          <h2 class="font-semibold text-gray-700 mb-3">Members</h2>
          <div class="bg-white rounded-xl border divide-y">
            <div v-for="m in members" :key="m.user_id" class="flex justify-between items-center px-4 py-3">
              <div>
                <span class="text-sm font-medium text-gray-800">{{ m.display_name || m.username }}</span>
                <span v-if="m.display_name" class="text-xs text-gray-400 ml-1">@{{ m.username }}</span>
              </div>
              <span class="text-xs text-gray-500 capitalize">{{ m.role }}</span>
            </div>
          </div>
        </section>
      </template>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { request } from "../services/api.js";

const route = useRoute();
const groupId = route.params.id;

const group = ref(null);
const series = ref([]);
const members = ref([]);
const loading = ref(true);
const error = ref(null);
const showInviteModal = ref(false);
const inviteLink = ref(null);
const creatingInvite = ref(false);
const copied = ref(false);

const isOrganiser = computed(() => group.value?.my_role === "organiser");

onMounted(async () => {
  try {
    const [gRes, sRes, mRes] = await Promise.all([
      request(`/api/groups/${groupId}`),
      request(`/api/groups/${groupId}/series`),
      request(`/api/groups/${groupId}/members`),
    ]);
    if (!gRes.ok) throw new Error("Failed to load group");
    group.value = await gRes.json();
    series.value = sRes.ok ? await sRes.json() : [];
    members.value = mRes.ok ? await mRes.json() : [];
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
});

async function createInvite() {
  creatingInvite.value = true;
  try {
    const res = await request(`/api/groups/${groupId}/invites`, {
      method: "POST",
      body: JSON.stringify({ expires_in_days: 7 }),
    });
    if (!res.ok) throw new Error("Failed to create invite");
    const invite = await res.json();
    inviteLink.value = `${window.location.origin}/invites/${invite.token}`;
  } finally {
    creatingInvite.value = false;
  }
}

async function copyInviteLink() {
  await navigator.clipboard.writeText(inviteLink.value);
  copied.value = true;
  setTimeout(() => (copied.value = false), 2000);
}

function statusClass(status) {
  return {
    active: "bg-green-100 text-green-700",
    on_hold: "bg-yellow-100 text-yellow-700",
    cancelled: "bg-red-100 text-red-600",
    completed: "bg-gray-100 text-gray-500",
  }[status] ?? "bg-gray-100 text-gray-500";
}

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
function recurrenceLabel(s) {
  const day = s.default_day_of_week != null ? DAYS[s.default_day_of_week] : "";
  const labels = {
    once: "One-time event",
    weekly: `Every ${day}`,
    biweekly: `Every other ${day}`,
    monthly: `Monthly`,
    custom: "Custom schedule",
  };
  return labels[s.recurrence] ?? s.recurrence;
}
</script>
