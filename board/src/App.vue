<script lang="ts">
import Ranklist from './Ranklist.vue'

// https://github.com/vuejs/rfcs/blob/master/active-rfcs/0040-script-setup.md#declaring-additional-options
export default {
  name: 'App',
  components: { Ranklist },
}
</script>

<template>
  <div id="app">
    <Ranklist />
  </div>
</template>

<style src="./tailwind.css" />

<style>
@import "tailwindcss" important;
@import "tailwindcss-primeui";

html {
  font-size: 14px;
  text-autospace: normal;
}
body {
  overflow-y: scroll;
}
</style>
