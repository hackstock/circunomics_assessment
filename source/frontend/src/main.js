import { createApp } from "vue";
import { createRouter, createWebHistory } from "vue-router";
import PrimeVue from "primevue/config";
import Aura from "@primeuix/themes/aura";
import "primeicons/primeicons.css";
import App from "./App.vue";
import Repositories from "./views/Repositories.vue";
import Contributors from "./views/Contributors.vue";
import ContributorDetail from "./views/ContributorDetail.vue";
import "./styles.css";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: Repositories },
    { path: "/repos/:id", component: Contributors, props: true },
    {
      path: "/repos/:id/contributors/:contributorKey",
      component: ContributorDetail,
      props: true,
    },
  ],
});

const app = createApp(App);
app.use(router);
app.use(PrimeVue, {
  theme: {
    preset: Aura,
    options: { darkModeSelector: false },
  },
});
app.mount("#app");
