<template>
  <section>
    <div class="page-header">
      <div>
        <h1>Repositories</h1>
        <p class="field-label">Import a GitHub repository and browse contributor activity.</p>
      </div>
    </div>

    <Card class="import-card">
      <template #title>Add a repository</template>
      <template #content>
        <form class="toolbar-row" @submit.prevent="onAdd">
          <div class="field grow">
            <label class="field-label" for="full-name">Owner / repo</label>
            <InputText
              id="full-name"
              v-model="fullName"
              placeholder="owner/repo"
              :disabled="importing"
              class="w-full"
            />
          </div>
          <Button
            type="submit"
            icon="pi pi-download"
            :label="importing ? 'Importing…' : 'Import'"
            :loading="importing"
            :disabled="importing || !fullName.trim()"
          />
        </form>
      </template>
    </Card>

    <Message v-if="importing" severity="info" :closable="false" class="block-message">
      Importing commits from GitHub. This stays open until the most recent 1000 commits are stored, or the provider stops us.
    </Message>
    <StatusBanner :loading="loading" :error="error" :warning="warning" :empty="emptyMessage" />

    <DataTable
      v-if="!loading && repositories.length"
      :value="repositories"
      dataKey="id"
      stripedRows
      class="shadow-table"
    >
      <Column header="Repository" field="full_name">
        <template #body="{ data }">
          <router-link class="table-link" :to="`/repos/${data.id}`">{{ data.full_name }}</router-link>
        </template>
      </Column>
      <Column header="Commits" field="commit_count" />
      <Column header="Last successful sync">
        <template #body="{ data }">{{ formatDate(data.last_sync_succeeded_at) }}</template>
      </Column>
      <Column header="Status">
        <template #body="{ data }">
          <Tag :value="data.last_sync_status || 'unknown'" :severity="statusSeverity(data.last_sync_status)" />
          <div v-if="data.last_sync_error" class="status-error">{{ data.last_sync_error }}</div>
        </template>
      </Column>
      <Column header="" style="width: 9rem">
        <template #body="{ data }">
          <Button
            icon="pi pi-refresh"
            label="Re-sync"
            severity="secondary"
            size="small"
            :loading="busyId === data.id"
            :disabled="busyId === data.id || importing"
            @click="onSync(data.id)"
          />
        </template>
      </Column>
    </DataTable>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import Button from "primevue/button";
import Card from "primevue/card";
import DataTable from "primevue/datatable";
import Column from "primevue/column";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Tag from "primevue/tag";
import StatusBanner from "../components/StatusBanner.vue";
import { addRepository, listRepositories, syncRepository } from "../api";

const repositories = ref([]);
const loading = ref(false);
const error = ref("");
const warning = ref("");
const fullName = ref("");
const importing = ref(false);
const busyId = ref(null);

const emptyMessage = computed(() =>
  !loading.value && !error.value && !warning.value && repositories.value.length === 0
    ? "No repositories imported yet."
    : ""
);

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : "never";
}

function statusSeverity(status) {
  if (status === "success") return "success";
  if (status === "partial") return "warn";
  if (status === "failed") return "danger";
  return "secondary";
}

function applySyncResult(result) {
  const message = result.message || "";
  if (!message) {
    warning.value = "";
    return;
  }
  if (result.repository?.last_sync_status === "partial") {
    warning.value = message;
    error.value = "";
  } else {
    error.value = message;
    warning.value = "";
  }
}

async function refresh() {
  loading.value = true;
  error.value = "";
  try {
    repositories.value = await listRepositories();
  } catch (err) {
    error.value = err.message;
    warning.value = "";
  } finally {
    loading.value = false;
  }
}

async function onAdd() {
  importing.value = true;
  error.value = "";
  warning.value = "";
  try {
    const result = await addRepository(fullName.value.trim());
    fullName.value = "";
    await refresh();
    applySyncResult(result);
  } catch (err) {
    error.value = err.message;
    warning.value = "";
  } finally {
    importing.value = false;
  }
}

async function onSync(id) {
  busyId.value = id;
  error.value = "";
  warning.value = "";
  try {
    const result = await syncRepository(id);
    await refresh();
    applySyncResult(result);
  } catch (err) {
    error.value = err.message;
    warning.value = "";
  } finally {
    busyId.value = null;
  }
}

onMounted(refresh);
</script>

<style scoped>
.import-card {
  margin-bottom: 1rem;
}

.w-full {
  width: 100%;
}

.block-message {
  margin-bottom: 1rem;
}

.shadow-table {
  background: var(--p-surface-0);
}
</style>
