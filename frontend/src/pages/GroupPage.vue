<template>
  <div class="max-w-3xl mx-auto px-4 sm:px-6 py-8">
    <!-- Breadcrumb -->
    <nav class="text-sm text-slate-500 dark:text-slate-400 mb-6 flex items-center gap-2">
      <router-link to="/dashboard" class="hover:text-slate-800 dark:hover:text-slate-200">Dashboard</router-link>
      <span>/</span>
      <span class="text-slate-800 dark:text-slate-200 font-medium">{{ group?.name ?? "Group" }}</span>
    </nav>

    <div v-if="loading" class="space-y-4">
      <SkeletonLoader height="h-8" width="w-64" />
      <SkeletonLoader height="h-4" width="w-48" />
    </div>
    <BaseAlert v-else-if="error" variant="error" :message="error" />

    <template v-else>
      <!-- Header -->
      <div class="flex justify-between items-start mb-8 gap-4">
        <div>
          <h1 class="text-2xl font-bold text-slate-900 dark:text-white">{{ group.name }}</h1>
          <p v-if="group.description" class="text-slate-500 dark:text-slate-400 mt-1 text-sm">{{ group.description }}</p>
          <p class="text-xs text-slate-400 dark:text-slate-500 mt-1">
            {{ group.member_count }} {{ group.member_count === 1 ? "member" : "members" }} · {{ group.my_role }}
          </p>
        </div>
        <BaseButton v-if="isOrganiser" @click="showInviteModal = true" variant="secondary" size="sm">
          <LinkIcon class="w-4 h-4 mr-1.5" />Invite
        </BaseButton>
      </div>

      <!-- Invite modal -->
      <Teleport to="body">
        <Transition enter-active-class="transition-opacity duration-150" enter-from-class="opacity-0" enter-to-class="opacity-100" leave-active-class="transition-opacity duration-100" leave-from-class="opacity-100" leave-to-class="opacity-0">
          <div v-if="showInviteModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
            <div class="bg-white dark:bg-slate-800 rounded-2xl shadow-xl p-6 max-w-sm w-full border border-slate-200 dark:border-slate-700">
              <h3 class="font-semibold text-slate-900 dark:text-white mb-4">Invite link</h3>
              <div v-if="inviteLink" class="space-y-3">
                <p class="text-sm text-slate-600 dark:text-slate-300 break-all font-mono bg-slate-50 dark:bg-slate-900 p-3 rounded-xl border border-slate-200 dark:border-slate-700">{{ inviteLink }}</p>
                <BaseButton @click="copyInviteLink" variant="secondary" block>
                  {{ copied ? "Copied!" : "Copy link" }}
                </BaseButton>
              </div>
              <BaseButton v-else @click="createInvite" :loading="creatingInvite" block>
                Generate invite link
              </BaseButton>
              <BaseButton @click="closeInviteModal" variant="ghost" block class="mt-2">Close</BaseButton>
            </div>
          </div>
        </Transition>
      </Teleport>

      <!-- Game Nights -->
      <section class="mb-8">
        <div class="flex justify-between items-center mb-3">
          <h2 class="font-semibold text-slate-700 dark:text-slate-300">Game Nights</h2>
          <BaseButton v-if="isOrganiser" :to="`/groups/${groupId}/series/new`" variant="ghost" size="sm">+ New game night</BaseButton>
        </div>

        <div v-if="series.length === 0" class="text-sm text-slate-400 dark:text-slate-500 text-center py-8 bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700">
          No game nights yet.
          <router-link v-if="isOrganiser" :to="`/groups/${groupId}/series/new`" class="text-primary-600 hover:underline ml-1">Create one</router-link>
        </div>
        <div v-else class="space-y-3">
          <router-link v-for="s in series" :key="s.id" :to="`/series/${s.id}`"
            class="flex justify-between items-center bg-white dark:bg-slate-800 rounded-2xl p-4 border border-slate-200 dark:border-slate-700 shadow-card hover:shadow-card-hover transition-all group">
            <div>
              <span class="font-medium text-slate-800 dark:text-slate-100 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">{{ s.title }}</span>
              <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{{ recurrenceLabel(s) }}</p>
            </div>
            <span :class="statusClass(s.status)" class="text-xs px-2 py-0.5 rounded-full capitalize">
              {{ s.status.replace("_", " ") }}
            </span>
          </router-link>
        </div>
      </section>

      <!-- Public toggle (organisers only) -->
      <section v-if="isOrganiser" class="mb-8">
        <div class="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-4">
          <div class="flex items-start justify-between gap-4">
            <div>
              <p class="text-sm font-medium text-slate-800 dark:text-slate-200">Open to the public</p>
              <p class="text-xs text-slate-400 dark:text-slate-500 mt-0.5">Upcoming nights will be listed on the public explore page</p>
            </div>
            <button
              type="button"
              role="switch"
              :aria-checked="group.is_public"
              @click="togglePublic"
              :disabled="savingPublic"
              :class="group.is_public ? 'bg-primary-600' : 'bg-slate-300 dark:bg-slate-600'"
              class="relative inline-flex h-6 w-11 flex-shrink-0 rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 disabled:opacity-50"
            >
              <span
                :class="group.is_public ? 'translate-x-5' : 'translate-x-0'"
                class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out"
              />
            </button>
          </div>
        </div>
      </section>

      <!-- Members -->
      <section>
        <h2 class="font-semibold text-slate-700 dark:text-slate-300 mb-3">Members</h2>
        <BaseCard padding="none" flush>
          <div v-for="(m, i) in members" :key="m.user_id"
            :class="i > 0 ? 'border-t border-slate-100 dark:border-slate-700' : ''"
            class="flex justify-between items-center px-4 py-3">
            <div class="flex items-center gap-3">
              <BaseAvatar :name="m.display_name || m.username" size="sm" />
              <div>
                <span class="text-sm font-medium text-slate-800 dark:text-slate-100">{{ m.display_name || m.username }}</span>
                <span v-if="m.display_name" class="text-xs text-slate-400 dark:text-slate-500 ml-1">@{{ m.username }}</span>
              </div>
            </div>
            <span class="text-xs text-slate-500 dark:text-slate-400 capitalize">{{ m.role }}</span>
          </div>
        </BaseCard>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { LinkIcon } from "@heroicons/vue/24/outline";
import { useRoute } from "vue-router";
import BaseAlert from "../components/ui/BaseAlert.vue";
import BaseAvatar from "../components/ui/BaseAvatar.vue";
import BaseButton from "../components/ui/BaseButton.vue";
import BaseCard from "../components/ui/BaseCard.vue";
import SkeletonLoader from "../components/ui/SkeletonLoader.vue";
import { useToast } from "../composables/useToast.js";
import { request } from "../services/api.js";

const { success: toastSuccess, error: toastError } = useToast();

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
const savingPublic = ref(false);

const isOrganiser = computed(() => group.value?.my_role === "organiser" || group.value?.my_role === "owner");

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

function closeInviteModal() {
  showInviteModal.value = false;
  inviteLink.value = null;
  copied.value = false;
}

async function togglePublic() {
  savingPublic.value = true;
  const newValue = !group.value.is_public;
  try {
    const res = await request(`/api/groups/${groupId}`, {
      method: "PATCH",
      body: JSON.stringify({ is_public: newValue }),
    });
    if (!res.ok) throw new Error("Failed to update group");
    group.value = await res.json();
    toastSuccess(newValue ? "Group is now public" : "Group is now private");
  } catch (err) {
    toastError(err.message);
  } finally {
    savingPublic.value = false;
  }
}

function statusClass(status) {
  return {
    active: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
    on_hold: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
    cancelled: "bg-red-100 text-red-600 dark:bg-red-950 dark:text-red-400",
    completed: "bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400",
  }[status] ?? "bg-slate-100 text-slate-500";
}

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
function recurrenceLabel(s) {
  const day = s.default_day_of_week != null ? DAYS[s.default_day_of_week] : "";
  return { once: "One-time event", weekly: `Every ${day}`, biweekly: `Every other ${day}`, monthly: "Monthly", custom: "Custom schedule" }[s.recurrence] ?? s.recurrence;
}
</script>
