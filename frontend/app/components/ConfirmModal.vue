<template>
  <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click.self="$emit('cancel')">
    <div class="bg-white rounded-2xl shadow-xl w-full max-w-sm mx-4 p-6">
      <h3 class="text-lg font-bold text-gray-900 mb-2">{{ title }}</h3>
      <p class="text-sm text-gray-600 mb-1">{{ message }}</p>
      <p v-if="subMessage" class="text-xs text-gray-400 mb-4">{{ subMessage }}</p>
      <div v-else class="mb-4"></div>
      <slot></slot>
      <div class="flex gap-2" :class="{ 'mt-4': !hasSlot }">
        <button @click="$emit('confirm')" class="flex-1 py-2 text-sm rounded-lg" :class="confirmClass">{{ confirmText }}</button>
        <button @click="$emit('cancel')" class="flex-1 py-2 border border-gray-200 text-sm rounded-lg hover:bg-gray-50">{{ cancelText }}</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, useSlots } from "vue";

const props = defineProps({
  show: Boolean,
  title: { type: String, default: "确认" },
  message: { type: String, default: "" },
  subMessage: { type: String, default: "" },
  confirmText: { type: String, default: "确定" },
  cancelText: { type: String, default: "取消" },
  variant: { type: String, default: "primary" },
});

defineEmits(["confirm", "cancel"]);

const slots = useSlots();
const hasSlot = computed(() => !!slots.default);

const confirmClass = computed(() => {
  const map = {
    primary: "bg-primary-600 text-white hover:bg-primary-700",
    danger: "bg-red-600 text-white hover:bg-red-700",
  };
  return map[props.variant] || map.primary;
});
</script>
