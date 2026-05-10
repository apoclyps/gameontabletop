<template>
  <div class="max-w-lg mx-auto px-4 sm:px-6 py-8">
    <div class="flex items-center gap-3 mb-6">
      <router-link to="/dashboard" class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 rounded-lg p-0.5">
        <ArrowLeftIcon class="w-5 h-5" />
      </router-link>
      <h1 class="text-2xl font-bold text-slate-900 dark:text-white">New group</h1>
    </div>

    <BaseCard>
      <form @submit.prevent="submit" class="space-y-4">
        <BaseInput v-model="form.name" label="Group name" required maxlength="100" placeholder="Friday Night Gamers" />
        <BaseInput v-model="form.description" label="Description" type="textarea" :rows="3" placeholder="What kind of games do you play?" />
        <BaseInput v-model.number="form.seat_size" label="Seat size" type="number" :min="1" :max="100" placeholder="e.g. 6 (leave blank for no limit)" />
        <label class="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300 cursor-pointer select-none">
          <input v-model="form.is_public" type="checkbox"
            class="w-4 h-4 rounded border-slate-300 text-primary-600 focus:ring-primary-500 dark:border-slate-600 dark:bg-slate-700" />
          Public group (discoverable by anyone)
        </label>

        <BaseAlert v-if="error" variant="error" :message="error" />

        <BaseButton type="submit" :loading="loading" block>Create group</BaseButton>
      </form>
    </BaseCard>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ArrowLeftIcon } from "@heroicons/vue/24/outline";
import BaseAlert from "../components/ui/BaseAlert.vue";
import BaseButton from "../components/ui/BaseButton.vue";
import BaseCard from "../components/ui/BaseCard.vue";
import BaseInput from "../components/ui/BaseInput.vue";
import { request } from "../services/api.js";

const router = useRouter();
const loading = ref(false);
const error = ref(null);
const form = reactive({ name: "", description: "", is_public: false, seat_size: null });

async function submit() {
  error.value = null;
  loading.value = true;
  try {
    const res = await request("/api/groups", {
      method: "POST",
      body: JSON.stringify(form),
    });
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || "Failed to create group");
    }
    const group = await res.json();
    router.push(`/groups/${group.id}`);
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}
</script>
