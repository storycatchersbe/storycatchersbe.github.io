/*
 * Static-site fix for Complianz cookie consent banner.
 *
 * This site was migrated off WordPress to a static host (GitHub Pages), but
 * complianz.min.js still tries to fetch banner data from a WordPress REST
 * endpoint ("<site>/<lang>/banner?...") that no longer exists. That request
 * 404s, the plugin's XHR onload handler tries to JSON.parse the 404 error
 * page body, throws, and conditionally_show_banner() is never called -- so
 * the cookie banner stays permanently hidden and visitors can never grant
 * consent (Google Consent Mode then stays stuck on "denied" forever).
 *
 * This must load BEFORE complianz.min.js (it is not deferred, so it runs
 * during HTML parsing, ahead of complianz.min.js's deferred execution) and
 * short-circuits just that one request with a harmless empty JSON response,
 * letting the rest of complianz.min.js run exactly as it would with a real
 * (empty) server response.
 */
(function () {
	var OrigOpen = XMLHttpRequest.prototype.open;
	XMLHttpRequest.prototype.open = function (method, url) {
		this._cmplzBannerFix = typeof url === "string" && /(^|\/)banner\?/.test(url);
		return OrigOpen.apply(this, arguments);
	};

	var OrigSend = XMLHttpRequest.prototype.send;
	XMLHttpRequest.prototype.send = function () {
		if (!this._cmplzBannerFix) {
			return OrigSend.apply(this, arguments);
		}
		var xhr = this;
		var body = "{}";
		setTimeout(function () {
			Object.defineProperty(xhr, "readyState", { value: 4, configurable: true });
			Object.defineProperty(xhr, "status", { value: 200, configurable: true });
			Object.defineProperty(xhr, "statusText", { value: "OK", configurable: true });
			Object.defineProperty(xhr, "response", { value: body, configurable: true });
			Object.defineProperty(xhr, "responseText", { value: body, configurable: true });
			if (typeof xhr.onreadystatechange === "function") {
				xhr.onreadystatechange();
			}
			if (typeof xhr.onload === "function") {
				xhr.onload();
			}
		}, 0);
	};
})();
