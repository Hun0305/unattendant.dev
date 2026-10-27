/* 상태 띠와 통계 탭이 /status.json을 읽어 채운다. 형식은 site/README.md "status.json".
   인라인 스크립트를 없애 Content-Security-Policy에서 script-src 'self'만 허용하려고 외부 파일로 뺐다(2026-10-27).
   head.html이 fingerprint를 붙여 defer로 불러온다 */
(function () {
  var STALE_MS = 30 * 60 * 1000;
  var lang = document.documentElement.lang;
  /* 화면 문구는 언어별로 띠 요소의 data-t-* 속성에 있다(status-band.html) */
  var band = document.querySelector("[data-status]");
  function t(key) { return band ? band.getAttribute("data-t-" + key) || "" : ""; }
  var fmt = {
    unattended_days: function (v) { return Number(v).toLocaleString(lang); },
    cpu_temp_c: function (v) { return Number(v).toFixed(1) + "°C"; },
    cost_today_krw: function (v) { return "₩" + Math.round(v).toLocaleString(lang); },
    mem: function (s) { return s.mem_used_gb.toFixed(1) + " / " + s.mem_total_gb.toFixed(1) + "GB"; },
    uptime_s: function (v) {
      var d = Math.floor(v / 86400), h = Math.floor(v % 86400 / 3600);
      return lang === "ko" ? d + "일 " + h + "시간" : d + "d " + h + "h";
    },
    disk_free_pct: function (v) { return Math.round(v) + "%"; },
    updated_time: function (v) { return new Date(v).toLocaleTimeString(lang, { hour: "2-digit", minute: "2-digit", hour12: false }); },
    updated: function (v) { return new Date(v).toLocaleString(lang, { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" }); }
  };
  fetch("/status.json", { cache: "no-store" })
    .then(function (r) { if (!r.ok) throw r.status; return r.json(); })
    .then(function (s) {
      var stale = !s.updated || Date.now() - new Date(s.updated).getTime() > STALE_MS;
      document.querySelectorAll("[data-k]").forEach(function (el) {
        var k = el.getAttribute("data-k");
        var v = k === "mem" ? (s.mem_used_gb != null && s.mem_total_gb != null ? s : null) : k === "updated_time" ? s.updated : s[k];
        var wrap = el.closest("[data-k-wrap]") || el.parentElement;
        if (v == null) { wrap.hidden = true; return; }
        wrap.hidden = false;
        el.textContent = fmt[k] ? fmt[k](v) : v;
      });
      document.querySelectorAll("[data-status-stats]").forEach(function (el) { el.hidden = false; });
      document.querySelectorAll("[data-status-idle]").forEach(function (el) {
        var until = el.getAttribute("data-keep-until");
        if (stale) { el.textContent = el.getAttribute("data-stale") || t("stale"); }
        else if (until && s[until] == null) { /* 그 값이 아직 없다(무인 운영 전): 안내를 그대로 둔다 */ }
        else { el.hidden = true; }
      });
      document.querySelectorAll("[data-status-dot]").forEach(function (el) {
        el.setAttribute("data-state", stale ? "stale" : "ok");
      });
    })
    .catch(function () {
      /* status.json이 아직 없다: 운영 준비 중 그대로. 통계 탭은 "불러오는 중"을 실패 안내로 바꾼다
         (실패 문구를 HTML에 미리 두면 검색엔진이 오류 페이지(Soft 404)로 볼 수 있다) */
      document.querySelectorAll("[data-fail]").forEach(function (el) { el.textContent = el.getAttribute("data-fail"); });
    });
})();
