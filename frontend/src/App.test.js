import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import { createRouter, createMemoryHistory } from "vue-router";
import App from "./App.vue";

vi.mock("./layouts/AppShell.vue", () => ({ default: { template: '<div data-testid="app-shell"><slot /></div>' } }));
vi.mock("./layouts/AuthLayout.vue", () => ({ default: { template: '<div data-testid="auth-layout"><slot /></div>' } }));

function makeRouter(meta = {}) {
  return createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/", component: { template: "<div>page</div>" }, meta }],
  });
}

describe("App layout switching", () => {
  it("renders AppShell for app layout routes", async () => {
    const router = makeRouter({ layout: "app" });
    await router.push("/");
    const wrapper = mount(App, { global: { plugins: [router] } });
    await router.isReady();
    expect(wrapper.find("[data-testid='app-shell']").exists()).toBe(true);
  });

  it("renders AuthLayout for auth layout routes", async () => {
    const router = makeRouter({ layout: "auth" });
    await router.push("/");
    const wrapper = mount(App, { global: { plugins: [router] } });
    await router.isReady();
    expect(wrapper.find("[data-testid='auth-layout']").exists()).toBe(true);
  });

  it("renders a plain div for routes with no layout meta", async () => {
    const router = makeRouter({});
    await router.push("/");
    const wrapper = mount(App, { global: { plugins: [router] } });
    await router.isReady();
    expect(wrapper.find("[data-testid='app-shell']").exists()).toBe(false);
    expect(wrapper.find("[data-testid='auth-layout']").exists()).toBe(false);
  });
});
