<template>
  <div>
    <Menubar :model="menuItems">
      <template #start>
        <router-link to="/" class="brand">
          <i class="pi pi-github" />
          Contributor tracker
        </router-link>
      </template>
    </Menubar>
    <div class="shell">
      <router-view />
    </div>
  </div>
</template>

<script setup>
import { useRouter } from "vue-router";
import Menubar from "primevue/menubar";

const router = useRouter();
const menuItems = [
  { label: "Repositories", icon: "pi pi-database", command: () => router.push("/") },
];
</script>

<style scoped>
.brand {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  margin-right: 1rem;
  font-weight: 700;
  color: inherit;
  text-decoration: none;
}
</style>
