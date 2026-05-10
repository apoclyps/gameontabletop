<template>
  <component :is="layout">
    <RouterView />
  </component>
</template>

<script setup>
import { computed } from "vue";
import { useRoute } from "vue-router";
import AppShell from "./layouts/AppShell.vue";
import AuthLayout from "./layouts/AuthLayout.vue";

const route = useRoute();

const layouts = { app: AppShell, auth: AuthLayout };

const layout = computed(() => {
  const key = route.meta.layout ?? "none";
  return layouts[key] ?? "div";
});
</script>
