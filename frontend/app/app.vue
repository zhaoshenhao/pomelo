<template>
  <NuxtLayout>
    <NuxtPage />
  </NuxtLayout>
</template>

<script setup>
const authStore = useAuthStore();
await authStore.init();
</script>
