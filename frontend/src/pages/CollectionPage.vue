<template>
  <div class="max-w-5xl mx-auto px-4 sm:px-6 py-8">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold text-slate-900 dark:text-white">My Collection</h1>
      <BaseButton @click="openAddModal" size="sm">+ Add game</BaseButton>
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

    <div v-if="loading" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <SkeletonLoader v-for="i in 6" :key="i" height="h-72" rounded="rounded-2xl" />
    </div>

    <BaseAlert v-else-if="error" variant="error" :message="error" />

    <div v-else-if="filteredEntries.length === 0" class="text-center py-20">
      <div class="w-16 h-16 mx-auto mb-4 rounded-2xl bg-primary-100 dark:bg-primary-950 flex items-center justify-center">
        <PuzzlePieceIcon class="w-8 h-8 text-primary-600 dark:text-primary-400" />
      </div>
      <p class="text-slate-500 dark:text-slate-400 mb-4">
        {{ activeTab === 'all' ? 'No games in your collection yet.' : `No games in your ${activeTab.replace('_', ' ')} list.` }}
      </p>
      <BaseButton @click="openAddModal">Add your first game</BaseButton>
    </div>

    <!-- Game grid -->
    <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <div
        v-for="entry in filteredEntries"
        :key="entry.id"
        class="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-card overflow-hidden flex flex-col"
      >
        <!-- Cover image -->
        <div class="relative h-44 bg-slate-100 dark:bg-slate-700 flex items-center justify-center overflow-hidden flex-shrink-0">
          <img
            v-if="coverImage(entry)"
            :src="coverImage(entry)"
            :alt="entry.game_title"
            class="w-full h-full object-cover"
          />
          <PuzzlePieceIcon v-else class="w-12 h-12 text-slate-300 dark:text-slate-600" />

          <!-- Rating badge -->
          <div
            v-if="bgg(entry)?.average_rating"
            class="absolute top-2 right-2 bg-black/60 backdrop-blur-sm text-white text-xs font-bold px-2 py-1 rounded-lg flex items-center gap-1"
          >
            <StarIcon class="w-3 h-3 text-amber-400" />
            {{ bgg(entry).average_rating.toFixed(1) }}
          </div>

          <!-- Status badge -->
          <div class="absolute bottom-2 left-2">
            <span :class="statusClass(entry.status)" class="text-xs px-2 py-0.5 rounded-full capitalize font-medium">
              {{ entry.status.replace('_', ' ') }}
            </span>
          </div>
        </div>

        <div class="p-4 flex flex-col flex-1">
          <!-- Title + year -->
          <div class="mb-2">
            <h3 class="font-semibold text-slate-900 dark:text-white text-sm leading-tight">{{ entry.game_title }}</h3>
            <p v-if="bgg(entry)?.year_published" class="text-xs text-slate-400 dark:text-slate-500 mt-0.5">{{ bgg(entry).year_published }}</p>
          </div>

          <!-- Stats row -->
          <div v-if="bgg(entry)" class="flex flex-wrap gap-x-3 gap-y-1 mb-2">
            <span v-if="bgg(entry).min_players" class="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
              <UsersIcon class="w-3.5 h-3.5" />
              {{ bgg(entry).min_players }}{{ bgg(entry).max_players && bgg(entry).max_players !== bgg(entry).min_players ? `–${bgg(entry).max_players}` : '' }}
            </span>
            <span v-if="bgg(entry).min_playtime" class="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
              <ClockIcon class="w-3.5 h-3.5" />
              {{ bgg(entry).min_playtime }}{{ bgg(entry).max_playtime && bgg(entry).max_playtime !== bgg(entry).min_playtime ? `–${bgg(entry).max_playtime}` : '' }} min
            </span>
            <span v-if="bgg(entry).complexity" class="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
              <AdjustmentsHorizontalIcon class="w-3.5 h-3.5" />
              {{ bgg(entry).complexity }}/5
            </span>
            <span v-if="bgg(entry).min_age" class="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
              {{ bgg(entry).min_age }}+
            </span>
          </div>
          <!-- Fallback player count when no BGG data -->
          <p v-else-if="entry.min_players || entry.max_players" class="text-xs text-slate-400 dark:text-slate-500 mb-2">
            {{ entry.min_players }}–{{ entry.max_players }} players
          </p>

          <!-- Category tags -->
          <div v-if="bgg(entry)?.categories?.length" class="flex flex-wrap gap-1 mb-2">
            <span
              v-for="cat in bgg(entry).categories.slice(0, 3)"
              :key="cat"
              class="text-xs px-1.5 py-0.5 rounded-md bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400"
            >{{ cat }}</span>
          </div>

          <p v-if="entry.notes" class="text-xs text-slate-500 dark:text-slate-400 mb-2 line-clamp-2 flex-1">{{ entry.notes }}</p>
          <div class="flex-1" />

          <!-- Actions -->
          <div class="flex gap-2 pt-3 border-t border-slate-100 dark:border-slate-700 mt-2">
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

            <!-- BGG search (add mode only) -->
            <template v-if="!editingEntry">
              <div class="flex gap-2 mb-3">
                <input
                  v-model="searchQuery"
                  type="text"
                  placeholder="Search BoardGameGeek…"
                  @keydown.enter.prevent="searchBgg"
                  class="flex-1 rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 px-3 py-2 text-sm text-slate-800 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
                <BaseButton @click="searchBgg" :loading="searching" size="sm">Search</BaseButton>
              </div>

              <!-- Search results -->
              <div v-if="searchResults.length" class="mb-4 border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden max-h-48 overflow-y-auto">
                <button
                  v-for="r in searchResults"
                  :key="r.bgg_id"
                  @click="selectBggGame(r)"
                  :class="selectedBgg?.bgg_id === r.bgg_id ? 'bg-primary-50 dark:bg-primary-950' : 'hover:bg-slate-50 dark:hover:bg-slate-700'"
                  class="w-full text-left px-3 py-2 text-sm border-b border-slate-100 dark:border-slate-700 last:border-0 transition-colors"
                >
                  <span class="font-medium text-slate-800 dark:text-slate-100">{{ r.title }}</span>
                  <span v-if="r.year_published" class="text-slate-400 dark:text-slate-500 ml-2 text-xs">{{ r.year_published }}</span>
                </button>
              </div>
              <p v-else-if="searchResults.length === 0 && searchQuery && !searching" class="text-xs text-slate-400 mb-3">No results found.</p>

              <!-- Selected game preview -->
              <div v-if="selectedBgg" class="flex gap-3 mb-4 p-3 bg-slate-50 dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700">
                <img v-if="selectedBgg.thumbnail" :src="selectedBgg.thumbnail" :alt="selectedBgg.title"
                  class="w-16 h-20 object-cover rounded-lg flex-shrink-0" />
                <div class="min-w-0">
                  <p class="font-semibold text-sm text-slate-900 dark:text-white">{{ selectedBgg.title }}</p>
                  <p v-if="selectedBgg.year_published" class="text-xs text-slate-400 mt-0.5">{{ selectedBgg.year_published }}</p>
                  <div class="flex flex-wrap gap-x-3 gap-y-1 mt-1.5">
                    <span v-if="selectedBgg.average_rating" class="flex items-center gap-1 text-xs text-slate-600 dark:text-slate-300">
                      <StarIcon class="w-3 h-3 text-amber-400" /> {{ selectedBgg.average_rating.toFixed(1) }}
                    </span>
                    <span v-if="selectedBgg.min_players" class="text-xs text-slate-500 dark:text-slate-400">
                      {{ selectedBgg.min_players }}{{ selectedBgg.max_players && selectedBgg.max_players !== selectedBgg.min_players ? `–${selectedBgg.max_players}` : '' }} players
                    </span>
                    <span v-if="selectedBgg.min_playtime" class="text-xs text-slate-500 dark:text-slate-400">
                      {{ selectedBgg.min_playtime }}{{ selectedBgg.max_playtime && selectedBgg.max_playtime !== selectedBgg.min_playtime ? `–${selectedBgg.max_playtime}` : '' }} min
                    </span>
                    <span v-if="selectedBgg.complexity" class="text-xs text-slate-500 dark:text-slate-400">
                      Weight {{ selectedBgg.complexity }}/5
                    </span>
                  </div>
                </div>
              </div>

              <div v-if="!selectedBgg" class="mb-3">
                <BaseInput v-model="form.game_title" label="Or enter title manually" placeholder="e.g. Wingspan" />
              </div>
            </template>

            <form @submit.prevent="saveEntry" class="space-y-3">
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
                <BaseButton type="submit" :loading="saving" :disabled="!editingEntry && !selectedBgg && !form.game_title">
                  {{ editingEntry ? 'Save' : 'Add game' }}
                </BaseButton>
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
import {
  AdjustmentsHorizontalIcon,
  ClockIcon,
  PuzzlePieceIcon,
  StarIcon,
  UsersIcon,
} from "@heroicons/vue/24/outline";
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
const bggData = ref({});
const loading = ref(true);
const error = ref(null);
const activeTab = ref("all");

const showAddModal = ref(false);
const editingEntry = ref(null);
const saving = ref(false);
const saveError = ref(null);

// BGG search state
const searchQuery = ref("");
const searchResults = ref([]);
const searching = ref(false);
const selectedBgg = ref(null);
const loadingBggDetail = ref(false);

const form = reactive({
  game_title: "",
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

function bgg(entry) {
  return entry.bgg_game_id ? bggData.value[String(entry.bgg_game_id)] ?? null : null;
}

function coverImage(entry) {
  const b = bgg(entry);
  return b?.image || b?.thumbnail || entry.game_thumbnail_url || null;
}

onMounted(fetchCollection);

async function fetchCollection() {
  loading.value = true;
  try {
    const res = await request("/api/users/me/collection");
    if (!res.ok) throw new Error("Failed to load collection");
    entries.value = await res.json();

    const ids = entries.value.filter((e) => e.bgg_game_id).map((e) => e.bgg_game_id);
    if (ids.length) {
      const bggRes = await request(`/api/bgg/games?ids=${ids.join(",")}`);
      if (bggRes.ok) bggData.value = await bggRes.json();
    }
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

function openAddModal() {
  showAddModal.value = true;
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
  searchQuery.value = "";
  searchResults.value = [];
  selectedBgg.value = null;
  Object.assign(form, { game_title: "", status: "own", collection_visible_to: "friends", notes: "" });
}

async function searchBgg() {
  if (!searchQuery.value.trim()) return;
  searching.value = true;
  searchResults.value = [];
  selectedBgg.value = null;
  try {
    const res = await request(`/api/bgg/search?q=${encodeURIComponent(searchQuery.value.trim())}`);
    if (res.ok) searchResults.value = await res.json();
  } finally {
    searching.value = false;
  }
}

async function selectBggGame(result) {
  loadingBggDetail.value = true;
  try {
    const res = await request(`/api/bgg/games?ids=${result.bgg_id}`);
    if (res.ok) {
      const data = await res.json();
      selectedBgg.value = data[String(result.bgg_id)] ?? { ...result };
    } else {
      selectedBgg.value = result;
    }
  } finally {
    loadingBggDetail.value = false;
  }
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
      const payload = {
        game_title: selectedBgg.value?.title ?? form.game_title,
        status: form.status,
        collection_visible_to: form.collection_visible_to,
        notes: form.notes || null,
      };
      if (selectedBgg.value) {
        payload.bgg_game_id = selectedBgg.value.bgg_id;
        payload.game_thumbnail_url = selectedBgg.value.thumbnail || null;
        payload.min_players = selectedBgg.value.min_players || null;
        payload.max_players = selectedBgg.value.max_players || null;
        payload.complexity = selectedBgg.value.complexity || null;
        // Cache BGG data immediately so card renders rich on add
        bggData.value[String(selectedBgg.value.bgg_id)] = selectedBgg.value;
      }
      const res = await request("/api/users/me/collection", { method: "POST", body: JSON.stringify(payload) });
      if (!res.ok) { const d = await res.json(); throw new Error(d.detail || "Add failed"); }
      entries.value.unshift(await res.json());
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
