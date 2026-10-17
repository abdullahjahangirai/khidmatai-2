/* ================================================================
   KhidmatAI — Organization Dashboard (org.js)
   Real FastAPI org APIs: /api/org/me · /api/org/posts
   Session is stored as "kai_org" in localStorage; every request
   carries the X-Org-Email header.
   ================================================================ */
(function () {
  "use strict";

  /* ---------- Session guard ---------- */
  var org = null;
  try { org = JSON.parse(localStorage.getItem("kai_org") || "null"); } catch (e) { org = null; }
  if (!org || !org.email) {
    location.replace("/login");
    return;
  }

  /* ---------- Helpers ---------- */
  function byId(id) { return document.getElementById(id); }
  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }
  function truncate(text, max) {
    var s = String(text || "");
    return s.length > max ? s.slice(0, max).trimEnd() + "…" : s;
  }
  function prettyDate(iso) {
    if (!iso) return "—";
    var d = new Date(iso);
    if (isNaN(d.getTime())) return "—";
    return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  }

  var toastTimer = null;
  function showToast(message) {
    var t = byId("orgToast");
    if (!t) return;
    t.textContent = message;
    t.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.classList.remove("show"); }, 2600);
  }

  /* Session expired / suspended / rejected → back to login with a note. */
  function sessionInvalid(detail) {
    localStorage.removeItem("kai_org");
    try {
      sessionStorage.setItem("kh_auth_notice",
        detail || "Your organization session has ended. Please sign in again.");
    } catch (e) { /* ignore */ }
    location.replace("/login");
  }

  async function api(path, options) {
    var opts = Object.assign({ headers: {} }, options || {});
    opts.headers["X-Org-Email"] = org.email;
    var tok = localStorage.getItem("kai_org_token");
    if (tok) opts.headers["X-Org-Token"] = tok;
    if (opts.body && typeof opts.body === "object") {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(opts.body);
    }
    var r = await fetch(path, opts);
    if (r.status === 401 || r.status === 403) {
      var d = {};
      try { d = await r.json(); } catch (e) { /* non-JSON */ }
      sessionInvalid(d.detail);
      throw new Error(d.detail || "Session expired.");
    }
    return r;
  }

  /* ---------- Theme ---------- */
  var root = document.documentElement;
  function applyTheme(mode) {
    var dark = mode === "dark";
    root.classList.toggle("dark-mode", dark);
    document.body.classList.toggle("dark-mode", dark);
    var icon = byId("themeIcon");
    if (icon) icon.textContent = dark ? "☀" : "☾";
  }
  applyTheme(localStorage.getItem("khidmat-theme") || "light");
  var themeBtn = byId("themeToggle");
  if (themeBtn) {
    themeBtn.addEventListener("click", function () {
      var next = root.classList.contains("dark-mode") ? "light" : "dark";
      localStorage.setItem("khidmat-theme", next);
      applyTheme(next);
    });
  }

  /* ---------- Sidebar (mobile) ---------- */
  var sidebar = byId("dashboardSidebar");
  var sidebarToggle = byId("sidebarToggle");
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener("click", function () { sidebar.classList.toggle("open"); });
  }

  /* ---------- Section navigation ---------- */
  var SECTION_TITLES = {
    overview: "Overview",
    posts: "My Posts",
    branches: "Manage Branches",
    claims: "Claim Facility",
    profile: "Org Profile"
  };
  var sections = Array.prototype.slice.call(document.querySelectorAll(".dashboard-section"));
  var navLinks = Array.prototype.slice.call(document.querySelectorAll(".dash-nav-link[data-section]"));

  function showSection(name) {
    if (!SECTION_TITLES[name]) name = "overview";
    sections.forEach(function (s) { s.classList.toggle("active-section", s.id === name); });
    navLinks.forEach(function (l) { l.classList.toggle("active", l.dataset.section === name); });
    document.querySelectorAll(".quick-card[data-section]").forEach(function (c) {
      c.classList.toggle("active", c.dataset.section === name);
    });
    if (byId("pageTitle")) byId("pageTitle").textContent = SECTION_TITLES[name];
    history.replaceState(null, "", "#" + name);
    if (sidebar) sidebar.classList.remove("open");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  navLinks.forEach(function (link) {
    link.addEventListener("click", function (event) {
      event.preventDefault();
      showSection(this.dataset.section);
    });
  });
  document.addEventListener("click", function (event) {
    var target = event.target.closest(".quick-card[data-section]");
    if (target) {
      event.preventDefault();
      showSection(target.dataset.section);
    }
  });
  if (byId("quickViewEco")) {
    byId("quickViewEco").addEventListener("click", function () {
      window.open("/dashboard#organizations", "_blank");
    });
  }

  /* ---------- Profile dropdown ---------- */
  var profileWrap = byId("topbarProfileWrap") || document.querySelector(".topbar-profile");
  var profileBtn = byId("topbarProfileBtn");
  var profileDropdown = byId("topbarDropdown");
  function closeProfileDropdown() {
    if (profileDropdown) profileDropdown.classList.remove("open");
    if (profileBtn) profileBtn.setAttribute("aria-expanded", "false");
  }
  if (profileBtn && profileDropdown) {
    profileBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      var open = profileDropdown.classList.toggle("open");
      profileBtn.setAttribute("aria-expanded", String(open));
    });
    profileDropdown.addEventListener("click", function (e) { e.stopPropagation(); });
    document.addEventListener("click", closeProfileDropdown);
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeProfileDropdown(); });
    if (byId("dropdownProfile")) byId("dropdownProfile").addEventListener("click", function () { closeProfileDropdown(); showSection("profile"); });
    if (byId("dropdownLogout")) byId("dropdownLogout").addEventListener("click", function () { closeProfileDropdown(); doLogout(); });
  }

  /* ---------- Logout ---------- */
  function doLogout() {
    localStorage.removeItem("kai_org");
    location.replace("/");
  }
  if (byId("logoutBtn")) byId("logoutBtn").addEventListener("click", doLogout);
  if (byId("logoutBtn2")) byId("logoutBtn2").addEventListener("click", doLogout);

  /* =====================
     ORG PROFILE
     ===================== */
  var postsCache = [];

  function fillProfile(o) {
    if (byId("orgWelcomeTitle")) byId("orgWelcomeTitle").textContent = "Welcome, " + (o.name || "Organization");
    if (byId("sidebarOrgName")) byId("sidebarOrgName").textContent = truncate(o.name || "Organization", 22);
    if (byId("sidebarOrgEmail")) byId("sidebarOrgEmail").textContent = o.email || "";
    if (byId("topbarOrgName")) byId("topbarOrgName").textContent = truncate(o.name || "Organization", 20);
    if (byId("topbarOrgType")) byId("topbarOrgType").textContent = o.org_type || "";
    if (byId("dropdownOrgName")) byId("dropdownOrgName").textContent = o.name || "Organization";
    if (byId("dropdownOrgEmail")) byId("dropdownOrgEmail").textContent = o.email || "";
    var initial = (o.name || "O").trim().charAt(0).toUpperCase();
    if (byId("sidebarOrgAvatar")) byId("sidebarOrgAvatar").textContent = initial;
    if (byId("topbarOrgAvatar")) byId("topbarOrgAvatar").textContent = initial;

    var fields = {
      orgName: o.name, orgType: o.org_type, orgContact: o.contact,
      orgWebsite: o.website, orgCity: o.city, orgProvince: o.province,
      orgAddress: o.address, orgServices: o.services,
      orgHours: o.opening_hours, orgPricing: o.pricing,
      orgDiscount: o.discount, orgDescription: o.description
    };
    Object.keys(fields).forEach(function (id) {
      var input = byId(id);
      if (input && fields[id] !== undefined && fields[id] !== null) {
        if (input.tagName === "SELECT") {
          var match = Array.prototype.some.call(input.options, function (opt) { return opt.value === fields[id]; });
          input.value = match ? fields[id] : input.options[0] ? input.options[0].value : "";
        } else {
          input.value = fields[id];
        }
      }
    });

    if (byId("orgEmailRo")) byId("orgEmailRo").textContent = o.email || "—";
    if (byId("orgStatusRo")) {
      var statusEl = byId("orgStatusRo");
      statusEl.textContent = "";
      var chip = el("span", "chip chip-" + (o.status || "pending"), o.status || "pending");
      statusEl.appendChild(chip);
    }
    if (byId("orgSinceRo")) byId("orgSinceRo").textContent = prettyDate(o.submitted_at);
    if (byId("orgReviewedRo")) byId("orgReviewedRo").textContent = prettyDate(o.reviewed_at);

    var badge = byId("orgVerifiedBadge");
    if (badge) badge.style.display = o.status === "approved" ? "inline-flex" : "none";

    var preview = byId("orgLogoPreview");
    if (preview) {
      if (o.logo_url) { preview.src = o.logo_url; preview.style.display = ""; }
      else { preview.removeAttribute("src"); preview.style.display = "none"; }
    }
  }

  async function loadOrg() {
    try {
      var r = await api("/api/org/me");
      if (!r.ok) return;
      var d = await r.json();
      org = d.organization || org;
      try { localStorage.setItem("kai_org", JSON.stringify(org)); } catch (e) { /* private mode */ }
      fillProfile(org);
    } catch (e) { /* sessionInvalid already handled */ }
  }

  var saveProfileBtn = byId("saveProfileBtn");
  if (saveProfileBtn) {
    saveProfileBtn.addEventListener("click", async function () {
      var name = byId("orgName") ? byId("orgName").value.trim() : "";
      if (!name) { showToast("Organization name cannot be empty."); return; }
      saveProfileBtn.disabled = true;
      try {
        var r = await api("/api/org/me", {
          method: "PUT",
          body: {
            name: name,
            org_type: byId("orgType") ? byId("orgType").value : "",
            contact: byId("orgContact") ? byId("orgContact").value.trim() : "",
            address: byId("orgAddress") ? byId("orgAddress").value.trim() : "",
            province: byId("orgProvince") ? byId("orgProvince").value : "",
            description: byId("orgDescription") ? byId("orgDescription").value.trim() : "",
            website: byId("orgWebsite") ? byId("orgWebsite").value.trim() : "",
            city: byId("orgCity") ? byId("orgCity").value.trim() : "",
            services: byId("orgServices") ? byId("orgServices").value.trim() : "",
            opening_hours: byId("orgHours") ? byId("orgHours").value.trim() : "",
            pricing: byId("orgPricing") ? byId("orgPricing").value : "Free",
            discount: byId("orgDiscount") ? byId("orgDiscount").value.trim() : ""
          }
        });
        var d = {};
        try { d = await r.json(); } catch (e) { /* non-JSON */ }
        if (!r.ok) throw new Error(d.detail || "Could not save profile.");
        org = d.organization || org;
        try { localStorage.setItem("kai_org", JSON.stringify(org)); } catch (e) { /* ignore */ }
        fillProfile(org);
        showToast("Organization profile updated.");
      } catch (err) {
        showToast((err && err.message) || "Could not save profile.");
      }
      saveProfileBtn.disabled = false;
    });
  }

  /* =====================
     LOGO UPLOAD
     ===================== */
  var logoInput = byId("orgLogoInput");
  var logoPreview = byId("orgLogoPreview");
  var logoStatus = byId("orgLogoStatus");
  if (logoInput) {
    logoInput.addEventListener("change", async function () {
      var file = logoInput.files && logoInput.files[0];
      if (!file) return;
      if (!/\.(png|jpe?g|webp|gif)$/i.test(file.name)) {
        if (showToast) showToast("Please choose a PNG, JPG, WEBP or GIF image.");
        logoInput.value = "";
        return;
      }
      if (file.size > 4 * 1024 * 1024) {
        if (showToast) showToast("Image is larger than 4 MB.");
        logoInput.value = "";
        return;
      }
      var fd = new FormData();
      fd.append("file", file);
      if (logoStatus) logoStatus.textContent = "Uploading\u2026";
      logoInput.disabled = true;
      try {
        var r = await fetch("/api/org/logo", {
          method: "POST",
          headers: { "X-Org-Email": org.email },
          body: fd
        });
        var d = {};
        try { d = await r.json(); } catch (e) { /* non-JSON */ }
        if (!r.ok) throw new Error(d.detail || "Upload failed.");
        if (logoPreview) { logoPreview.src = d.logo_url; logoPreview.style.display = ""; }
        if (logoStatus) logoStatus.textContent = "Logo uploaded.";
        org.logo_url = d.logo_url;
        try { localStorage.setItem("kai_org", JSON.stringify(org)); } catch (e) { /* ignore */ }
      } catch (err) {
        if (showToast) showToast((err && err.message) || "Could not upload logo.");
        if (logoStatus) logoStatus.textContent = "Upload failed \u2014 try again.";
      }
      logoInput.disabled = false;
    });
  }

  /* =====================
     MY POSTS
     ===================== */
  function statusChip(status) {
    return el("span", "chip chip-" + (status || "pending"), status || "pending");
  }
  function pricingChip(pricing) {
    var p = String(pricing || "Free").toLowerCase();
    var cls = p === "free" ? "chip-free" : (p === "paid" ? "chip-paid" : "chip-subsidized");
    return el("span", "chip " + cls, pricing || "Free");
  }

  function postCard(post) {
    var card = el("div", "org-post-card");

    var head = el("div", "org-post-head");
    var titleWrap = el("div");
    titleWrap.appendChild(el("h3", null, post.title || "Post"));
    var chips = el("div", "org-post-chips");
    chips.appendChild(statusChip(post.status));
    chips.appendChild(el("span", "chip chip-neutral", post.post_type || "Program"));
    chips.appendChild(el("span", "chip chip-neutral", post.category || "General"));
    chips.appendChild(pricingChip(post.pricing));
    titleWrap.appendChild(chips);
    head.appendChild(titleWrap);
    head.appendChild(el("span", "section-note", prettyDate(post.created_at)));
    card.appendChild(head);

    if (post.description) {
      card.appendChild(el("p", "org-post-desc", truncate(post.description, 260)));
    }

    var meta = el("div", "org-post-meta");
    if (post.location) meta.appendChild(metaItem("fa-location-dot", post.location));
    if (post.contact) meta.appendChild(metaItem("fa-phone", post.contact));
    if (post.website && /^https?:\/\//i.test(post.website)) {
      var link = el("a");
      link.href = post.website;
      link.target = "_blank";
      link.rel = "noopener";
      link.style.cssText = "display:inline-flex;align-items:center;gap:6px;color:#0b805f;text-decoration:none;";
      var li = el("i", "fa-solid fa-arrow-up-right-from-square");
      link.appendChild(li);
      link.appendChild(document.createTextNode("Website"));
      meta.appendChild(link);
    }
    if (Array.isArray(post.eligibility) && post.eligibility.length) {
      meta.appendChild(metaItem("fa-user-check", "Eligibility: " + truncate(post.eligibility.join(" · "), 80)));
    }
    if (Array.isArray(post.documents) && post.documents.length) {
      meta.appendChild(metaItem("fa-file-lines", "Docs: " + truncate(post.documents.join(" · "), 80)));
    }
    if (meta.childNodes.length) card.appendChild(meta);

    if (post.status === "rejected") {
      card.appendChild(el("p", "org-post-desc",
        "This post was not approved. Please review the details, update it and submit again."));
    }

    var actions = el("div", "org-post-actions");
    var edit = el("button", "pill-btn", "Edit");
    edit.setAttribute("data-edit-post", post.id);
    actions.appendChild(edit);
    var del = el("button", "pill-btn", "Delete");
    del.style.borderColor = "#f2c7c3";
    del.style.color = "#c0392b";
    del.setAttribute("data-delete-post", post.id);
    actions.appendChild(del);
    card.appendChild(actions);

    return card;
  }

  function metaItem(iconClass, text) {
    var span = el("span");
    var i = el("i", "fa-solid " + iconClass);
    span.appendChild(i);
    span.appendChild(document.createTextNode(text));
    return span;
  }

  function renderStats(posts) {
    var counts = { approved: 0, pending: 0, rejected: 0 };
    posts.forEach(function (p) {
      if (counts[p.status] !== undefined) counts[p.status]++;
    });
    if (byId("statTotalPosts")) byId("statTotalPosts").textContent = posts.length;
    if (byId("statApprovedPosts")) byId("statApprovedPosts").textContent = counts.approved;
    if (byId("statPendingPosts")) byId("statPendingPosts").textContent = counts.pending;
    if (byId("statRejectedPosts")) byId("statRejectedPosts").textContent = counts.rejected;
  }

  async function loadPosts() {
    var list = byId("orgPostsList");
    if (!list) return;
    list.innerHTML = "";
    list.appendChild(el("p", "section-note", "Loading your posts…"));
    try {
      var r = await api("/api/org/posts");
      if (!r.ok) throw new Error("Could not load posts.");
      var d = await r.json();
      postsCache = d.posts || [];
      renderStats(postsCache);
      list.innerHTML = "";
      if (!postsCache.length) {
        var empty = el("div", "empty-list",
          "You have not published any posts yet. Click “New post” to announce a welfare program, scholarship, healthcare service, training or event.");
        list.appendChild(empty);
        return;
      }
      postsCache.forEach(function (p) { list.appendChild(postCard(p)); });
    } catch (e) {
      list.innerHTML = "";
      list.appendChild(el("div", "empty-list", "Could not load your posts. Please refresh the page."));
    }
  }

  /* ---------- Post editor modal ---------- */
  var editingPostId = null;

  function openPostModal(post) {
    editingPostId = post ? post.id : null;
    if (byId("postModalTitle")) byId("postModalTitle").textContent = post ? "Edit post" : "New post";
    if (byId("postModalSub")) {
      byId("postModalSub").textContent = post
        ? "Update your post — it will be sent back to admin verification."
        : "Publish a welfare program, event or announcement for citizens.";
    }
    var set = function (id, value) { var n = byId(id); if (n) n.value = value !== undefined && value !== null ? value : ""; };
    set("postTitle", post ? post.title : "");
    set("postDescription", post ? post.description : "");
    set("postLocation", post ? post.location : "");
    set("postContact", post ? post.contact : (org && org.contact) || "");
    set("postWebsite", post ? post.website : (org && org.website) || "");
    set("postEligibility", post && Array.isArray(post.eligibility) ? post.eligibility.join("\n") : "");
    set("postDocuments", post && Array.isArray(post.documents) ? post.documents.join("\n") : "");
    if (byId("postCategory")) byId("postCategory").value = (post && post.category && byId("postCategory").querySelector('option[value="' + post.category + '"]')) ? post.category : "Education";
    if (byId("postType")) byId("postType").value = (post && post.post_type && byId("postType").querySelector('option[value="' + post.post_type + '"]')) ? post.post_type : "Program";
    if (byId("postPricing")) byId("postPricing").value = (post && post.pricing && byId("postPricing").querySelector('option[value="' + post.pricing + '"]')) ? post.pricing : "Free";
    if (byId("postModal")) byId("postModal").style.display = "flex";
  }

  function closePostModal() {
    if (byId("postModal")) byId("postModal").style.display = "none";
    editingPostId = null;
  }

  function linesToArray(value) {
    return String(value || "").split("\n").map(function (s) { return s.trim(); }).filter(Boolean);
  }

  if (byId("newPostBtn")) byId("newPostBtn").addEventListener("click", function () { openPostModal(null); });

  document.querySelectorAll("[data-close]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var target = byId(btn.dataset.close);
      if (target) target.style.display = "none";
      if (btn.dataset.close === "postModal") editingPostId = null;
    });
  });
  var postModal = byId("postModal");
  if (postModal) {
    postModal.addEventListener("click", function (event) {
      if (event.target === postModal) closePostModal();
    });
  }
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && postModal && postModal.style.display !== "none") closePostModal();
  });

  if (byId("savePostBtn")) {
    byId("savePostBtn").addEventListener("click", async function () {
      var title = byId("postTitle") ? byId("postTitle").value.trim() : "";
      if (!title) { showToast("Please give your post a title."); return; }
      var btn = byId("savePostBtn");
      btn.disabled = true;
      var payload = {
        title: title,
        description: byId("postDescription") ? byId("postDescription").value.trim() : "",
        category: byId("postCategory") ? byId("postCategory").value : "General",
        post_type: byId("postType") ? byId("postType").value : "Program",
        eligibility: linesToArray(byId("postEligibility") ? byId("postEligibility").value : ""),
        documents: linesToArray(byId("postDocuments") ? byId("postDocuments").value : ""),
        location: byId("postLocation") ? byId("postLocation").value.trim() : "",
        contact: byId("postContact") ? byId("postContact").value.trim() : "",
        website: byId("postWebsite") ? byId("postWebsite").value.trim() : "",
        pricing: byId("postPricing") ? byId("postPricing").value : "Free"
      };
      try {
        var r = editingPostId
          ? await api("/api/org/posts/" + encodeURIComponent(editingPostId), { method: "PUT", body: payload })
          : await api("/api/org/posts", { method: "POST", body: payload });
        var d = {};
        try { d = await r.json(); } catch (e) { /* non-JSON */ }
        if (!r.ok) throw new Error(d.detail || "Could not save the post.");
        closePostModal();
        showToast(d.message || "Post submitted for admin verification.");
        loadPosts();
      } catch (err) {
        showToast((err && err.message) || "Could not save the post.");
      }
      btn.disabled = false;
    });
  }

  /* =====================
     BRANCH MANAGEMENT
     ===================== */
  var branchesCache = [];

  function branchCard(b) {
    var card = el("div", "org-post-card");
    var head = el("div", "org-post-head");
    var titleWrap = el("div");
    titleWrap.appendChild(el("h3", null, b.name || "Branch"));
    var chips = el("div", "org-post-chips");
    chips.appendChild(statusChip(b.status));
    chips.appendChild(el("span", "chip chip-neutral", b.city || "Pakistan"));
    titleWrap.appendChild(chips);
    head.appendChild(titleWrap);
    head.appendChild(el("span", "section-note", prettyDate(b.created_at)));
    card.appendChild(head);

    if (b.rejection_reason) {
      var rej = el("div", null);
      rej.style = "background:#fef2f2;border:1px solid #fecaca;padding:8px 12px;border-radius:6px;color:#dc2626;font-size:12px;margin:8px 0;";
      rej.innerHTML = "<strong>Rejection Reason:</strong> " + esc(b.rejection_reason) + " <small style='display:block;color:#666;'>Edit and re-submit to send back to review.</small>";
      card.appendChild(rej);
    }

    if (b.description) {
      card.appendChild(el("p", "org-post-desc", truncate(b.description, 260)));
    }

    var meta = el("div", "org-post-meta");
    if (b.address) meta.appendChild(metaItem("fa-location-dot", b.address));
    if (b.phone) meta.appendChild(metaItem("fa-phone", b.phone));
    if (b.opening_hours) meta.appendChild(metaItem("fa-clock", b.opening_hours));
    if (b.latitude && b.longitude) {
      meta.appendChild(metaItem("fa-map-pin", Number(b.latitude).toFixed(4) + ", " + Number(b.longitude).toFixed(4)));
    }
    card.appendChild(meta);

    var foot = el("div", "org-post-foot");
    var actions = el("div", "org-post-actions");
    var editBtn = el("button", "pill-btn", "Edit branch");
    editBtn.dataset.editBranch = b.id;
    editBtn.innerHTML = '<i class="fa-solid fa-pen"></i> Edit';
    actions.appendChild(editBtn);

    var delBtn = el("button", "pill-btn", "Delete");
    delBtn.dataset.deleteBranch = b.id;
    delBtn.innerHTML = '<i class="fa-solid fa-trash"></i> Delete';
    actions.appendChild(delBtn);

    foot.appendChild(actions);
    card.appendChild(foot);
    return card;
  }

  async function loadBranches() {
    var list = byId("orgBranchesList");
    if (!list) return;
    try {
      var r = await api("/api/org/branches");
      if (!r.ok) return;
      var d = await r.json();
      branchesCache = d.branches || [];
      list.innerHTML = "";
      if (!branchesCache.length) {
        list.innerHTML = '<p class="empty-hint">No branches added yet. Click "+ Add new branch" above to create your first location.</p>';
        return;
      }
      branchesCache.forEach(function (b) { list.appendChild(branchCard(b)); });
    } catch (e) {
      list.innerHTML = '<p class="empty-hint">Could not load branches right now.</p>';
    }
  }

  var branchModal = byId("branchModal");
  function openBranchModal(b) {
    if (!branchModal) return;
    byId("branchEditId").value = b ? b.id : "";
    byId("branchModalTitle").textContent = b ? "Edit Branch" : "Add New Branch";
    byId("branchName").value = b ? b.name : "";
    byId("branchCity").value = b ? b.city : "Karachi";
    byId("branchAddress").value = b ? b.address : "";
    byId("branchLat").value = (b && b.latitude != null) ? b.latitude : "";
    byId("branchLon").value = (b && b.longitude != null) ? b.longitude : "";
    byId("branchPhone").value = (b && b.phone) ? b.phone : "";
    byId("branchEmail").value = (b && b.email) ? b.email : "";
    byId("branchHours").value = (b && b.opening_hours) ? b.opening_hours : "";
    byId("branchPhoto").value = (b && b.photo_url) ? b.photo_url : "";
    byId("branchServices").value = (b && b.services) ? b.services : "";
    byId("branchDesc").value = (b && b.description) ? b.description : "";
    branchModal.style.display = "flex";
  }
  function closeBranchModal() {
    if (branchModal) branchModal.style.display = "none";
  }

  if (byId("newBranchBtn")) {
    byId("newBranchBtn").addEventListener("click", function () { openBranchModal(null); });
  }

  if (byId("branchGetGpsBtn")) {
    byId("branchGetGpsBtn").addEventListener("click", function () {
      if (!navigator.geolocation) { showToast("Geolocation is not supported by your browser."); return; }
      byId("branchGetGpsBtn").innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Getting GPS...';
      navigator.geolocation.getCurrentPosition(function (pos) {
        byId("branchLat").value = pos.coords.latitude.toFixed(6);
        byId("branchLon").value = pos.coords.longitude.toFixed(6);
        byId("branchGetGpsBtn").innerHTML = '<i class="fa-solid fa-check"></i> GPS Coordinates captured!';
        setTimeout(function () {
          if (byId("branchGetGpsBtn")) byId("branchGetGpsBtn").innerHTML = '<i class="fa-solid fa-location-crosshairs"></i> Use current GPS coordinates';
        }, 2500);
      }, function () {
        showToast("Could not retrieve GPS location. Please enter coordinates manually.");
        byId("branchGetGpsBtn").innerHTML = '<i class="fa-solid fa-location-crosshairs"></i> Use current GPS coordinates';
      });
    });
  }

  if (byId("saveBranchBtn")) {
    byId("saveBranchBtn").addEventListener("click", async function () {
      var editId = byId("branchEditId").value.trim();
      var name = byId("branchName").value.trim();
      var city = byId("branchCity").value.trim();
      var address = byId("branchAddress").value.trim();
      var latVal = byId("branchLat").value.trim();
      var lonVal = byId("branchLon").value.trim();

      if (!name) { showToast("Branch name is required."); return; }
      if (!address) { showToast("Branch address is required."); return; }

      var payload = {
        name: name,
        city: city,
        address: address,
        latitude: latVal ? parseFloat(latVal) : null,
        longitude: lonVal ? parseFloat(lonVal) : null,
        phone: byId("branchPhone").value.trim(),
        email: byId("branchEmail").value.trim(),
        opening_hours: byId("branchHours").value.trim(),
        photo_url: byId("branchPhoto").value.trim(),
        services: byId("branchServices").value.trim(),
        description: byId("branchDesc").value.trim(),
        is_public: true
      };

      var btn = byId("saveBranchBtn");
      btn.disabled = true;
      try {
        var r = editId
          ? await api("/api/org/branches/" + encodeURIComponent(editId), { method: "PUT", body: payload })
          : await api("/api/org/branches", { method: "POST", body: payload });
        var d = await r.json();
        if (!r.ok) throw new Error(d.detail || "Could not save branch.");
        closeBranchModal();
        showToast(d.message || "Branch saved successfully.");
        loadBranches();
      } catch (err) {
        showToast((err && err.message) || "Could not save branch.");
      }
      btn.disabled = false;
    });
  }

  /* =====================
     FACILITY CLAIMS
     ===================== */
  var claimsCache = [];

  function claimCard(c) {
    var card = el("div", "org-post-card");
    var head = el("div", "org-post-head");
    var titleWrap = el("div");
    titleWrap.appendChild(el("h3", null, c.facility_name || ("Facility: " + c.facility_id)));
    var chips = el("div", "org-post-chips");
    chips.appendChild(statusChip(c.status));
    titleWrap.appendChild(chips);
    head.appendChild(titleWrap);
    head.appendChild(el("span", "section-note", prettyDate(c.created_at)));
    card.appendChild(head);

    if (c.explanation) {
      var exp = el("p", "org-post-desc");
      exp.innerHTML = "<strong>Justification:</strong> " + esc(c.explanation);
      card.appendChild(exp);
    }
    if (c.admin_notes) {
      var note = el("div", null);
      note.style = "background:#f8fafc;border:1px solid #e2e8f0;padding:8px 12px;border-radius:6px;font-size:12px;margin:8px 0;";
      note.innerHTML = "<strong>Admin Note:</strong> " + esc(c.admin_notes);
      card.appendChild(note);
    }
    if (c.rejection_reason) {
      var rej = el("div", null);
      rej.style = "background:#fef2f2;border:1px solid #fecaca;padding:8px 12px;border-radius:6px;color:#dc2626;font-size:12px;margin:8px 0;";
      rej.innerHTML = "<strong>Rejection Reason:</strong> " + esc(c.rejection_reason);
      card.appendChild(rej);
    }

    if (c.status === "pending") {
      var foot = el("div", "org-post-foot");
      var actions = el("div", "org-post-actions");
      var cancelBtn = el("button", "pill-btn", "Cancel request");
      cancelBtn.dataset.cancelClaim = c.id;
      cancelBtn.innerHTML = '<i class="fa-solid fa-ban"></i> Cancel claim';
      actions.appendChild(cancelBtn);
      foot.appendChild(actions);
      card.appendChild(foot);
    }
    return card;
  }

  async function loadClaims() {
    var list = byId("orgClaimsList");
    if (!list) return;
    try {
      var r = await api("/api/org/claims");
      if (!r.ok) return;
      var d = await r.json();
      claimsCache = d.claims || [];
      list.innerHTML = "";
      if (!claimsCache.length) {
        list.innerHTML = '<p class="empty-hint">You have not submitted any facility claims yet.</p>';
        return;
      }
      claimsCache.forEach(function (c) { list.appendChild(claimCard(c)); });
    } catch (e) {
      list.innerHTML = '<p class="empty-hint">Could not load claims right now.</p>';
    }
  }

  async function loadFacilitiesForClaim() {
    var sel = byId("claimFacilitySelect");
    if (!sel) return;
    try {
      var r1 = await fetch("/api/facilities?city=all&category=all");
      var d1 = await r1.json();
      var facs = d1.facilities || [];
      try {
        var r2 = await fetch("/api/facilities/db?city=all&category=all");
        var d2 = await r2.json();
        facs = facs.concat(d2.facilities || []);
      } catch (e) { }

      sel.innerHTML = '<option value="">-- Choose an existing facility --</option>';
      facs.forEach(function (f) {
        var opt = document.createElement("option");
        opt.value = f.id;
        opt.textContent = f.name + " (" + (f.city || "Pakistan") + " — " + (f.facility_type || f.category) + ")";
        sel.appendChild(opt);
      });
    } catch (e) { }
  }

  if (byId("submitClaimBtn")) {
    byId("submitClaimBtn").addEventListener("click", async function () {
      var facId = byId("claimFacilitySelect").value;
      var exp = byId("claimExplanation").value.trim();
      var doc = byId("claimDoc").value.trim();

      if (!facId) { showToast("Please select a facility to claim."); return; }
      if (!exp || exp.length < 10) { showToast("Please provide a detailed justification (at least 10 characters)."); return; }

      var btn = byId("submitClaimBtn");
      btn.disabled = true;
      try {
        var r = await api("/api/org/claims", {
          method: "POST",
          body: { facility_id: facId, explanation: exp, verification_doc: doc }
        });
        var d = await r.json();
        if (!r.ok) throw new Error(d.detail || "Could not submit claim.");
        showToast(d.message || "Claim submitted for admin review.");
        byId("claimExplanation").value = "";
        byId("claimDoc").value = "";
        byId("claimFacilitySelect").value = "";
        loadClaims();
      } catch (err) {
        showToast((err && err.message) || "Could not submit claim.");
      }
      btn.disabled = false;
    });
  }

  /* ---------- Delegated actions (posts / branches / claims / modals) ---------- */
  document.addEventListener("click", function (event) {
    var editBtn = event.target.closest("[data-edit-post]");
    if (editBtn) {
      var post = postsCache.find(function (p) { return p.id === editBtn.dataset.editPost; });
      if (post) openPostModal(post);
      return;
    }
    var delBtn = event.target.closest("[data-delete-post]");
    if (delBtn) {
      var id = delBtn.dataset.deletePost;
      if (!window.confirm("Delete this post permanently?")) return;
      delBtn.disabled = true;
      api("/api/org/posts/" + encodeURIComponent(id), { method: "DELETE" })
        .then(function () { showToast("Post deleted."); loadPosts(); })
        .catch(function () { showToast("Could not delete the post."); });
      return;
    }
    var editB = event.target.closest("[data-edit-branch]");
    if (editB) {
      var b = branchesCache.find(function (x) { return x.id === editB.dataset.editBranch; });
      if (b) openBranchModal(b);
      return;
    }
    var delB = event.target.closest("[data-delete-branch]");
    if (delB) {
      var idB = delB.dataset.deleteBranch;
      if (!window.confirm("Permanently delete this branch?")) return;
      delB.disabled = true;
      api("/api/org/branches/" + encodeURIComponent(idB), { method: "DELETE" })
        .then(function () { showToast("Branch deleted."); loadBranches(); })
        .catch(function () { showToast("Could not delete branch."); });
      return;
    }
    var canC = event.target.closest("[data-cancel-claim]");
    if (canC) {
      var cId = canC.dataset.cancelClaim;
      if (!window.confirm("Cancel this pending claim?")) return;
      canC.disabled = true;
      api("/api/org/claims/" + encodeURIComponent(cId), { method: "DELETE" })
        .then(function () { showToast("Claim cancelled."); loadClaims(); })
        .catch(function () { showToast("Could not cancel claim."); });
      return;
    }
    var closeBranchM = event.target.closest("[data-close='branchModal']");
    if (closeBranchM) {
      closeBranchModal();
    }
    var closePostM = event.target.closest("[data-close='postModal']");
    if (closePostM) {
      closePostModal();
    }
  });

  /* ---------- Boot ---------- */
  fillProfile(org);
  loadOrg();
  loadPosts();
  loadBranches();
  loadClaims();
  loadFacilitiesForClaim();

  var startHash = (location.hash || "").replace("#", "");
  if (SECTION_TITLES[startHash]) showSection(startHash);
})();
