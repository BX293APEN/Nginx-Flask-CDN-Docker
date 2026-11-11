/**
 * # index.js : ゲージの定期更新 (nginxが直接配信)
 *
 * | 項目 | 内容 |
 * | --- | --- |
 * | 取得先 | `GET /partials/gauges` (HTML断片) を `#gauges` に差し替える |
 * | 更新間隔 | `#gauges` の `data-interval` 属性(秒)。サーバの `REFRESH_SEC` |
 * | 失敗時 | 表示は据え置き、`#updated` に失敗を表示して次の周期で再試行する |
 * | 非表示タブ | 取得しない(戻ってきた時に即更新する) |
 *
 * ## 定数
 *
 * | 名前 | 値 | 説明 |
 * | --- | --- | --- |
 * | `PARTIAL_URL` | `"/partials/gauges"` | 取得先 |
 */
(() => {
    "use strict";

    const PARTIAL_URL = "/partials/gauges";

    const panel = document.getElementById("gauges");
    const stamp = document.getElementById("updated");
    const intervalMs = Number(panel.dataset.interval) * 1000;

    /**
     * #### 最終更新時刻を表示する
     *
     * | 引数 | 型 | 説明 |
     * | --- | --- | --- |
     * | `failed` | `boolean` | `true` なら失敗表示(赤字)にする |
     *
     * | 戻り値 | 型 | 説明 |
     * | --- | --- | --- |
     * | なし | `void` | - |
     */
    function showStamp(failed) {
        const now = new Date().toLocaleString("ja-JP");
        stamp.textContent = failed ? `更新失敗 (${now})` : `最終更新 ${now}`;
        stamp.classList.toggle("text-danger", failed);
    }

    /**
     * #### ゲージを1回更新する
     *
     * | 引数 | 型 | 説明 |
     * | --- | --- | --- |
     * | なし | - | - |
     *
     * | 戻り値 | 型 | 説明 |
     * | --- | --- | --- |
     * | 完了通知 | `Promise<void>` | 成功・失敗にかかわらず例外は投げない |
     */
    async function refresh() {
        if (document.hidden) {
            return;
        }
        try {
            const res = await fetch(PARTIAL_URL, { cache: "no-store" });
            if (!res.ok) {
                throw new Error(`HTTP ${res.status}`);
            }
            panel.innerHTML = await res.text();
            showStamp(false);
        } catch (err) {
            console.error(err);
            showStamp(true);
        }
    }

    /**
     * #### 前回の完了後に次回を予約して更新を繰り返す
     *
     * `setInterval` だと、CPU計測で応答が遅れた時にリクエストが重なるため `setTimeout` で連鎖させる。
     *
     * | 引数 | 型 | 説明 |
     * | --- | --- | --- |
     * | なし | - | - |
     *
     * | 戻り値 | 型 | 説明 |
     * | --- | --- | --- |
     * | 完了通知 | `Promise<void>` | 実際には終わらない |
     */
    async function loop() {
        await refresh();
        setTimeout(loop, intervalMs);
    }

    // 初回描画はサーバ側で済んでいるので、時刻だけ入れて次の周期から取得する
    showStamp(false);
    setTimeout(loop, intervalMs);
    document.addEventListener("visibilitychange", refresh);
})();
