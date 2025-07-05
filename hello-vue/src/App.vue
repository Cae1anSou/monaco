<style>
h1 {
  text-align: center;
  margin-top: 2rem;
  color: #42b883;
}
</style>


<template>
  <main>
    <h1>{{ msg }}</h1>
    <button @click="count++">count is {{ count }}</button>
  </main>
</template>

<script setup>
import { ref } from 'vue'
const msg = 'Hello Vue Sandbox'
const count = ref(0)
</script>