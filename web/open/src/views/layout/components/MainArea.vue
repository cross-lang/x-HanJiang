<template>
  <main class="main-area">
    <router-view />
  </main>
</template>

<style scoped>
.main-area {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  background: var(--hj-bg-page);
}
</style>
