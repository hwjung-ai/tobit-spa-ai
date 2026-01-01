import { test } from "node:test";
import assert from "node:assert/strict";
import { saveApiWithFallback } from "./apiManagerSave.js";

const createMemoryStorage = () => {
  const store = new Map();
  return {
    getItem(key) {
      return store.has(key) ? store.get(key) : null;
    },
    setItem(key, value) {
      store.set(key, value);
    },
  };
};

test("saveApiWithFallback uses server when available", async () => {
  const storage = createMemoryStorage();
  const saveApiToServer = async () => ({ ok: true, data: { api_id: "srv-1" } });
  const result = await saveApiWithFallback({
    payload: { api_name: "A" },
    saveApiToServer,
    storage,
    storageKey: "api-manager:api:test",
  });

  assert.equal(result.target, "server");
  assert.equal(storage.getItem("api-manager:api:test"), null);
});

test("saveApiWithFallback falls back to local storage on failure", async () => {
  const storage = createMemoryStorage();
  const saveApiToServer = async () => ({ ok: false, error: "NO_ENDPOINT" });
  const result = await saveApiWithFallback({
    payload: { api_name: "B" },
    saveApiToServer,
    storage,
    storageKey: "api-manager:api:test",
  });

  assert.equal(result.target, "local");
  assert.ok(storage.getItem("api-manager:api:test"));
});
