<template>
  <section>
    <Button
      link
      icon="pi pi-arrow-left"
      label="Repositories"
      class="back-link"
      @click="router.push('/')"
    />
    <div class="page-header">
      <div>
        <h1>Contributors</h1>
        <p class="field-label">{{ repoLabel || "Loading repository…" }}</p>
      </div>
    </div>

    <Card class="filter-card">
      <template #content>
        <form class="toolbar-row" @submit.prevent="load(1)">
          <div class="field grow">
            <label class="field-label" for="search">Search</label>
            <InputText id="search" v-model="q" placeholder="Name or email" class="w-full" />
          </div>
          <div class="field">
            <label class="field-label">Since</label>
            <DatePicker v-model="since" dateFormat="yy-mm-dd" showIcon />
          </div>
          <div class="field">
            <label class="field-label">Until</label>
            <DatePicker v-model="until" dateFormat="yy-mm-dd" showIcon />
          </div>
          <Button type="submit" icon="pi pi-filter" label="Apply" />
        </form>
      </template>
    </Card>

    <StatusBanner :loading="loading" :error="error" :empty="emptyMessage" />

    <DataTable
      v-if="!loading && items.length"
      lazy
      :value="items"
      dataKey="key"
      stripedRows
      paginator
      :rows="meta.page_size"
      :totalRecords="meta.total"
      :first="(meta.page - 1) * meta.page_size"
      :sortField="sortField"
      :sortOrder="sortOrder"
      @page="onPage"
      @sort="onSort"
    >
      <Column field="name" header="Name" sortable>
        <template #body="{ data }">
          <router-link
            class="table-link"
            :to="`/repos/${id}/contributors/${encodeURIComponent(data.key)}`"
          >
            {{ data.name }}
          </router-link>
        </template>
      </Column>
      <Column field="email" header="Email">
        <template #body="{ data }">{{ data.email || "—" }}</template>
      </Column>
      <Column field="commit_count" header="Commits" sortable />
    </DataTable>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import Button from "primevue/button";
import Card from "primevue/card";
import DataTable from "primevue/datatable";
import Column from "primevue/column";
import DatePicker from "primevue/datepicker";
import InputText from "primevue/inputtext";
import StatusBanner from "../components/StatusBanner.vue";
import { getRepository, listContributors } from "../api";

const props = defineProps({ id: { type: String, required: true } });
const router = useRouter();

const items = ref([]);
const meta = ref({ page: 1, page_size: 20, total: 0 });
const loading = ref(false);
const error = ref("");
const repoLabel = ref("");
const q = ref("");
const since = ref(null);
const until = ref(null);
const sort = ref("commits");
const order = ref("desc");

const emptyMessage = computed(() =>
  !loading.value && !error.value && items.value.length === 0
    ? "No contributors match these filters."
    : ""
);
const sortField = computed(() => (sort.value === "name" ? "name" : "commit_count"));
const sortOrder = computed(() => (order.value === "asc" ? 1 : -1));

function formatDay(value) {
  if (!value) return "";
  const date = value instanceof Date ? value : new Date(value);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function toIsoDate(value, endOfDay) {
  const day = formatDay(value);
  if (!day) return "";
  return endOfDay ? `${day}T23:59:59` : `${day}T00:00:00`;
}

async function load(page) {
  loading.value = true;
  error.value = "";
  try {
    const data = await listContributors(props.id, {
      q: q.value,
      sort: sort.value,
      order: order.value,
      since: toIsoDate(since.value, false),
      until: toIsoDate(until.value, true),
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

function onSort(event) {
  sort.value = event.sortField === "name" ? "name" : "commits";
  order.value = event.sortOrder === 1 ? "asc" : "desc";
  load(1);
}

onMounted(async () => {
  try {
    const repo = await getRepository(props.id);
    repoLabel.value = repo.full_name;
  } catch (err) {
    error.value = err.message;
  }
  await load(1);
});
</script>

<style scoped>
.back-link {
  padding-left: 0;
  margin-bottom: 0.5rem;
}

.filter-card {
  margin-bottom: 1rem;
}

.w-full {
  width: 100%;
}
</style>
