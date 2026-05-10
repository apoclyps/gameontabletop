<template>
  <div role="status" aria-label="Loading" :class="classes" />
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  height: { type: String, default: "h-4" },
  width: { type: String, default: "w-full" },
  rounded: { type: String, default: "rounded-lg" },
});

const classes = computed(() => [
  "animate-pulse bg-slate-200 dark:bg-slate-700",
  props.height,
  props.width,
  props.rounded,
]);
</script>
