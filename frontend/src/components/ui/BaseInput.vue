<template>
  <div class="w-full">
    <label v-if="label" :for="inputId" class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
      {{ label }}
      <span v-if="required" class="text-red-500 ml-0.5" aria-hidden="true">*</span>
    </label>
    <div class="relative">
      <div v-if="$slots.leading" class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-slate-400">
        <slot name="leading" />
      </div>
      <component
        :is="type === 'textarea' ? 'textarea' : 'input'"
        :id="inputId"
        v-bind="$attrs"
        :type="type !== 'textarea' ? type : undefined"
        :rows="type === 'textarea' ? rows : undefined"
        :required="required"
        :value="modelValue"
        :class="inputClasses"
        @input="$emit('update:modelValue', $event.target.value)"
      />
      <div v-if="$slots.trailing" class="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none text-slate-400">
        <slot name="trailing" />
      </div>
    </div>
    <p v-if="error" :id="`${inputId}-error`" role="alert" class="mt-1 text-xs text-red-500 dark:text-red-400">{{ error }}</p>
    <p v-else-if="hint" class="mt-1 text-xs text-slate-500 dark:text-slate-400">{{ hint }}</p>
  </div>
</template>

<script setup>
import { computed, useId } from "vue";

const props = defineProps({
  modelValue: { type: String, default: "" },
  label: { type: String, default: "" },
  type: { type: String, default: "text" },
  error: { type: String, default: "" },
  hint: { type: String, default: "" },
  required: { type: Boolean, default: false },
  rows: { type: Number, default: 3 },
});

defineEmits(["update:modelValue"]);
defineOptions({ inheritAttrs: false });

const inputId = useId();

const inputClasses = computed(() => [
  "w-full rounded-xl border px-3 py-2 text-sm text-slate-900 dark:text-slate-100 bg-white dark:bg-slate-800 placeholder-slate-400 transition-colors",
  "focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent",
  props.$slots?.leading ? "pl-9" : "",
  props.$slots?.trailing ? "pr-9" : "",
  props.error
    ? "border-red-400 dark:border-red-500"
    : "border-slate-300 dark:border-slate-600",
  props.type === "textarea" ? "resize-none" : "",
]);
</script>
