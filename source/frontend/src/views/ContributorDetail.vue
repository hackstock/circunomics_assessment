<template>
  <section>
    <Button
      link
      icon="pi pi-arrow-left"
      label="Contributors"
      class="back-link"
      @click="router.push(`/repos/${id}`)"
    />
    <div class="page-header">
      <div>
        <h1>Commits</h1>
        <p class="field-label">Each SHA opens the commit on GitHub.</p>
      </div>
    </div>

    <StatusBanner :loading="loading" :error="error" :empty="emptyMessage" />

    <DataTable
      v-if="!loading && items.length"
      lazy
      :value="items"
      dataKey="sha"
      stripedRows
      paginator
      :rows="meta.page_size"
      :totalRecords="meta.total"
      :first="(meta.page - 1) * meta.page_size"
      @page="onPage"
    >
      <Column header="SHA">
        <template #body="{ data }">
          <a class="table-link" :href="data.html_url" target="_blank" rel="noreferrer">
            {{ data.sha.slice(0, 7) }}
            <i class="pi pi-external-link" />
          </a>
        </template>
      </Column>
      <Column field="author_name" header="Author" />
      <Column header="Date">
        <template #body="{ data }">{{ formatDate(data.committed_at) }}</template>
      </Column>
    </DataTable>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import Button from "primevue/button";
import DataTable from "primevue/datatable";
import Column from "primevue/column";
import StatusBanner from "../components/StatusBanner.vue";
import { listContributorCommits } from "../api";

const props = defineProps({
  id: { type: String, required: true },
  contributorKey: { type: String, required: true },
});
const router = useRouter();

const items = ref([]);
const meta = ref({ page: 1, page_size: 20, total: 0 });
const loading = ref(false);
const error = ref("");

const emptyMessage = computed(() =>
  !loading.value && !error.value && items.value.length === 0
    ? "No commits found for this contributor."
    : ""
);

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : "";
}

async function load(page) {
  loading.value = true;
  error.value = "";
  try {
    const data = await listContributorCommits(props.id, props.contributorKey, {
      page,
      page_size: 20,
    });
    items.value = data.items;
    meta.value = data.meta;
  } catch (err) {
    error.value = err.message;
    items.value = [];
  } finally {
    loading.value = false;
  }
}

function onPage(event) {
  load(Math.floor(event.first / event.rows) + 1);
}

onMounted(() => load(1));
</script>

<style scoped>
.back-link {
  padding-left: 0;
  margin-bottom: 0.5rem;
}
</style>
