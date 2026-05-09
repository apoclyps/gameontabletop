import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App.vue";

describe("App", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ message: "Hello World" }),
      }),
    );
  });

  it("displays the API message after loading", async () => {
    const wrapper = mount(App);
    await flushPromises();
    expect(wrapper.text()).toContain("Hello World");
  });

  it("shows an error when the API call fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
      }),
    );
    const wrapper = mount(App);
    await flushPromises();
    expect(wrapper.text()).toContain("Failed to reach API");
  });
});
