<template>
  <div class="max-w-5xl mx-auto px-4 sm:px-6 py-8">
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="text-2xl font-bold text-slate-900 dark:text-white">Friends' Games</h1>
        <p class="text-sm text-slate-500 dark:text-slate-400 mt-0.5">Games your friends own</p>
      </div>
      <router-link to="/friends" class="text-sm text-primary-600 hover:underline dark:text-primary-400">← Friends</router-link>
    </div>

    <!-- Filters -->
    <div class="flex gap-3 mb-6 flex-wrap">
      <BaseInput v-model="search" placeholder="Search games…" class="max-w-xs" />
      <BaseInput v-model.number="minPlayers" label="" placeholder="Min players" type="number" class="w-32" />
      <BaseInput v-model.number="maxPlayers" label="" placeholder="Max players" type="number" class="w-32" />
      <BaseButton @click="fetchGames" variant="secondary" size="sm">Filter</BaseButton>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <SkeletonLoader v-for="i in 6" :key="i" height="h-40" rounded="rounded-2xl" />
    </div>

    <BaseAlert v-else-if="error" variant="error" :message="error" />

    <div v-else-if="games.length === 0" class="text-center py-20">
      <PuzzlePieceIcon class="w-10 h-10 mx-auto mb-3 text-slate-300 dark:text-slate-600" />
      <p class="text-slate-500 dark:text-slate-400">
        {{ hasFriends ? "No games match your filters." : "Add friends to see their games here." }}
      </p>
      <BaseButton v-if="!hasFriends" to="/friends" class="mt-4" variant="secondary">Find friends</BaseButton>
    </div>

    <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <div v-for="game in games" :key="game.bgg_game_id"
        class="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-card overflow-hidden">
        <div class="h-32 bg-slate-100 dark:bg-slate-700 flex items-center justify-center overflow-hidden">
          <img v-if="game.game_thumbnail_url" :src="game.game_thumbnail_url" :alt="game.game_title" class="w-full h-full object-cover" />
          <PuzzlePieceIcon v-else class="w-10 h-10 text-slate-300 dark:text-slate-600" />
        </div>

        <div class="p-4">
          <h3 class="font-semibold text-slate-900 dark:text-white text-sm mb-1 leading-tight">{{ game.game_title }}</h3>

          <div class="flex flex-wrap gap-2 text-xs text-slate-400 dark:text-slate-500 mb-3">
            <span v-if="game.min_players || game.max_players">{{ game.min_players }}–{{ game.max_players }} players</span>
            <span v-if="game.complexity">⚙ {{ Number(game.complexity).toFixed(1) }}</span>
          </div>

          <!-- Owners -->
          <div>
            <p class="text-xs text-slate-500 dark:text-slate-400 mb-1.5">Owned by:</p>
            <div class="flex flex-wrap gap-1">
              <span v-for="owner in game.owners" :key="owner.user_id"
                class="inline-flex items-center gap-1 text-xs bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-full px-2 py-0.5">
                <BaseAvatar :name="owner.display_name || owner.username" size="sm" class="w-4 h-4" />
                {{ owner.display_name || owner.username }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { PuzzlePieceIcon } from "@heroicons/vue/24/outline";
import BaseAlert from "../components/ui/BaseAlert.vue";
import BaseAvatar from "../components/ui/BaseAvatar.vue";
import BaseButton from "../components/ui/BaseButton.vue";
import BaseInput from "../components/ui/BaseInput.vue";
import SkeletonLoader from "../components/ui/SkeletonLoader.vue";
import { request } from "../services/api.js";

const games = ref([]);
const loading = ref(true);
const error = ref(null);
const hasFriends = ref(true);
const search = ref("");
const minPlayers = ref(null);
const maxPlayers = ref(null);

onMounted(fetchGames);

async function fetchGames() {
  loading.value = true;
  error.value = null;
  try {
    const params = new URLSearchParams({ status: "own" });
    if (search.value) params.set("q", search.value);
    if (minPlayers.value) params.set("min_players", minPlayers.value);
    if (maxPlayers.value) params.set("max_players", maxPlayers.value);

    const [gRes, fRes] = await Promise.all([
      request(`/api/friends/collection?${params}`),
      request("/api/friends"),
    ]);

    games.value = gRes.ok ? await gRes.json() : [];
    const friends = fRes.ok ? await fRes.json() : [];
    hasFriends.value = friends.length > 0;
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}
</script>
