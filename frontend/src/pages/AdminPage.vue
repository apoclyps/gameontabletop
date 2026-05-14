<template>
  <div class="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-8">
    <div>
      <h1 class="text-2xl font-bold text-slate-900 dark:text-white">Admin</h1>
      <p class="text-slate-500 dark:text-slate-400 text-sm mt-1">Manage the platform.</p>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <router-link
        to="/admin/users"
        class="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-6 hover:border-primary-400 dark:hover:border-primary-600 transition-colors group"
      >
        <div class="flex items-center gap-3 mb-2">
          <div class="w-10 h-10 rounded-xl bg-primary-100 dark:bg-primary-950 flex items-center justify-center">
            <UsersIcon class="w-5 h-5 text-primary-600 dark:text-primary-400" />
          </div>
          <h2 class="font-semibold text-slate-900 dark:text-white group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
            Users
          </h2>
        </div>
        <p class="text-sm text-slate-500 dark:text-slate-400">
          View and manage user accounts and admin roles.
        </p>
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { UsersIcon } from "@heroicons/vue/24/outline";
</script>
