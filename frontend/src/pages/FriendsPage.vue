<template>
  <div class="max-w-3xl mx-auto px-4 sm:px-6 py-8">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold text-slate-900 dark:text-white">Friends</h1>
      <BaseButton to="/friends/games" variant="secondary" size="sm">
        <PuzzlePieceIcon class="w-4 h-4 mr-1.5" /> Friends' games
      </BaseButton>
    </div>

    <!-- Add friend -->
    <BaseCard class="mb-4">
      <h2 class="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">Add a friend</h2>
      <form @submit.prevent="sendRequest" class="flex gap-2">
        <BaseInput v-model="searchUsername" placeholder="Enter username" class="flex-1" />
        <BaseButton type="submit" :loading="sending">Send request</BaseButton>
      </form>
      <BaseAlert v-if="requestError" variant="error" :message="requestError" class="mt-2" />
      <BaseAlert v-if="requestSent" variant="success" message="Friend request sent!" class="mt-2" />
    </BaseCard>

    <!-- Invite link -->
    <BaseCard class="mb-6">
      <h2 class="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-1">Invite a friend</h2>
      <p class="text-xs text-slate-500 dark:text-slate-400 mb-3">Share this link — anyone who opens it can add you as a friend.</p>
      <div v-if="inviteUrl" class="flex gap-2">
        <BaseInput :modelValue="inviteUrl" readonly class="flex-1" />
        <BaseButton @click="copyInvite" variant="secondary" size="sm">{{ copied ? 'Copied!' : 'Copy' }}</BaseButton>
      </div>
      <BaseButton v-else @click="generateInvite" :loading="generatingInvite" variant="secondary" size="sm">
        <LinkIcon class="w-4 h-4 mr-1.5" /> Generate invite link
      </BaseButton>
    </BaseCard>

    <!-- Pending incoming requests -->
    <section v-if="pendingRequests.length > 0" class="mb-6">
      <h2 class="font-semibold text-slate-700 dark:text-slate-300 mb-3">
        Pending requests <span class="text-xs bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300 rounded-full px-2 py-0.5 ml-1">{{ pendingRequests.length }}</span>
      </h2>
      <div class="space-y-2">
        <div v-for="req in pendingRequests" :key="req.friendship_id"
          class="flex items-center justify-between bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-card px-4 py-3">
          <div class="flex items-center gap-3">
            <BaseAvatar :name="req.display_name || req.username" />
            <div>
              <p class="text-sm font-medium text-slate-900 dark:text-white">{{ req.display_name || req.username }}</p>
              <p class="text-xs text-slate-400 dark:text-slate-500">@{{ req.username }}</p>
            </div>
          </div>
          <div class="flex gap-2">
            <BaseButton @click="respond(req.friendship_id, 'accepted')" size="sm">Accept</BaseButton>
            <BaseButton @click="respond(req.friendship_id, 'declined')" variant="secondary" size="sm">Decline</BaseButton>
          </div>
        </div>
      </div>
    </section>

    <!-- Friends list -->
    <section>
      <h2 class="font-semibold text-slate-700 dark:text-slate-300 mb-3">
        My friends <span class="text-xs text-slate-400 dark:text-slate-500 ml-1">{{ friends.length }}</span>
      </h2>

      <div v-if="loading" class="space-y-2">
        <SkeletonLoader v-for="i in 4" :key="i" height="h-16" rounded="rounded-2xl" />
      </div>
      <BaseAlert v-else-if="error" variant="error" :message="error" />
      <div v-else-if="friends.length === 0" class="text-center py-12 bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700">
        <UserGroupIcon class="w-8 h-8 text-slate-300 dark:text-slate-600 mx-auto mb-2" />
        <p class="text-sm text-slate-500 dark:text-slate-400">No friends yet — send a request above.</p>
      </div>
      <div v-else class="space-y-2">
        <div v-for="friend in friends" :key="friend.friendship_id"
          class="flex items-center justify-between bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-card px-4 py-3">
          <router-link :to="`/users/${friend.user_id}/collection`" class="flex items-center gap-3 flex-1 min-w-0 hover:opacity-80 transition-opacity">
            <BaseAvatar :name="friend.display_name || friend.username" :src="friend.avatar_url" />
            <div class="min-w-0">
              <p class="text-sm font-medium text-slate-900 dark:text-white truncate">{{ friend.display_name || friend.username }}</p>
              <p class="text-xs text-slate-400 dark:text-slate-500">@{{ friend.username }} · {{ friend.game_count }} {{ friend.game_count === 1 ? 'game' : 'games' }}</p>
            </div>
          </router-link>
          <button @click="unfriend(friend.friendship_id)"
            class="ml-3 text-xs text-slate-400 hover:text-red-500 dark:hover:text-red-400 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 rounded px-2 py-1">
            Remove
          </button>
        </div>
      </div>
    </section>

    <!-- Suggestions -->
    <section v-if="suggestions.length > 0" class="mt-8">
      <h2 class="font-semibold text-slate-700 dark:text-slate-300 mb-3 text-sm">People you play with</h2>
      <div class="space-y-2">
        <div v-for="s in suggestions" :key="s.user_id"
          class="flex items-center justify-between bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-card px-4 py-3">
          <div class="flex items-center gap-3">
            <BaseAvatar :name="s.display_name || s.username" :src="s.avatar_url" />
            <div>
              <p class="text-sm font-medium text-slate-900 dark:text-white">{{ s.display_name || s.username }}</p>
              <p class="text-xs text-slate-400 dark:text-slate-500">@{{ s.username }}</p>
            </div>
          </div>
          <BaseButton @click="sendRequestTo(s.username)" variant="secondary" size="sm">Add friend</BaseButton>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { LinkIcon, PuzzlePieceIcon, UserGroupIcon } from "@heroicons/vue/24/outline";
import BaseAlert from "../components/ui/BaseAlert.vue";
import BaseAvatar from "../components/ui/BaseAvatar.vue";
import BaseButton from "../components/ui/BaseButton.vue";
import BaseCard from "../components/ui/BaseCard.vue";
import BaseInput from "../components/ui/BaseInput.vue";
import SkeletonLoader from "../components/ui/SkeletonLoader.vue";
import { useToast } from "../composables/useToast.js";
import { request } from "../services/api.js";

const { success: toastSuccess, error: toastError } = useToast();

const friends = ref([]);
const pendingRequests = ref([]);
const suggestions = ref([]);
const loading = ref(true);
const error = ref(null);
const searchUsername = ref("");
const sending = ref(false);
const requestError = ref(null);
const requestSent = ref(false);
const inviteUrl = ref(null);
const generatingInvite = ref(false);
const copied = ref(false);

onMounted(async () => {
  try {
    const [fRes, rRes, sRes] = await Promise.all([
      request("/api/friends"),
      request("/api/friends/requests"),
      request("/api/friends/suggestions"),
    ]);
    friends.value = fRes.ok ? await fRes.json() : [];
    pendingRequests.value = rRes.ok ? await rRes.json() : [];
    suggestions.value = sRes.ok ? await sRes.json() : [];
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
});

async function sendRequest() {
  if (!searchUsername.value.trim()) return;
  await sendRequestTo(searchUsername.value.trim());
  searchUsername.value = "";
}

async function sendRequestTo(username) {
  requestError.value = null;
  requestSent.value = false;
  sending.value = true;
  try {
    const res = await request("/api/friends/request", {
      method: "POST",
      body: JSON.stringify({ username }),
    });
    if (!res.ok) {
      const d = await res.json();
      throw new Error(d.detail || "Failed to send request");
    }
    requestSent.value = true;
    suggestions.value = suggestions.value.filter((s) => s.username !== username);
    setTimeout(() => (requestSent.value = false), 3000);
  } catch (err) {
    requestError.value = err.message;
  } finally {
    sending.value = false;
  }
}

async function respond(friendshipId, status) {
  const res = await request(`/api/friends/${friendshipId}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
  if (res.ok) {
    pendingRequests.value = pendingRequests.value.filter((r) => r.friendship_id !== friendshipId);
    if (status === "accepted") {
      const updated = await res.json();
      friends.value.push(updated);
      toastSuccess(`You are now friends with ${updated.username}!`);
    }
  } else {
    toastError("Failed to respond to request.");
  }
}

async function generateInvite() {
  generatingInvite.value = true;
  try {
    const res = await request("/api/friends/invite", { method: "POST" });
    if (!res.ok) throw new Error("Failed to generate invite");
    const data = await res.json();
    inviteUrl.value = data.url;
  } catch (err) {
    toastError(err.message);
  } finally {
    generatingInvite.value = false;
  }
}

async function copyInvite() {
  try {
    await navigator.clipboard.writeText(inviteUrl.value);
    copied.value = true;
    setTimeout(() => (copied.value = false), 2000);
  } catch {
    toastError("Failed to copy to clipboard");
  }
}

async function unfriend(friendshipId) {
  if (!confirm("Remove this friend?")) return;
  const res = await request(`/api/friends/${friendshipId}`, { method: "DELETE" });
  if (res.ok || res.status === 204) {
    friends.value = friends.value.filter((f) => f.friendship_id !== friendshipId);
    toastSuccess("Friend removed.");
  } else {
    toastError("Failed to remove friend.");
  }
}
</script>
