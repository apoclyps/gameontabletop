<template>
  <div v-if="show" role="alert" :class="classes">
    <component :is="icon" class="w-5 h-5 flex-shrink-0" aria-hidden="true" />
    <p class="text-sm flex-1">{{ message }}</p>
    <button v-if="dismissible" @click="show = false" class="flex-shrink-0 ml-2 opacity-60 hover:opacity-100 focus-visible:outline-none focus-visible:ring-2 rounded" :aria-label="'Dismiss'">
      <XMarkIcon class="w-4 h-4" />
    </button>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import {
  CheckCircleIcon,
  ExclamationCircleIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  XMarkIcon,
} from "@heroicons/vue/20/solid";

const props = defineProps({
  variant: { type: String, default: "error" },
  message: { type: String, required: true },
  dismissible: { type: Boolean, default: false },
});

const show = ref(true);

const variantMap = {
  error: {
    classes: "bg-red-50 text-red-700 border border-red-200 dark:bg-red-950 dark:text-red-300 dark:border-red-800",
    icon: ExclamationCircleIcon,
  },
  success: {
    classes: "bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950 dark:text-emerald-300 dark:border-emerald-800",
    icon: CheckCircleIcon,
  },
  warning: {
    classes: "bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950 dark:text-amber-300 dark:border-amber-800",
    icon: ExclamationTriangleIcon,
  },
  info: {
    classes: "bg-primary-50 text-primary-700 border border-primary-200 dark:bg-primary-950 dark:text-primary-300 dark:border-primary-800",
    icon: InformationCircleIcon,
  },
};

const classes = computed(() => [
  "flex items-start gap-3 rounded-xl px-4 py-3",
  variantMap[props.variant]?.classes ?? variantMap.error.classes,
]);

const icon = computed(() => variantMap[props.variant]?.icon ?? ExclamationCircleIcon);
</script>
