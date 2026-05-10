<template>
  <component
    :is="to ? 'router-link' : 'button'"
    :to="to"
    :type="to ? undefined : type"
    :disabled="!to && (disabled || loading)"
    :class="classes"
    v-bind="$attrs"
  >
    <span v-if="loading" class="inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin mr-2 align-middle" aria-hidden="true" />
    <slot />
  </component>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  variant: { type: String, default: "primary" },
  size: { type: String, default: "md" },
  loading: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  type: { type: String, default: "button" },
  to: { type: [String, Object], default: null },
  block: { type: Boolean, default: false },
});

const variantClasses = {
  primary: "bg-primary-600 text-white hover:bg-primary-700 focus-visible:ring-primary-500 disabled:bg-primary-300 dark:disabled:bg-primary-800",
  secondary: "bg-white text-slate-700 border border-slate-300 hover:bg-slate-50 focus-visible:ring-slate-400 dark:bg-slate-700 dark:text-slate-100 dark:border-slate-600 dark:hover:bg-slate-600 disabled:opacity-50",
  danger: "bg-red-600 text-white hover:bg-red-700 focus-visible:ring-red-500 disabled:opacity-50",
  ghost: "text-slate-600 hover:bg-slate-100 focus-visible:ring-slate-400 dark:text-slate-300 dark:hover:bg-slate-700 disabled:opacity-50",
};

const sizeClasses = {
  sm: "px-3 py-1.5 text-xs rounded-lg",
  md: "px-4 py-2 text-sm rounded-xl",
  lg: "px-6 py-3 text-base rounded-xl",
};

const classes = computed(() => [
  "inline-flex items-center justify-center font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:cursor-not-allowed",
  variantClasses[props.variant] ?? variantClasses.primary,
  sizeClasses[props.size] ?? sizeClasses.md,
  props.block ? "w-full" : "",
]);
</script>
