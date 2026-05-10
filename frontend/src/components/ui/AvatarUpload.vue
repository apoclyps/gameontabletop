<template>
  <div class="relative w-24 h-24">
    <BaseAvatar :src="previewUrl || src" :name="name" size="2xl" />
    <label
      class="absolute inset-0 flex items-end justify-center pb-1 cursor-pointer group rounded-full overflow-hidden"
    >
      <span
        class="bg-black/50 text-white text-xs rounded-full px-2 py-0.5 opacity-0 group-hover:opacity-100 transition-opacity mb-1"
      >
        Change
      </span>
      <input
        ref="inputRef"
        type="file"
        class="sr-only"
        accept="image/jpeg,image/png,image/webp"
        @change="onFile"
      />
    </label>
  </div>
</template>

<script setup>
import { ref } from "vue";
import BaseAvatar from "./BaseAvatar.vue";

const props = defineProps({
  src: { type: String, default: "" },
  name: { type: String, default: "" },
  modelValue: { type: Object, default: null },
});

const emit = defineEmits(["update:modelValue"]);

const inputRef = ref(null);
const previewUrl = ref("");

function onFile(e) {
  const file = e.target.files?.[0];
  if (!file) return;
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value);
  previewUrl.value = URL.createObjectURL(file);
  emit("update:modelValue", file);
}

defineExpose({ reset: () => { previewUrl.value = ""; emit("update:modelValue", null); } });
</script>
