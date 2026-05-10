<template>
  <div :class="classes">
    <slot />
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  padding: { type: String, default: "md" },
  hover: { type: Boolean, default: false },
  flush: { type: Boolean, default: false },
});

const paddingClasses = { sm: "p-4", md: "p-6", lg: "p-8", none: "" };

const classes = computed(() => [
  "bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700",
  props.flush ? "" : (paddingClasses[props.padding] ?? "p-6"),
  "shadow-card",
  props.hover ? "hover:shadow-card-hover transition-shadow cursor-pointer" : "",
]);
</script>
