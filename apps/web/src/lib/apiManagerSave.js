export async function saveApiWithFallback({
  payload,
  saveApiToServer,
  storage,
  storageKey,
}) {
  let serverResult;
  try {
    serverResult = await saveApiToServer(payload);
  } catch (error) {
    serverResult = { ok: false, error };
  }

  if (serverResult && serverResult.ok) {
    return { ok: true, target: "server", data: serverResult.data ?? null };
  }

  storage.setItem(storageKey, JSON.stringify(payload));
  return { ok: true, target: "local", error: serverResult?.error ?? null };
}
