<template>
  <!--
      This component displays the red line indicating the current time.
      Its vertical position is controlled by the `top` style property.
    -->
  <div class="absolute w-full flex items-center" :style="{ top: `${top}px` }">
    <div class="w-2 h-2 rounded-full bg-red-500 -ml-1"></div>
    <div class="flex-grow h-0.5 bg-red-500"></div>
  </div>
</template>

<script setup>
defineProps({
  top: {
    type: Number,
    required: true,
  },
});
</script>
