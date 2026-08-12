<template>
  <VideoPlayer :video-id="Number(route.params.id)" :record-stats="false" />
</template>

<script setup>
definePageMeta({ layout: false });
const route = useRoute();
</script>
