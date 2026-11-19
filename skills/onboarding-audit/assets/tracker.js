// Prefilled "new issue" links for GitHub, Linear and Jira, built in the reader's browser.
// Mirrors onboarding_audit/trackers.py: same body layout, same hidden key, same 2,000-character limit.
(function (root) {
  var MAX_URL = 2000;
  var NAMES = { github: "GitHub", linear: "Linear", jira: "Jira" };

  function enc(params) {
    return params.map(function (p) { return encodeURIComponent(p[0]) + "=" + encodeURIComponent(p[1]); }).join("&");
  }

  function sections(f, level) {
    var s = [["Steps", f.steps || "See the report for the exact screen."], ["Expected", f.expected], ["Actual", f.actual]]
      .filter(function (x) { return x[1]; });
    if (f.fix && level < 1) s.push(["Fix idea", f.fix]);
    if (level >= 2) s = [["Actual", f.actual.slice(0, 600)]];
    if (level >= 3) s = [];
    return s;
  }

  function md(f, ctx, level) {
    var link = ctx.reportUrl + "#finding-" + f.n;
    var out = ["**Severity:** " + f.severity + " · **Confidence:** " + f.confidence,
               "**Found by:** signup audit, " + ctx.month + " ([report with screenshot](" + link + "))"];
    sections(f, level).forEach(function (x) { out.push("", "**" + x[0] + "**", x[1]); });
    if (level >= 3) out.push("", "Details and screenshot are in the report.");
    out.push("", "<!-- signup-audit-key: " + f.key + " -->");
    return out.join("\n");
  }

  function jiraText(f, ctx, level) {
    var link = ctx.reportUrl + "#finding-" + f.n;
    var out = ["*Severity:* " + f.severity + " | *Confidence:* " + f.confidence,
               "*Found by:* signup audit, " + ctx.month + " ([report with screenshot|" + link + "])"];
    sections(f, level).forEach(function (x) { out.push("", "*" + x[0] + "*", x[1]); });
    if (level >= 3) out.push("", "Details and screenshot are in the report.");
    out.push("", "signup-audit-key: " + f.key);
    return out.join("\n");
  }

  function fit(build) {
    for (var level = 0; level < 4; level++) {
      var u = build(level);
      if (u.length <= MAX_URL) return u;
    }
    return build(3);
  }

  function labels(cfg, dflt) {
    return (cfg.labels || dflt).split(",").map(function (l) { return l.trim(); }).filter(Boolean);
  }

  var builders = {
    github: function (f, ctx, cfg) {
      var repo = (cfg.repo || "").trim().replace(/^https?:\/\/github\.com\//, "").replace(/\/$/, "");
      if (!/^[\w.-]+\/[\w.-]+$/.test(repo)) throw new Error("Enter the repository as owner/name");
      return fit(function (lv) {
        return "https://github.com/" + repo + "/issues/new?" + enc([["title", "[Audit] " + f.title], ["body", md(f, ctx, lv)], ["labels", labels(cfg, "bug,signup-audit").join(",")]]);
      });
    },
    linear: function (f, ctx, cfg) {
      var team = (cfg.team || "").trim();
      var base = team ? "https://linear.app/team/" + encodeURIComponent(team) + "/new" : "https://linear.new";
      var link = ctx.reportUrl + "#finding-" + f.n;
      return fit(function (lv) {
        return base + "?" + enc([["title", "[Audit] " + f.title], ["description", md(f, ctx, lv)], ["labels", labels(cfg, "Bug,signup-audit").join(",")],
                                  ["priority", f.severity], ["links", link + "|Signup audit report"]]);
      });
    },
    jira: function (f, ctx, cfg) {
      var site = (cfg.site || "").trim().replace(/\/$/, "");
      if (!/^https?:\/\//.test(site)) site = "https://" + site;
      if (!/^https:\/\/[\w.-]+(:\d+)?(\/[\w.-]*)*$/.test(site)) throw new Error("Enter your Jira site, like yourteam.atlassian.net");
      if (!/^\d+$/.test(String(cfg.projectId || "").trim())) throw new Error("Project ID must be a number");
      if (!/^\d+$/.test(String(cfg.issueTypeId || "").trim())) throw new Error("Issue type ID must be a number");
      var ls = labels(cfg, "signup-audit").filter(function (l) { return l.indexOf(" ") < 0; });
      return fit(function (lv) {
        var p = [["pid", String(cfg.projectId).trim()], ["issuetype", String(cfg.issueTypeId).trim()], ["summary", "[Audit] " + f.title], ["description", jiraText(f, ctx, lv)]];
        ls.forEach(function (l) { p.push(["labels", l]); });
        return site + "/secure/CreateIssueDetails!init.jspa?" + enc(p);
      });
    }
  };

  root.AuditTracker = {
    NAMES: NAMES,
    url: function (type, f, ctx, cfg) {
      if (!builders[type]) throw new Error("Unknown tracker");
      return builders[type](f, ctx, cfg);
    }
  };
})(typeof window !== "undefined" ? window : globalThis);
