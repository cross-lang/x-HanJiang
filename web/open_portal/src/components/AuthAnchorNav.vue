<template>
  <div class="auth-anchor-nav">
    <a
      v-for="a in anchors"
      :key="a.id"
      class="auth-anchor-item"
      :class="{ active: activeId === a.id }"
      :href="`#${a.id}`"
      @click.prevent="scrollTo(a.id)"
    >
      {{ a.label }}
    </a>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

export interface AuthAnchor {
  id: string
  label: string
}

const props = defineProps<{ anchors: AuthAnchor[] }>()

const activeId = ref('')

function scrollTo(id: string) {
  const el = document.getElementById(id)
  if (!el) return
  const top = el.getBoundingClientRect().top + window.scrollY - 88
  window.scrollTo({ top, behavior: 'smooth' })
  activeId.value = id
}

let observer: IntersectionObserver | null = null

onMounted(() => {
  // 每个锚点段包一层监听：进入视口顶部 200px 时置为当前
  observer = new IntersectionObserver(
    entries => {
      for (const e of entries) {
        if (e.isIntersecting) activeId.value = e.target.id
      }
    },
    { rootMargin: '-120px 0px -65% 0px', threshold: 0 },
  )
  for (const a of props.anchors) {
    const el = document.getElementById(a.id)
    if (el) observer.observe(el)
  }
})

onBeforeUnmount(() => observer?.disconnect())
</script>

<style scoped>
.auth-anchor-nav {
  position: sticky;
  top: 0;
  z-index: 9;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 18px;
  padding: 10px 14px;
  background: color-mix(in srgb, var(--hj-bg-card) 92%, transparent);
  backdrop-filter: blur(6px);
  border: 1px solid var(--hj-border-lighter);
  border-radius: var(--hj-radius-lg);
  box-shadow: 0 2px 10px rgba(31, 45, 61, 0.04);
}
.auth-anchor-item {
  padding: 5px 14px;
  font-size: 13px;
  color: var(--hj-text-secondary);
  border-radius: 999px;
  text-decoration: none;
  transition: all 0.15s;
  user-select: none;
}
.auth-anchor-item:hover {
  color: var(--hj-primary);
  background: var(--hj-primary-bg);
}
.auth-anchor-item.active {
  color: #fff;
  background: linear-gradient(135deg, var(--hj-primary), var(--hj-primary-weak));
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.35);
}
</style>
