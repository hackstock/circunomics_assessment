<template>
  <div v-if="loading || error || warning || empty" class="status">
    <Message v-if="loading" severity="info" :closable="false">
      <span class="status-row">
        <ProgressSpinner strokeWidth="4" style="width: 1.5rem; height: 1.5rem" />
        Loading…
      </span>
    </Message>
    <Message v-else-if="error" severity="error" :closable="false">{{ error }}</Message>
    <Message v-else-if="warning" severity="warn" :closable="false">{{ warning }}</Message>
    <Message v-else-if="empty" severity="secondary" :closable="false">{{ empty }}</Message>
  </div>
</template>

<script setup>
import Message from "primevue/message";
import ProgressSpinner from "primevue/progressspinner";

defineProps({
  loading: { type: Boolean, default: false },
  error: { type: String, default: "" },
  warning: { type: String, default: "" },
  empty: { type: String, default: "" },
});
</script>

<style scoped>
.status {
  margin-bottom: 1rem;
}

.status-row {
  display: inline-flex;
  align-items: center;
  gap: 0.75rem;
}
</style>
