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
            <span v-if="group.seat_size"> · {{ group.seat_size }} seat{{ group.seat_size === 1 ? "" : "s" }}</span>
          </p>
        </div>
        <div class="flex gap-2">
          <BaseButton v-if="isOrganiser" @click="showInviteModal = true" variant="secondary" size="sm">
            <LinkIcon class="w-4 h-4 mr-1.5" />Invite
          </BaseButton>
          <BaseButton v-if="isOwner" @click="openDeleteModal" variant="danger" size="sm">
            Delete
          </BaseButton>
        </div>
      </div>

      <!-- Delete confirmation modal -->
      <Teleport to="body">
        <Transition enter-active-class="transition-opacity duration-150" enter-from-class="opacity-0" enter-to-class="opacity-100" leave-active-class="transition-opacity duration-100" leave-from-class="opacity-100" leave-to-class="opacity-0">
          <div v-if="showDeleteModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
            <div class="bg-white dark:bg-slate-800 rounded-2xl shadow-xl p-6 max-w-sm w-full border border-slate-200 dark:border-slate-700">
              <h3 class="font-semibold text-slate-900 dark:text-white mb-2">Delete group?</h3>
              <p class="text-sm text-slate-500 dark:text-slate-400 mb-4">
                <strong class="text-slate-700 dark:text-slate-200">{{ group.name }}</strong> and all its game nights will be permanently deleted. This cannot be undone.
              </p>
              <p class="text-xs text-slate-500 dark:text-slate-400 mb-2">Type <strong class="text-slate-700 dark:text-slate-200">{{ group.name }}</strong> to confirm:</p>
              <input
                v-model="deleteConfirmText"
                type="text"
                :placeholder="group.name"
                class="w-full rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-3 py-2 text-sm text-slate-800 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-red-500 mb-4"
              />
              <div class="flex gap-3">
                <BaseButton @click="deleteGroup" variant="danger" :loading="deleting" :disabled="deleteConfirmText !== group.name" class="flex-1">Delete</BaseButton>
                <BaseButton @click="showDeleteModal = false" variant="secondary" class="flex-1">Cancel</BaseButton>
              </div>
            </div>
          </div>
        </Transition>
      </Teleport>

      <!-- Invite modal -->
      <Teleport to="body">
        <Transition enter-active-class="transition-opacity duration-150" enter-from-class="opacity-0" enter-to-class="opacity-100" leave-active-class="transition-opacity duration-100" leave-from-class="opacity-100" leave-to-class="opacity-0">
          <div v-if="showInviteModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
            <div class="bg-white dark:bg-slate-800 rounded-2xl shadow-xl p-6 max-w-sm w-full border border-slate-200 dark:border-slate-700">
              <h3 class="font-semibold text-slate-900 dark:text-white mb-4">Invite members</h3>

              <!-- Tabs -->
              <div class="flex gap-1 bg-slate-100 dark:bg-slate-900 rounded-xl p-1 mb-4">
                <button
                  @click="inviteTab = 'link'"
                  :class="inviteTab === 'link' ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm' : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'"
                  class="flex-1 text-sm font-medium px-3 py-1.5 rounded-lg transition-colors"
                >Link</button>
                <button
                  @click="inviteTab = 'email'"
                  :class="inviteTab === 'email' ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm' : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'"
                  class="flex-1 text-sm font-medium px-3 py-1.5 rounded-lg transition-colors"
                >Email</button>
              </div>

              <!-- Link tab -->
              <div v-if="inviteTab === 'link'">
                <div v-if="inviteLink" class="space-y-3">
                  <p class="text-sm text-slate-600 dark:text-slate-300 break-all font-mono bg-slate-50 dark:bg-slate-900 p-3 rounded-xl border border-slate-200 dark:border-slate-700">{{ inviteLink }}</p>
                  <BaseButton @click="copyInviteLink" variant="secondary" block>
                    {{ copied ? "Copied!" : "Copy link" }}
                  </BaseButton>
                </div>
                <BaseButton v-else @click="createInvite" :loading="creatingInvite" block>
                  Generate invite link
                </BaseButton>
              </div>

              <!-- Email tab -->
              <div v-else class="space-y-3">
                <div v-if="emailInviteSent" class="text-sm text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950 rounded-xl p-3 border border-emerald-200 dark:border-emerald-800">
                  Invite sent to {{ inviteEmail }}
                </div>
                <template v-else>
                  <input
                    v-model="inviteEmail"
                    type="email"
                    placeholder="friend@example.com"
                    class="w-full rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-3 py-2 text-sm text-slate-800 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                  <BaseButton @click="sendEmailInvite" :loading="sendingEmailInvite" :disabled="!inviteEmail" block>
                    Send invite
                  </BaseButton>
                </template>
              </div>

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

      <!-- Settings (organisers only) -->
      <section v-if="isOrganiser" class="mb-8">
        <h2 class="font-semibold text-slate-700 dark:text-slate-300 mb-3">Settings</h2>
        <div class="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-4 space-y-4">

          <!-- Public toggle -->
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

          <div class="border-t border-slate-100 dark:border-slate-700" />

          <!-- Edit form -->
          <form @submit.prevent="saveSettings" class="space-y-3">
            <div>
              <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Group name</label>
              <input
                v-model="settingsForm.name"
                type="text"
                maxlength="100"
                required
                class="w-full rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-3 py-2 text-sm text-slate-800 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <div>
              <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Description</label>
              <textarea
                v-model="settingsForm.description"
                rows="2"
                class="w-full rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-3 py-2 text-sm text-slate-800 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
                placeholder="What kind of games do you play?"
              />
            </div>
            <div>
              <label class="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Seat size <span class="font-normal text-slate-400">(optional)</span></label>
              <input
                v-model.number="settingsForm.seat_size"
                type="number"
                min="1"
                max="100"
                placeholder="No limit"
                class="w-full rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-3 py-2 text-sm text-slate-800 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <BaseButton type="submit" :loading="savingSettings" size="sm">Save changes</BaseButton>
          </form>
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
import { computed, onMounted, reactive, ref } from "vue";
import { LinkIcon } from "@heroicons/vue/24/outline";
import { useRoute, useRouter } from "vue-router";
import BaseAlert from "../components/ui/BaseAlert.vue";
import BaseAvatar from "../components/ui/BaseAvatar.vue";
import BaseButton from "../components/ui/BaseButton.vue";
import BaseCard from "../components/ui/BaseCard.vue";
import SkeletonLoader from "../components/ui/SkeletonLoader.vue";
import { useCurrentUser } from "../composables/useCurrentUser.js";
import { useToast } from "../composables/useToast.js";
import { request } from "../services/api.js";

const { success: toastSuccess, error: toastError } = useToast();
const { user: currentUser } = useCurrentUser();

const route = useRoute();
const router = useRouter();
const groupId = route.params.id;

const group = ref(null);
const series = ref([]);
const members = ref([]);
const loading = ref(true);
const error = ref(null);

// invite modal
const showInviteModal = ref(false);
const inviteTab = ref("link");
const inviteLink = ref(null);
const creatingInvite = ref(false);
const copied = ref(false);
const inviteEmail = ref("");
const sendingEmailInvite = ref(false);
const emailInviteSent = ref(false);

// delete modal
const showDeleteModal = ref(false);
const deleting = ref(false);
const deleteConfirmText = ref("");

// settings
const settingsForm = reactive({ name: "", description: "", seat_size: null });
const savingSettings = ref(false);
const savingPublic = ref(false);

const isOrganiser = computed(() => group.value?.my_role === "organiser" || group.value?.my_role === "owner");
const isOwner = computed(() => !!group.value && !!currentUser.value && group.value.owner_id === currentUser.value.id);

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
    Object.assign(settingsForm, {
      name: group.value.name,
      description: group.value.description ?? "",
      seat_size: group.value.seat_size ?? null,
    });
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

async function sendEmailInvite() {
  if (!inviteEmail.value) return;
  sendingEmailInvite.value = true;
  try {
    const res = await request(`/api/groups/${groupId}/invites`, {
      method: "POST",
      body: JSON.stringify({ email: inviteEmail.value, expires_in_days: 7 }),
    });
    if (!res.ok) throw new Error("Failed to send invite");
    emailInviteSent.value = true;
  } catch (err) {
    toastError(err.message);
  } finally {
    sendingEmailInvite.value = false;
  }
}

function closeInviteModal() {
  showInviteModal.value = false;
  inviteLink.value = null;
  copied.value = false;
  inviteEmail.value = "";
  emailInviteSent.value = false;
  inviteTab.value = "link";
}

function openDeleteModal() {
  deleteConfirmText.value = "";
  showDeleteModal.value = true;
}

async function deleteGroup() {
  if (deleteConfirmText.value !== group.value.name) return;
  deleting.value = true;
  try {
    const res = await request(`/api/groups/${groupId}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to delete group");
    router.push("/dashboard");
  } catch (err) {
    toastError(err.message);
    showDeleteModal.value = false;
  } finally {
    deleting.value = false;
  }
}

async function saveSettings() {
  savingSettings.value = true;
  try {
    const payload = {
      name: settingsForm.name,
      description: settingsForm.description || null,
      seat_size: settingsForm.seat_size || null,
    };
    const res = await request(`/api/groups/${groupId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Failed to save settings");
    group.value = await res.json();
    toastSuccess("Settings saved");
  } catch (err) {
    toastError(err.message);
  } finally {
    savingSettings.value = false;
  }
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
