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
      <!-- Info card -->
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
            <div v-if="collectionStats" class="mt-2 flex gap-3">
              <router-link to="/collection" class="text-xs text-primary-600 dark:text-primary-400 hover:underline">
                {{ collectionStats.own }} {{ collectionStats.own === 1 ? 'game' : 'games' }} owned
              </router-link>
              <span v-if="collectionStats.wishlist > 0" class="text-xs text-slate-400">
                · {{ collectionStats.wishlist }} on wishlist
              </span>
            </div>
          </div>
        </div>
      </BaseCard>

      <!-- Edit form -->
      <BaseCard class="mb-6">
        <h2 class="text-base font-semibold text-slate-900 dark:text-white mb-5">Edit profile</h2>
        <form @submit.prevent="save" class="space-y-5">
          <!-- Avatar -->
          <div>
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">Photo</label>
            <div class="flex items-center gap-4">
              <AvatarUpload
                :src="user.avatar_url || ''"
                :name="user.display_name || user.username"
                v-model="pendingFile"
              />
              <div class="text-xs text-slate-400 dark:text-slate-500">
                <p>JPG, PNG or WebP</p>
                <p>Max 2 MB</p>
              </div>
            </div>
            <div v-if="uploadError" class="mt-2 text-xs text-red-600 dark:text-red-400">{{ uploadError }}</div>
          </div>

          <BaseInput v-model="form.display_name" label="Display name" maxlength="100" />
          <BaseInput v-model="form.bio" label="Bio" type="textarea" :rows="3" maxlength="500" />

          <div class="flex items-center gap-3 pt-2">
            <BaseButton type="submit" :loading="saving">Save changes</BaseButton>
          </div>
        </form>
      </BaseCard>

      <!-- Visibility settings -->
      <BaseCard>
        <h2 class="text-base font-semibold text-slate-900 dark:text-white mb-4">Privacy</h2>
        <div class="space-y-4">
          <label class="flex items-start justify-between gap-4 cursor-pointer">
            <div>
              <p class="text-sm font-medium text-slate-800 dark:text-slate-200">Public profile</p>
              <p class="text-xs text-slate-400 dark:text-slate-500 mt-0.5">Anyone can view your profile at /users/{{ user.username }}</p>
            </div>
            <button
              type="button"
              role="switch"
              :aria-checked="form.profile_public"
              @click="toggleVisibility('profile_public')"
              :class="form.profile_public ? 'bg-primary-600' : 'bg-slate-300 dark:bg-slate-600'"
              class="relative inline-flex h-6 w-11 flex-shrink-0 rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
            >
              <span
                :class="form.profile_public ? 'translate-x-5' : 'translate-x-0'"
                class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out"
              />
            </button>
          </label>

          <label v-if="form.profile_public" class="flex items-start justify-between gap-4 cursor-pointer">
            <div>
              <p class="text-sm font-medium text-slate-800 dark:text-slate-200">Public stats</p>
              <p class="text-xs text-slate-400 dark:text-slate-500 mt-0.5">Show play and collection stats on your public profile</p>
            </div>
            <button
              type="button"
              role="switch"
              :aria-checked="form.stats_public"
              @click="toggleVisibility('stats_public')"
              :class="form.stats_public ? 'bg-primary-600' : 'bg-slate-300 dark:bg-slate-600'"
              class="relative inline-flex h-6 w-11 flex-shrink-0 rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500"
            >
              <span
                :class="form.stats_public ? 'translate-x-5' : 'translate-x-0'"
                class="pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out"
              />
            </button>
          </label>
        </div>
      </BaseCard>
    </template>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import BaseAlert from "../components/ui/BaseAlert.vue";
import BaseAvatar from "../components/ui/BaseAvatar.vue";
import AvatarUpload from "../components/ui/AvatarUpload.vue";
import BaseButton from "../components/ui/BaseButton.vue";
import BaseCard from "../components/ui/BaseCard.vue";
import BaseInput from "../components/ui/BaseInput.vue";
import SkeletonLoader from "../components/ui/SkeletonLoader.vue";
import { useToast } from "../composables/useToast.js";
import { useCurrentUser } from "../composables/useCurrentUser.js";
import { request } from "../services/api.js";

const { success: toastSuccess, error: toastError } = useToast();
const { user: navUser } = useCurrentUser();

const user = ref(null);
const loading = ref(true);
const fetchError = ref(null);
const saving = ref(false);
const pendingFile = ref(null);
const uploadError = ref(null);
const form = reactive({ display_name: "", bio: "", profile_public: true, stats_public: true });
const collectionStats = ref(null);

onMounted(async () => {
  try {
    const [uRes, cRes] = await Promise.all([
      request("/api/users/me"),
      request("/api/users/me/collection"),
    ]);
    if (!uRes.ok) throw new Error("Failed to load profile");
    user.value = await uRes.json();
    form.display_name = user.value.display_name || "";
    form.bio = user.value.bio || "";
    form.profile_public = user.value.profile_public ?? true;
    form.stats_public = user.value.stats_public ?? true;
    if (cRes.ok) {
      const entries = await cRes.json();
      collectionStats.value = {
        own: entries.filter((e) => e.status === "own").length,
        wishlist: entries.filter((e) => e.status === "wishlist").length,
      };
    }
  } catch (err) {
    fetchError.value = err.message;
  } finally {
    loading.value = false;
  }
});

async function save() {
  saving.value = true;
  uploadError.value = null;
  try {
    if (pendingFile.value) {
      if (pendingFile.value.size > 2 * 1024 * 1024) {
        uploadError.value = "Image must be 2 MB or smaller";
        return;
      }
      const fd = new FormData();
      fd.append("file", pendingFile.value);
      const { access } = (() => {
        return { access: localStorage.getItem("access_token") };
      })();
      const uploadRes = await fetch("/api/users/me/avatar", {
        method: "POST",
        headers: access ? { Authorization: `Bearer ${access}` } : {},
        body: fd,
      });
      if (!uploadRes.ok) {
        const err = await uploadRes.json().catch(() => ({}));
        toastError(err.detail || "Avatar upload failed");
        return;
      }
      user.value = await uploadRes.json();
      pendingFile.value = null;
    }

    const res = await request("/api/users/me", {
      method: "PATCH",
      body: JSON.stringify({
        display_name: form.display_name || null,
        bio: form.bio || null,
      }),
    });
    if (!res.ok) throw new Error("Save failed");
    user.value = await res.json();
    if (navUser.value) navUser.value = { ...navUser.value, ...user.value };
    toastSuccess("Profile saved!");
  } catch (err) {
    toastError(err.message);
  } finally {
    saving.value = false;
  }
}

async function toggleVisibility(field) {
  const newValue = !form[field];
  form[field] = newValue;
  try {
    const res = await request("/api/users/me", {
      method: "PATCH",
      body: JSON.stringify({ [field]: newValue }),
    });
    if (!res.ok) throw new Error("Save failed");
    user.value = await res.json();
    toastSuccess("Saved");
  } catch (err) {
    form[field] = !newValue;
    toastError(err.message);
  }
}
</script>
