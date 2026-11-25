// Live visitor count for theguybile.com.
// GET /api/visits -> {"count": N}. Reads the GoatCounter API (key kept as the
// Worker secret GC_TOKEN) and caches the answer for 60 seconds at the edge.
// Every other request is served from the static assets in dist/.
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname !== "/api/visits") return env.ASSETS.fetch(request);
    if (!env.GC_TOKEN) return new Response("not configured", { status: 404 });

    const cache = caches.default;
    const key = new Request(url.origin + "/api/visits");
    const hit = await cache.match(key);
    if (hit) return hit;

    const end = new Date(Date.now() + 864e5).toISOString().slice(0, 10);
    const r = await fetch(
      `https://${env.GC_CODE}.goatcounter.com/api/v0/stats/total?start=2020-01-01&end=${end}`,
      { headers: { Authorization: "Bearer " + env.GC_TOKEN, Accept: "application/json" } }
    );
    if (!r.ok) return new Response("upstream " + r.status, { status: 502 });
    const j = await r.json();
    const res = new Response(JSON.stringify({ count: j.total }), {
      headers: { "content-type": "application/json", "cache-control": "public, max-age=60" },
    });
    await cache.put(key, res.clone());
    return res;
  },
};
