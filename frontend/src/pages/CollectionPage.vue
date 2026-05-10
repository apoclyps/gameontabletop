<template>
  <div class="max-w-5xl mx-auto px-4 sm:px-6 py-8">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold text-slate-900 dark:text-white">My Collection</h1>
      <BaseButton @click="showAddModal = true" size="sm">+ Add game</BaseButton>
    </div>

    <!-- Tabs -->
    <div class="flex gap-1 mb-6 bg-slate-100 dark:bg-slate-800 rounded-xl p-1 w-fit">
      <button
        v-for="tab in TABS"
        :key="tab.value"
        @click="activeTab = tab.value"
        :class="activeTab === tab.value
          ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
          : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'"
        class="px-3 py-1.5 text-sm font-medium rounded-lg transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
      >
        {{ tab.label }}
        <span v-if="counts[tab.value] !== undefined" class="ml-1 text-xs opacity-60">({{ counts[tab.value] }})</span>
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <SkeletonLoader v-for="i in 6" :key="i" height="h-40" rounded="rounded-2xl" />
    </div>

    <BaseAlert v-else-if="error" variant="error" :message="error" />

    <!-- Empty state -->
    <div v-else-if="filteredEntries.length === 0" class="text-center py-20">
      <div class="w-16 h-16 mx-auto mb-4 rounded-2xl bg-primary-100 dark:bg-primary-950 flex items-center justify-center">
        <PuzzlePieceIcon class="w-8 h-8 text-primary-600 dark:text-primary-400" />
      </div>
      <p class="text-slate-500 dark:text-slate-400 mb-4">
        {{ activeTab === 'all' ? 'No games in your collection yet.' : `No games in your ${activeTab.replace('_', ' ')} list.` }}
      </p>
      <BaseButton @click="showAddModal = true">Add your first game</BaseButton>
    </div>

    <!-- Game grid -->
    <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <div
        v-for="entry in filteredEntries"
        :key="entry.id"
        class="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-card overflow-hidden"
      >
        <!-- Thumbnail -->
        <div class="h-32 bg-slate-100 dark:bg-slate-700 flex items-center justify-center overflow-hidden">
          <img v-if="entry.game_thumbnail_url" :src="entry.game_thumbnail_url" :alt="entry.game_title"
            class="w-full h-full object-cover" />
          <PuzzlePieceIcon v-else class="w-10 h-10 text-slate-300 dark:text-slate-600" />
        </div>

        <div class="p-4">
          <div class="flex justify-between items-start gap-2 mb-1">
            <h3 class="font-semibold text-slate-900 dark:text-white text-sm leading-tight">{{ entry.game_title }}</h3>
            <span :class="statusClass(entry.status)" class="text-xs px-2 py-0.5 rounded-full capitalize flex-shrink-0 whitespace-nowrap">
              {{ entry.status.replace('_', ' ') }}
            </span>
          </div>

          <p v-if="entry.min_players || entry.max_players" class="text-xs text-slate-400 dark:text-slate-500 mb-1">
            {{ entry.min_players }}–{{ entry.max_players }} players
          </p>
          <p v-if="entry.notes" class="text-xs text-slate-500 dark:text-slate-400 mb-2 line-clamp-2">{{ entry.notes }}</p>

          <!-- Actions -->
          <div class="flex gap-2 mt-3 pt-3 border-t border-slate-100 dark:border-slate-700">
            <button @click="startEdit(entry)"
              class="flex-1 text-xs text-slate-500 dark:text-slate-400 hover:text-primary-600 dark:hover:text-primary-400 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 rounded">
              Edit
            </button>
            <button @click="removeEntry(entry)"
              class="flex-1 text-xs text-red-400 hover:text-red-600 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 rounded">
              Remove
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Add / Edit modal -->
    <Teleport to="body">
      <Transition enter-active-class="transition-opacity duration-150" enter-from-class="opacity-0" enter-to-class="opacity-100"
        leave-active-class="transition-opacity duration-100" leave-from-class="opacity-100" leave-to-class="opacity-0">
        <div v-if="showAddModal || editingEntry" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div class="bg-white dark:bg-slate-800 rounded-2xl shadow-xl p-6 max-w-md w-full border border-slate-200 dark:border-slate-700 max-h-[90vh] overflow-y-auto">
            <h3 class="font-semibold text-slate-900 dark:text-white mb-4">{{ editingEntry ? 'Edit game' : 'Add game' }}</h3>

            <form @submit.prevent="saveEntry" class="space-y-3">
              <BaseInput v-if="!editingEntry" v-model="form.game_title" label="Game title" required placeholder="e.g. Wingspan" />
              <BaseInput v-if="!editingEntry" v-model.number="form.bgg_game_id" label="BGG Game ID" type="number" hint="Optional — from boardgamegeek.com" />

              <div>
                <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Status</label>
                <select v-model="form.status"
                  class="w-full border border-slate-300 dark:border-slate-600 rounded-xl px-3 py-2 text-sm bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-primary-500">
                  <option value="own">Own</option>
                  <option value="wishlist">Wishlist</option>
                  <option value="want_to_play">Want to play</option>
                  <option value="previously_owned">Previously owned</option>
                </select>
              </div>

              <div>
                <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">Visibility</label>
                <select v-model="form.collection_visible_to"
                  class="w-full border border-slate-300 dark:border-slate-600 rounded-xl px-3 py-2 text-sm bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-primary-500">
                  <option value="public">Public</option>
                  <option value="friends">Friends only</option>
                  <option value="private">Private</option>
                </select>
              </div>

              <BaseInput v-model="form.notes" label="Notes" type="textarea" :rows="2" placeholder="e.g. includes all expansions" />

              <BaseAlert v-if="saveError" variant="error" :message="saveError" />

              <div class="flex gap-2 pt-2">
                <BaseButton type="submit" :loading="saving">{{ editingEntry ? 'Save' : 'Add game' }}</BaseButton>
                <BaseButton @click="closeModal" variant="ghost" type="button">Cancel</BaseButton>
              </div>
            </form>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { PuzzlePieceIcon } from "@heroicons/vue/24/outline";
import BaseAlert from "../components/ui/BaseAlert.vue";
import BaseButton from "../components/ui/BaseButton.vue";
import BaseInput from "../components/ui/BaseInput.vue";
import SkeletonLoader from "../components/ui/SkeletonLoader.vue";
import { useToast } from "../composables/useToast.js";
import { request } from "../services/api.js";

const { success: toastSuccess, error: toastError } = useToast();

const TABS = [
  { label: "All", value: "all" },
  { label: "Owned", value: "own" },
  { label: "Wishlist", value: "wishlist" },
  { label: "Want to play", value: "want_to_play" },
  { label: "Previously owned", value: "previously_owned" },
];

const entries = ref([]);
const loading = ref(true);
const error = ref(null);
const activeTab = ref("all");
const showAddModal = ref(false);
const editingEntry = ref(null);
const saving = ref(false);
const saveError = ref(null);

const form = reactive({
  game_title: "",
  bgg_game_id: null,
  status: "own",
  collection_visible_to: "friends",
  notes: "",
});

const filteredEntries = computed(() =>
  activeTab.value === "all" ? entries.value : entries.value.filter((e) => e.status === activeTab.value)
);

const counts = computed(() => {
  const c = {};
  for (const tab of TABS) {
    if (tab.value !== "all") c[tab.value] = entries.value.filter((e) => e.status === tab.value).length;
  }
  return c;
});

onMounted(fetchCollection);

async function fetchCollection() {
  loading.value = true;
  try {
    const res = await request("/api/users/me/collection");
    if (!res.ok) throw new Error("Failed to load collection");
    entries.value = await res.json();
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

function startEdit(entry) {
  editingEntry.value = entry;
  form.status = entry.status;
  form.collection_visible_to = entry.collection_visible_to;
  form.notes = entry.notes || "";
}

function closeModal() {
  showAddModal.value = false;
  editingEntry.value = null;
  saveError.value = null;
  Object.assign(form, { game_title: "", bgg_game_id: null, status: "own", collection_visible_to: "friends", notes: "" });
}

async function saveEntry() {
  saving.value = true;
  saveError.value = null;
  try {
    if (editingEntry.value) {
      const res = await request(`/api/users/me/collection/${editingEntry.value.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: form.status, collection_visible_to: form.collection_visible_to, notes: form.notes || null }),
      });
      if (!res.ok) { const d = await res.json(); throw new Error(d.detail || "Save failed"); }
      const updated = await res.json();
      const idx = entries.value.findIndex((e) => e.id === updated.id);
      if (idx >= 0) entries.value[idx] = updated;
      toastSuccess("Game updated!");
    } else {
      const payload = { game_title: form.game_title, status: form.status, collection_visible_to: form.collection_visible_to, notes: form.notes || null };
      if (form.bgg_game_id) payload.bgg_game_id = Number(form.bgg_game_id);
      const res = await request("/api/users/me/collection", { method: "POST", body: JSON.stringify(payload) });
      if (!res.ok) { const d = await res.json(); throw new Error(d.detail || "Add failed"); }
      const newEntry = await res.json();
      entries.value.unshift(newEntry);
      toastSuccess("Game added to collection!");
    }
    closeModal();
  } catch (err) {
    saveError.value = err.message;
  } finally {
    saving.value = false;
  }
}

async function removeEntry(entry) {
  if (!confirm(`Remove "${entry.game_title}" from your collection?`)) return;
  const res = await request(`/api/users/me/collection/${entry.id}`, { method: "DELETE" });
  if (res.ok || res.status === 204) {
    entries.value = entries.value.filter((e) => e.id !== entry.id);
    toastSuccess("Game removed.");
  } else {
    toastError("Failed to remove game.");
  }
}

function statusClass(s) {
  return {
    own: "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
    wishlist: "bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
    want_to_play: "bg-primary-100 text-primary-700 dark:bg-primary-950 dark:text-primary-300",
    previously_owned: "bg-slate-100 text-slate-500 dark:bg-slate-700 dark:text-slate-400",
  }[s] ?? "bg-slate-100 text-slate-500";
}
</script>
