<template>
  <div class="max-w-3xl mx-auto px-4 sm:px-6 py-8">
    <h1 class="text-2xl font-bold text-slate-900 dark:text-white mb-6">Profile</h1>

    <div v-if="loading" class="space-y-4">
      <SkeletonLoader height="h-5" width="w-48" />
      <SkeletonLoader height="h-4" width="w-64" />
      <SkeletonLoader height="h-10" />
      <SkeletonLoader height="h-10" />
    </div>

    <BaseAlert v-else-if="fetchError" variant="error" :message="fetchError" />

    <template v-else>
      <!-- Info -->
      <BaseCard class="mb-6">
        <div class="flex items-start gap-5">
          <BaseAvatar :src="user.avatar_url" :name="user.display_name || user.username" size="xl" />
          <div class="flex-1 min-w-0">
            <p class="font-semibold text-slate-900 dark:text-white text-lg">{{ user.display_name || user.username }}</p>
            <p class="text-sm text-slate-500 dark:text-slate-400">@{{ user.username }}</p>
            <p class="text-xs text-slate-400 dark:text-slate-500 mt-1">{{ user.email }}</p>
            <p class="text-xs text-slate-400 dark:text-slate-500">
              Member since {{ new Date(user.created_at).toLocaleDateString() }}
            </p>
          </div>
        </div>
      </BaseCard>

      <!-- Edit form -->
      <BaseCard>
        <h2 class="text-base font-semibold text-slate-900 dark:text-white mb-5">Edit profile</h2>
        <form @submit.prevent="save" class="space-y-4">
          <BaseInput v-model="form.display_name" label="Display name" />
          <BaseInput v-model="form.bio" label="Bio" type="textarea" :rows="3" />
          <BaseInput v-model="form.avatar_url" label="Avatar URL" type="url" />

          <div class="flex items-center gap-3 pt-2">
            <BaseButton type="submit" :loading="saving">Save changes</BaseButton>
          </div>
        </form>
      </BaseCard>
    </template>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import BaseAlert from "../components/ui/BaseAlert.vue";
import BaseAvatar from "../components/ui/BaseAvatar.vue";
import BaseButton from "../components/ui/BaseButton.vue";
import BaseCard from "../components/ui/BaseCard.vue";
import BaseInput from "../components/ui/BaseInput.vue";
import SkeletonLoader from "../components/ui/SkeletonLoader.vue";
import { useToast } from "../composables/useToast.js";
import { request } from "../services/api.js";

const { success: toastSuccess, error: toastError } = useToast();

const user = ref(null);
const loading = ref(true);
const fetchError = ref(null);
const saving = ref(false);
const form = reactive({ display_name: "", bio: "", avatar_url: "" });

onMounted(async () => {
  try {
    const res = await request("/api/users/me");
    if (!res.ok) throw new Error("Failed to load profile");
    user.value = await res.json();
    form.display_name = user.value.display_name || "";
    form.bio = user.value.bio || "";
    form.avatar_url = user.value.avatar_url || "";
  } catch (err) {
    fetchError.value = err.message;
  } finally {
    loading.value = false;
  }
});

async function save() {
  saving.value = true;
  try {
    const res = await request("/api/users/me", {
      method: "PATCH",
      body: JSON.stringify(form),
    });
    if (!res.ok) throw new Error("Save failed");
    user.value = await res.json();
    toastSuccess("Profile saved!");
  } catch (err) {
    toastError(err.message);
  } finally {
    saving.value = false;
  }
}
</script>
