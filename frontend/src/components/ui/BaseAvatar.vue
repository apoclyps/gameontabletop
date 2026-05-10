<template>
  <div :class="sizeClasses" class="rounded-full overflow-hidden flex items-center justify-center flex-shrink-0">
    <img v-if="src" :src="src" :alt="alt" class="w-full h-full object-cover" />
    <span v-else :class="[textSizeClasses, bgClass]" class="w-full h-full flex items-center justify-center font-semibold text-white">
      {{ initials }}
    </span>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  src: { type: String, default: "" },
  name: { type: String, default: "" },
  size: { type: String, default: "md" },
  alt: { type: String, default: "Avatar" },
});

const sizeClasses = computed(() => ({ sm: "w-7 h-7", md: "w-9 h-9", lg: "w-12 h-12", xl: "w-20 h-20" }[props.size] ?? "w-9 h-9"));
const textSizeClasses = computed(() => ({ sm: "text-xs", md: "text-sm", lg: "text-base", xl: "text-2xl" }[props.size] ?? "text-sm"));

const COLORS = [
  "bg-primary-600", "bg-teal-600", "bg-cyan-600", "bg-sky-600",
  "bg-indigo-600", "bg-violet-600", "bg-fuchsia-600", "bg-rose-600",
];

const bgClass = computed(() => {
  if (!props.name) return COLORS[0];
  const idx = [...props.name].reduce((acc, c) => acc + c.charCodeAt(0), 0) % COLORS.length;
  return COLORS[idx];
});

const initials = computed(() => {
  if (!props.name) return "?";
  return props.name.split(/\s+/).map((w) => w[0]).slice(0, 2).join("").toUpperCase();
});
</script>
