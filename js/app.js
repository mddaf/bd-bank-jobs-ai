/**
 * BD Bank Jobs AI — Interactive Web Application
 * Vanilla JS logic for GitHub Pages
 */

(function () {
  'use strict';

  // State Management
  const state = {
    jobs: [],
    banks: [],
    filteredJobs: [],
    filteredBanks: [],
    activeCategory: 'all',
    activeSector: 'all',
    activeSort: 'deadline_asc',
    searchQuery: '',
    bankSearchQuery: '',
    activeDirType: 'all',
  };

  // DOM Elements
  const elements = {
    circularsGrid: document.getElementById('circulars-grid'),
    emptyState: document.getElementById('empty-state'),
    resultsCountBadge: document.getElementById('results-count-badge'),
    searchInput: document.getElementById('job-search-input'),
    clearSearchBtn: document.getElementById('clear-search-btn'),
    sectorFilter: document.getElementById('sector-filter'),
    sortSelect: document.getElementById('sort-select'),
    categoryChips: document.getElementById('category-chips'),
    resetFiltersBtn: document.getElementById('reset-filters-btn'),
    statActiveJobs: document.getElementById('stat-active-jobs'),
    statInstitutions: document.getElementById('stat-institutions'),

    // Directory
    directoryGrid: document.getElementById('directory-grid'),
    bankDirectorySearch: document.getElementById('bank-directory-search'),
    directoryTabs: document.getElementById('directory-tabs'),

    // Modal
    modalBackdrop: document.getElementById('job-modal-backdrop'),
    modalCloseBtn: document.getElementById('modal-close-btn'),
    modalOrgBadge: document.getElementById('modal-org-badge'),
    modalJobTitle: document.getElementById('modal-job-title'),
    modalTags: document.getElementById('modal-tags'),
    modalBody: document.getElementById('modal-body'),
    modalFooter: document.getElementById('modal-footer'),

    // Toast & Theme
    toast: document.getElementById('toast'),
    themeToggle: document.getElementById('theme-toggle'),
  };

  /**
   * Initialize Application
   */
  async function init() {
    initTheme();
    setupEventListeners();
    await loadData();

    // Auto-poll every 20 seconds so admin changes in Telegram reflect live without manual reload
    setInterval(loadData, 20000);

    // Re-check immediately whenever user switches back to this tab
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') {
        loadData();
      }
    });
  }

  /**
   * Load JSON Data (with cache-busting & live sync)
   */
  async function loadData() {
    try {
      const cacheBuster = `?_ts=${Date.now()}`;
      const response = await fetch(`data/jobs.json${cacheBuster}`, { cache: 'no-store' });
      if (!response.ok) throw new Error('Network error');
      const data = await response.json();

      state.jobs = data.jobs || [];
      state.banks = data.banks || [];
      state.botAccessMode = data.bot_access_mode || 'private';

      if (elements.statActiveJobs) elements.statActiveJobs.textContent = state.jobs.length;
      if (elements.statInstitutions) elements.statInstitutions.textContent = `${state.banks.length}+`;

      updateCategoryChipCounts();
      applyFilters();
      renderDirectory();
      updateBotAccessModeUI(state.botAccessMode);
    } catch (err) {
      console.warn('Could not load data/jobs.json asynchronously, attempting embedded fallback...', err);
      loadEmbeddedFallback();
    }
  }

  /**
   * Fallback data in case the page is opened locally via file:///
   */
  function loadEmbeddedFallback() {
    // If running offline or without server, load live cached jobs
    state.jobs = [
      {
        id: 1,
        title: "Principal Officer (Grade-6) for Ansar VDP Unnayan Bank",
        organization: "Ansar VDP Unnayan Bank",
        url: "https://erecruitment.bb.org.bd/onlineapp/joblist.php",
        deadline: "2026-10-25",
        deadline_formatted: "25 Oct 2026",
        days_left: 18,
        category: "officer",
        category_label: "Officers & Cadre",
        source: "BB_BSCS",
        source_type: "state_owned",
        vacancies: "2",
        salary: "National Pay Scale Grade-6",
        eligibility: "Post Graduate degree / 4-year Bachelor degree from any recognized university with relevant experience.",
        ai_summary: "Official recruitment for Principal Officer (Grade-6) at Ansar VDP Unnayan Bank via BSCS.",
        ai_summary_bn: "বাংলাদেশ ব্যাংক বিএসসিএস এর মাধ্যমে আনসার ভিডিপি উন্নয়ন ব্যাংকে প্রিন্সিপাল অফিসার (গ্রেড-৬) নিয়োগ বিজ্ঞপ্তি।",
        ai_relevance_score: 0.95,
        circular_url: "https://erecruitment.bb.org.bd/career/20260616_bscs_307.pdf",
        apply_url: "https://erecruitment.bb.org.bd/onlineapp/joblist.php"
      },
      {
        id: 2,
        title: "System Manager (Grade-3) for Ansar VDP Unnayan Bank",
        organization: "Ansar VDP Unnayan Bank",
        url: "https://erecruitment.bb.org.bd/onlineapp/joblist.php",
        deadline: "2026-10-25",
        deadline_formatted: "25 Oct 2026",
        days_left: 18,
        category: "it",
        category_label: "IT & Systems",
        source: "BB_BSCS",
        source_type: "state_owned",
        vacancies: "1",
        salary: "National Pay Scale Grade-3",
        eligibility: "B.Sc in Computer Science / CSE / EEE or related discipline with minimum 12 years ICT experience.",
        ai_summary: "Executive ICT leadership vacancy for System Manager (Grade-3) at Ansar VDP Unnayan Bank.",
        ai_summary_bn: "আনসার ভিডিপি উন্নয়ন ব্যাংকে সিস্টেম ম্যানেজার (গ্রেড-৩) পদে আইসিটি নেতৃত্বমূলক নিয়োগ বিজ্ঞপ্তি।",
        ai_relevance_score: 0.92,
        circular_url: "https://erecruitment.bb.org.bd/career/20260616_bscs_307.pdf",
        apply_url: "https://erecruitment.bb.org.bd/onlineapp/joblist.php"
      },
      {
        id: 3,
        title: "Assistant Engineer (Civil) / Senior Officer (Assistant Engineer-Civil) (Grade-9)",
        organization: "Sonali Bank PLC / Combined Banks",
        url: "https://erecruitment.bb.org.bd/onlineapp/joblist.php",
        deadline: "2026-10-18",
        deadline_formatted: "18 Oct 2026",
        days_left: 11,
        category: "engineering",
        category_label: "Engineering",
        source: "BB_BSCS",
        source_type: "state_owned",
        vacancies: "8",
        salary: "National Pay Scale Grade-9",
        eligibility: "B.Sc in Civil Engineering from any recognized university with minimum two first division/class.",
        ai_summary: "Combined recruitment for Civil Engineers at Sonali Bank and participating state-owned banks.",
        ai_summary_bn: "সোনালী ব্যাংক এবং সমন্বিত রাষ্ট্রায়ত্ত ব্যাংকে সহকারী প্রকৌশলী (সিভিল) নিয়োগ বিজ্ঞপ্তি।",
        ai_relevance_score: 0.95,
        circular_url: "https://erecruitment.bb.org.bd/career/20260616_bscs_307.pdf",
        apply_url: "https://erecruitment.bb.org.bd/onlineapp/joblist.php"
      },
      {
        id: 4,
        title: "Assistant Engineer (Electrical) / Senior Officer (Grade-9)",
        organization: "Combined State Banks / BSCS",
        url: "https://erecruitment.bb.org.bd/onlineapp/joblist.php",
        deadline: "2026-10-18",
        deadline_formatted: "18 Oct 2026",
        days_left: 11,
        category: "engineering",
        category_label: "Engineering",
        source: "BB_BSCS",
        source_type: "state_owned",
        vacancies: "6",
        salary: "National Pay Scale Grade-9",
        eligibility: "B.Sc in Electrical / EEE from any recognized university.",
        ai_summary: "Official recruitment for Electrical Engineers at participating state banks.",
        ai_summary_bn: "রাষ্ট্রায়ত্ত ব্যাংকে সহকারী প্রকৌশলী (তড়িৎ) পদে নিয়োগ বিজ্ঞপ্তি।",
        ai_relevance_score: 0.95,
        circular_url: "https://erecruitment.bb.org.bd/career/20260616_bscs_307.pdf",
        apply_url: "https://erecruitment.bb.org.bd/onlineapp/joblist.php"
      },
      {
        id: 5,
        title: "Senior Officer (Law) (Grade-9)",
        organization: "Combined State Banks / BSCS",
        url: "https://erecruitment.bb.org.bd/onlineapp/joblist.php",
        deadline: "2026-10-18",
        deadline_formatted: "18 Oct 2026",
        days_left: 11,
        category: "law",
        category_label: "Law & Legal",
        source: "BB_BSCS",
        source_type: "state_owned",
        vacancies: "4",
        salary: "National Pay Scale Grade-9",
        eligibility: "LL.B (Honours) or LL.M from any recognized university with at least two first divisions.",
        ai_summary: "Legal specialist vacancy for Senior Officer (Law) across participating state banks.",
        ai_summary_bn: "রাষ্ট্রায়ত্ত ব্যাংকে সিনিয়র অফিসার (আইন) পদে নিয়োগ বিজ্ঞপ্তি।",
        ai_relevance_score: 0.90,
        circular_url: "https://erecruitment.bb.org.bd/career/20260616_bscs_307.pdf",
        apply_url: "https://erecruitment.bb.org.bd/onlineapp/joblist.php"
      },
      {
        id: 6,
        title: "Senior Officer(Audit) of Agrani Bank Limited",
        organization: "Agrani Bank PLC",
        url: "https://erecruitment.bb.org.bd/onlineapp/joblist.php",
        deadline: "2026-10-18",
        deadline_formatted: "18 Oct 2026",
        days_left: 11,
        category: "audit",
        category_label: "Audit & Accounts",
        source: "BB_BSCS",
        source_type: "state_owned",
        vacancies: "5",
        salary: "National Pay Scale Grade-9",
        eligibility: "Master degree / 4-year Bachelor degree in Accounting, Finance or Business.",
        ai_summary: "Official recruitment for Senior Officer (Audit) at Agrani Bank PLC.",
        ai_summary_bn: "অগ্রণী ব্যাংক পিএলসি-তে সিনিয়র অফিসার (অডিট) পদে নিয়োগ বিজ্ঞপ্তি।",
        ai_relevance_score: 0.92,
        circular_url: "https://erecruitment.bb.org.bd/career/20260616_bscs_307.pdf",
        apply_url: "https://erecruitment.bb.org.bd/onlineapp/joblist.php"
      },
      {
        id: 7,
        title: "Financial Analyst (Grade-9) of Karmasangsthan Bank",
        organization: "Karmasangsthan Bank",
        url: "https://erecruitment.bb.org.bd/onlineapp/joblist.php",
        deadline: "2026-10-18",
        deadline_formatted: "18 Oct 2026",
        days_left: 11,
        category: "analyst",
        category_label: "Financial Analyst",
        source: "BB_BSCS",
        source_type: "state_owned",
        vacancies: "3",
        salary: "National Pay Scale Grade-9",
        eligibility: "Master degree in Finance / Economics / Business Administration.",
        ai_summary: "Financial Analyst opening at Karmasangsthan Bank.",
        ai_summary_bn: "কর্মসংস্থান ব্যাংকে ফাইন্যান্সিয়াল অ্যানালিস্ট (গ্রেড-৯) পদে নিয়োগ বিজ্ঞপ্তি।",
        ai_relevance_score: 0.90,
        circular_url: "https://erecruitment.bb.org.bd/career/20260616_bscs_307.pdf",
        apply_url: "https://erecruitment.bb.org.bd/onlineapp/joblist.php"
      }
    ];

    if (elements.statActiveJobs) elements.statActiveJobs.textContent = state.jobs.length;
    updateCategoryChipCounts();
    applyFilters();
  }

  /**
   * Setup Event Listeners
   */
  function setupEventListeners() {
    // Search input
    if (elements.searchInput) {
      elements.searchInput.addEventListener('input', (e) => {
        state.searchQuery = e.target.value.trim().toLowerCase();
        if (elements.clearSearchBtn) {
          elements.clearSearchBtn.style.display = state.searchQuery ? 'block' : 'none';
        }
        applyFilters();
      });
    }

    if (elements.clearSearchBtn) {
      elements.clearSearchBtn.addEventListener('click', () => {
        elements.searchInput.value = '';
        state.searchQuery = '';
        elements.clearSearchBtn.style.display = 'none';
        applyFilters();
      });
    }

    // Sector Filter
    if (elements.sectorFilter) {
      elements.sectorFilter.addEventListener('change', (e) => {
        state.activeSector = e.target.value;
        applyFilters();
      });
    }

    // Sort Select
    if (elements.sortSelect) {
      elements.sortSelect.addEventListener('change', (e) => {
        state.activeSort = e.target.value;
        applyFilters();
      });
    }

    // Category Chips
    if (elements.categoryChips) {
      elements.categoryChips.addEventListener('click', (e) => {
        const chip = e.target.closest('.chip-btn');
        if (!chip) return;

        elements.categoryChips.querySelectorAll('.chip-btn').forEach(c => c.classList.remove('active'));
        chip.classList.add('active');
        state.activeCategory = chip.dataset.category || 'all';
        applyFilters();
      });
    }

    // Reset Filters
    if (elements.resetFiltersBtn) {
      elements.resetFiltersBtn.addEventListener('click', () => {
        state.searchQuery = '';
        state.activeCategory = 'all';
        state.activeSector = 'all';
        state.activeSort = 'deadline_asc';

        if (elements.searchInput) elements.searchInput.value = '';
        if (elements.clearSearchBtn) elements.clearSearchBtn.style.display = 'none';
        if (elements.sectorFilter) elements.sectorFilter.value = 'all';
        if (elements.sortSelect) elements.sortSelect.value = 'deadline_asc';

        if (elements.categoryChips) {
          elements.categoryChips.querySelectorAll('.chip-btn').forEach(c => {
            c.classList.toggle('active', c.dataset.category === 'all');
          });
        }
        applyFilters();
      });
    }

    // Directory Search
    if (elements.bankDirectorySearch) {
      elements.bankDirectorySearch.addEventListener('input', (e) => {
        state.bankSearchQuery = e.target.value.trim().toLowerCase();
        renderDirectory();
      });
    }

    // Directory Tabs
    if (elements.directoryTabs) {
      elements.directoryTabs.addEventListener('click', (e) => {
        const tab = e.target.closest('.dir-tab');
        if (!tab) return;
        elements.directoryTabs.querySelectorAll('.dir-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        state.activeDirType = tab.dataset.dirType || 'all';
        renderDirectory();
      });
    }

    // Job Modal Close
    if (elements.modalCloseBtn) {
      elements.modalCloseBtn.addEventListener('click', closeModal);
    }
    if (elements.modalBackdrop) {
      elements.modalBackdrop.addEventListener('click', (e) => {
        if (e.target === elements.modalBackdrop) closeModal();
      });
    }

    // Modal Tab Switcher (Bot Usage vs Group Invite)
    const modalTabs = document.getElementById('modal-access-tabs');
    if (modalTabs) {
      modalTabs.addEventListener('click', (e) => {
        const btn = e.target.closest('.modal-tab-btn');
        if (!btn) return;
        switchModalTab(btn.dataset.tab);
      });
    }

    // Invite Modal Triggers
    document.querySelectorAll('.private-invite-trigger').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const targetTab = btn.dataset.targetTab || 'bot';
        openInviteModal(targetTab);
      });
    });

    // Close buttons for Invite Modal
    const inviteCloseBtn = document.getElementById('invite-modal-close-btn');
    if (inviteCloseBtn) inviteCloseBtn.addEventListener('click', closeInviteModal);

    const inviteDoneBtn = document.getElementById('invite-modal-done-btn');
    if (inviteDoneBtn) inviteDoneBtn.addEventListener('click', closeInviteModal);

    const inviteBackdrop = document.getElementById('invite-modal-backdrop');
    if (inviteBackdrop) {
      inviteBackdrop.addEventListener('click', (e) => {
        if (e.target === inviteBackdrop) closeInviteModal();
      });
    }

    // Copy template buttons
    document.querySelectorAll('.copy-template-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const targetId = btn.dataset.target;
        const textarea = document.getElementById(targetId);
        if (textarea) {
          navigator.clipboard.writeText(textarea.value)
            .then(() => showToast('📋 Request message copied to clipboard!'))
            .catch(() => showToast('Please copy message text manually.'));
        }
      });
    });

    // Quick Command copy chips in public modal
    document.querySelectorAll('.modal-cmd-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const cmd = chip.dataset.cmd || chip.innerText.trim();
        navigator.clipboard.writeText(cmd)
          .then(() => showToast(`⚡ Command ${cmd} copied!`))
          .catch(() => showToast('Copied to clipboard.'));
      });
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        if (elements.modalBackdrop && elements.modalBackdrop.style.display !== 'none') {
          closeModal();
        }
        const inv = document.getElementById('invite-modal-backdrop');
        if (inv && inv.style.display !== 'none') {
          closeInviteModal();
        }
      }
    });

    // Theme Toggle
    if (elements.themeToggle) {
      elements.themeToggle.addEventListener('click', toggleTheme);
    }
  }

  /**
   * Filter and Sort Circulars
   */
  function applyFilters() {
    let list = [...state.jobs];

    // 1. Text Search Filter
    if (state.searchQuery) {
      const q = state.searchQuery;
      list = list.filter(j => {
        return (
          (j.title || '').toLowerCase().includes(q) ||
          (j.organization || '').toLowerCase().includes(q) ||
          (j.eligibility || '').toLowerCase().includes(q) ||
          (j.ai_summary || '').toLowerCase().includes(q) ||
          (j.category_label || '').toLowerCase().includes(q)
        );
      });
    }

    // 2. Category Filter
    if (state.activeCategory !== 'all') {
      list = list.filter(j => j.category === state.activeCategory);
    }

    // 3. Sector Filter
    if (state.activeSector !== 'all') {
      list = list.filter(j => {
        if (state.activeSector === 'central_recruitment') return j.source === 'BB_BSCS' || j.source_type === 'central_recruitment';
        return j.source_type === state.activeSector;
      });
    }

    // 4. Sorting
    list.sort((a, b) => {
      if (state.activeSort === 'deadline_asc') {
        const da = a.days_left != null ? a.days_left : 999;
        const db = b.days_left != null ? b.days_left : 999;
        return da - db;
      }
      if (state.activeSort === 'score_desc') {
        return (b.ai_relevance_score || 0) - (a.ai_relevance_score || 0);
      }
      if (state.activeSort === 'title_asc') {
        return (a.title || '').localeCompare(b.title || '');
      }
      return 0;
    });

    state.filteredJobs = list;
    renderJobs();
  }

  /**
   * Render Circular Cards
   */
  function renderJobs() {
    if (!elements.circularsGrid) return;

    if (elements.resultsCountBadge) {
      elements.resultsCountBadge.textContent = `Showing ${state.filteredJobs.length} of ${state.jobs.length} circulars`;
    }

    if (state.filteredJobs.length === 0) {
      elements.circularsGrid.innerHTML = '';
      if (elements.emptyState) elements.emptyState.style.display = 'block';
      return;
    }

    if (elements.emptyState) elements.emptyState.style.display = 'none';

    elements.circularsGrid.innerHTML = state.filteredJobs.map(job => {
      // Days remaining badge styling
      let deadlineBadge = '';
      if (job.days_left != null) {
        if (job.days_left <= 2) {
          deadlineBadge = `<span class="deadline-chip deadline-soon">🔥 ${job.days_left === 0 ? 'Ends Today!' : job.days_left + ' Days Left'}</span>`;
        } else if (job.days_left <= 7) {
          deadlineBadge = `<span class="deadline-chip deadline-mid">⏳ ${job.days_left} Days Left</span>`;
        } else {
          deadlineBadge = `<span class="deadline-chip deadline-ok">📅 ${job.days_left} Days Left</span>`;
        }
      } else {
        deadlineBadge = `<span class="deadline-chip deadline-ok">${escapeHtml(job.deadline_formatted || 'Official Circular')}</span>`;
      }

      const matchPercent = Math.round((job.ai_relevance_score || 0.85) * 100);

      return `
        <article class="job-card glass-panel" id="job-card-${job.id}">
          <div>
            <div class="job-card-top">
              <div class="job-org-info">
                <span class="job-org-name">${escapeHtml(job.organization)}</span>
                <span class="job-sector-tag">${escapeHtml(job.category_label || 'Banking')}</span>
              </div>
              <span class="job-score-badge" title="AI Verification & Relevancy">${matchPercent}% Match</span>
            </div>

            <h3 class="job-title">${escapeHtml(job.title)}</h3>

            <!-- Minimalistic Blockquote Card (Telegram Style) -->
            <div class="job-blockquote">
              <div class="bq-item">
                <span class="bq-label">👥 Vacancy:</span>
                <span class="bq-val">${escapeHtml(job.vacancies || 'Check Circular')}</span>
              </div>
              <div class="bq-item">
                <span class="bq-label">💰 Salary:</span>
                <span class="bq-val">${escapeHtml(job.salary || 'National Pay Scale')}</span>
              </div>
              <div class="bq-item">
                <span class="bq-label">🎓 Degree:</span>
                <span class="bq-val">${escapeHtml(truncate(job.eligibility, 70) || 'See Circular')}</span>
              </div>
              <div class="bq-item">
                <span class="bq-label">📅 Deadline:</span>
                <span class="bq-val">${escapeHtml(job.deadline_formatted || job.deadline)} ${deadlineBadge}</span>
              </div>
            </div>

            <!-- Summary snippet -->
            <p class="job-summary">${escapeHtml(job.ai_summary || job.title)}</p>
          </div>

          <div class="job-actions">
            <button class="job-details-btn" data-action="details" data-job-id="${job.id}">
              ℹ️ View Full Details & Summary
            </button>
            ${job.circular_url ? `
              <a href="${escapeHtml(job.circular_url)}" target="_blank" rel="noopener noreferrer" class="btn btn-sm btn-secondary">
                📄 Circular (PDF)
              </a>
            ` : `
              <button class="btn btn-sm btn-secondary" disabled>📄 No PDF</button>
            `}
            <a href="${escapeHtml(job.apply_url || job.url)}" target="_blank" rel="noopener noreferrer" class="btn btn-sm btn-primary">
              👉 Apply Online ➔
            </a>
          </div>
        </article>
      `;
    }).join('');

    // Attach click listeners for "Details" buttons
    elements.circularsGrid.querySelectorAll('[data-action="details"]').forEach(btn => {
      btn.addEventListener('click', () => {
        const jobId = parseInt(btn.dataset.jobId, 10);
        const job = state.jobs.find(j => j.id === jobId);
        if (job) openModal(job);
      });
    });
  }

  /**
   * Render 105+ Institutions Directory
   */
  function renderDirectory() {
    if (!elements.directoryGrid) return;

    let list = [...state.banks];

    // Filter by type tab
    if (state.activeDirType !== 'all') {
      list = list.filter(b => b.type === state.activeDirType);
    }

    // Filter by search query
    if (state.bankSearchQuery) {
      const q = state.bankSearchQuery;
      list = list.filter(b => b.name.toLowerCase().includes(q) || (b.short_name || '').toLowerCase().includes(q));
    }

    if (list.length === 0) {
      elements.directoryGrid.innerHTML = `
        <div style="grid-column: 1/-1; text-align: center; padding: 30px; color: var(--text-muted);">
          No institutions found matching '${escapeHtml(state.bankSearchQuery)}'.
        </div>
      `;
      return;
    }

    elements.directoryGrid.innerHTML = list.map(bank => {
      const typeDisplay = formatBankType(bank.type);
      return `
        <a href="${escapeHtml(bank.career_url)}" target="_blank" rel="noopener noreferrer" class="bank-card" title="Visit ${escapeHtml(bank.name)} Career Page">
          <div class="bank-info">
            <span class="bank-name">${escapeHtml(bank.name)}</span>
            <span class="bank-category">${escapeHtml(typeDisplay)}</span>
          </div>
          <span class="bank-status-dot" title="Actively Monitored Every 30 Minutes"></span>
        </a>
      `;
    }).join('');
  }

  /**
   * Modal Open & Populate
   */
  function openModal(job) {
    if (!elements.modalBackdrop) return;

    elements.modalOrgBadge.textContent = job.organization;
    elements.modalJobTitle.textContent = job.title;

    // Tags
    elements.modalTags.innerHTML = `
      <span class="badge badge-accent">${escapeHtml(job.category_label || 'Banking')}</span>
      <span class="badge" style="background: rgba(255,255,255,0.08);">${escapeHtml(job.source || 'Verified Source')}</span>
      <span class="badge" style="background: rgba(16, 185, 129, 0.15); color: var(--accent-emerald);">Match: ${Math.round((job.ai_relevance_score || 0.85) * 100)}%</span>
    `;

    // Body content
    elements.modalBody.innerHTML = `
      <div class="job-blockquote" style="margin-bottom: 0;">
        <div class="bq-item"><span class="bq-label">👥 Vacancies:</span> <span class="bq-val">${escapeHtml(job.vacancies || 'As per circular')}</span></div>
        <div class="bq-item"><span class="bq-label">💰 Salary:</span> <span class="bq-val">${escapeHtml(job.salary || 'National Pay Scale')}</span></div>
        <div class="bq-item"><span class="bq-label">📅 Deadline:</span> <span class="bq-val">${escapeHtml(job.deadline_formatted || job.deadline)} (${job.days_left != null ? job.days_left + ' days left' : 'Active'})</span></div>
      </div>

      <div>
        <h4 class="modal-section-title">🎓 Key Eligibility Requirements</h4>
        <p style="font-size: 0.9rem; color: var(--text-secondary); line-height: 1.6;">
          ${escapeHtml(job.eligibility || 'Please refer to the official PDF circular for detailed requirements.')}
        </p>
      </div>

      ${job.ai_summary ? `
        <div>
          <h4 class="modal-section-title">📄 AI English Summary</h4>
          <p style="font-size: 0.88rem; color: var(--text-secondary); line-height: 1.5;">${escapeHtml(job.ai_summary)}</p>
        </div>
      ` : ''}

      ${job.ai_summary_bn ? `
        <div>
          <h4 class="modal-section-title">🇧🇩 সারসংক্ষেপ (বাংলা)</h4>
          <p style="font-size: 0.88rem; color: var(--text-secondary); line-height: 1.6; font-family: 'Noto Sans Bengali', sans-serif;">
            ${escapeHtml(job.ai_summary_bn)}
          </p>
        </div>
      ` : ''}
    `;

    // Footer actions
    elements.modalFooter.innerHTML = `
      ${job.circular_url ? `
        <a href="${escapeHtml(job.circular_url)}" target="_blank" rel="noopener noreferrer" class="btn btn-secondary">
          📄 Download Official Circular (PDF)
        </a>
      ` : ''}
      <a href="${escapeHtml(job.apply_url || job.url)}" target="_blank" rel="noopener noreferrer" class="btn btn-primary">
        👉 Apply on Official Portal ➔
      </a>
      <button class="btn btn-secondary" id="modal-copy-link-btn">
        📋 Copy Direct Link
      </button>
    `;

    const copyBtn = elements.modalFooter.querySelector('#modal-copy-link-btn');
    if (copyBtn) {
      copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(job.apply_url || job.url);
        showToast('Link copied to clipboard!');
      });
    }

    elements.modalBackdrop.style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }

  function closeModal() {
    if (!elements.modalBackdrop) return;
    elements.modalBackdrop.style.display = 'none';
    document.body.style.overflow = '';
  }

  function updateModalActionBtn(tabName, isPublic) {
    const actionBtn = document.getElementById('modal-action-btn');
    const badgeEl = document.getElementById('modal-org-badge');
    const titleEl = document.getElementById('modal-invite-title');

    if (!actionBtn) return;

    if (tabName === 'group') {
      actionBtn.href = 'https://t.me/BDBankJobMonitorBot?start=request_group';
      actionBtn.innerHTML = '<span>Open Bot to Request Group Invite ➔</span>';
      if (badgeEl) badgeEl.textContent = '🔒 Telegram Access Protocol';
      if (titleEl) titleEl.textContent = 'Request Private Group Invite';
    } else {
      // tabName === 'bot'
      if (isPublic) {
        actionBtn.href = 'https://t.me/BDBankJobMonitorBot';
        actionBtn.innerHTML = '<span>🚀 Start 1-on-1 Bot Chat Now ➔</span>';
        if (badgeEl) badgeEl.textContent = '🌐 Public 1-on-1 Bot Access';
        if (titleEl) titleEl.textContent = 'Direct 1-on-1 Bot Access';
      } else {
        actionBtn.href = 'https://t.me/BDBankJobMonitorBot?start=request_access';
        actionBtn.innerHTML = '<span>Open Bot in Telegram to Request ➔</span>';
        if (badgeEl) badgeEl.textContent = '🔒 Telegram Access Protocol';
        if (titleEl) titleEl.textContent = 'Request Bot Usage Access';
      }
    }
  }

  function updateModalForMode() {
    const isPublic = (state.botAccessMode === 'public');
    const flowPub = document.getElementById('bot-flow-public');
    const flowPriv = document.getElementById('bot-flow-private');

    if (flowPub) flowPub.style.display = isPublic ? 'block' : 'none';
    if (flowPriv) flowPriv.style.display = isPublic ? 'none' : 'block';

    const currentTab = state.activeModalTab || 'bot';
    updateModalActionBtn(currentTab, isPublic);
  }

  function switchModalTab(tabName) {
    state.activeModalTab = tabName;
    const modalTabs = document.getElementById('modal-access-tabs');
    if (modalTabs) {
      modalTabs.querySelectorAll('.modal-tab-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.tab === tabName);
      });
    }
    const paneBot = document.getElementById('pane-tab-bot');
    const paneGroup = document.getElementById('pane-tab-group');
    if (paneBot) paneBot.style.display = tabName === 'bot' ? 'block' : 'none';
    if (paneGroup) paneGroup.style.display = tabName === 'group' ? 'block' : 'none';

    updateModalActionBtn(tabName, state.botAccessMode === 'public');
  }

  function openInviteModal(tab = 'bot') {
    const backdrop = document.getElementById('invite-modal-backdrop');
    if (!backdrop) return;
    state.activeModalTab = tab;
    updateModalForMode();
    switchModalTab(tab);
    backdrop.style.display = 'flex';
    document.body.style.overflow = 'hidden';
  }

  function closeInviteModal() {
    const backdrop = document.getElementById('invite-modal-backdrop');
    if (!backdrop) return;
    backdrop.style.display = 'none';
    document.body.style.overflow = '';
  }

  /**
   * Dynamically reflect Telegram Bot Access Mode (controlled by admin via /mode)
   */
  function updateBotAccessModeUI(mode) {
    const isPublic = (mode === 'public');
    const indicator = document.getElementById('tg-status-indicator');
    const valEl = document.getElementById('tg-status-val');
    const badgeBot = document.getElementById('pathway-badge-bot');
    const descBot = document.getElementById('pathway-desc-bot');
    const actionWrap = document.getElementById('pathway-action-bot-wrap');

    if (indicator) {
      indicator.classList.toggle('status-public', isPublic);
      indicator.classList.toggle('status-private', !isPublic);
    }

    if (valEl) {
      valEl.textContent = isPublic 
        ? '🌐 Public (Open to Everyone)' 
        : '🔒 Private (Admin Approval Required)';
    }

    if (badgeBot) {
      badgeBot.textContent = isPublic 
        ? 'DIRECT 1-ON-1 DM • OPEN TO ALL' 
        : 'DIRECT 1-ON-1 DM • APPROVAL GATED';
    }

    if (descBot) {
      descBot.innerHTML = isPublic
        ? '1-on-1 private bot queries are currently <strong>publicly open</strong> to all Telegram users! Query <code>/latest</code>, <code>/categories</code>, and <code>/search</code> without waiting for admin approval.'
        : 'Prefer direct personal queries? Request permission to use the bot in 1-on-1 private chat. Query <code>/latest</code>, <code>/categories</code>, and <code>/search</code> without notifications from other members.';
    }

    if (actionWrap) {
      if (isPublic) {
        actionWrap.innerHTML = `
          <a href="https://t.me/BDBankJobMonitorBot" target="_blank" rel="noopener noreferrer" class="btn btn-primary" id="bot-action-btn">
            <span>🚀 Start 1-on-1 Bot Chat</span>
          </a>
        `;
      } else {
        actionWrap.innerHTML = `
          <button class="btn btn-primary private-invite-trigger" id="bot-action-btn" data-target-tab="bot">
            <span>🤖 Request Bot Usage Access</span>
          </button>
        `;
        const btn = document.getElementById('bot-action-btn');
        if (btn) {
          btn.addEventListener('click', (e) => {
            e.preventDefault();
            openInviteModal('bot');
          });
        }
      }
    }

    // Synchronize modal state as well
    updateModalForMode();
  }

  /**
   * Category Chip Badge Counts
   */
  function updateCategoryChipCounts() {
    const counts = {
      all: state.jobs.length,
      engineering: 0,
      it: 0,
      law: 0,
      analyst: 0,
      audit: 0,
      officer: 0,
    };

    state.jobs.forEach(j => {
      if (counts[j.category] !== undefined) {
        counts[j.category]++;
      }
    });

    Object.keys(counts).forEach(cat => {
      const el = document.getElementById(`count-${cat}`);
      if (el) el.textContent = counts[cat];
    });
  }

  /**
   * Theme Toggle
   */
  function initTheme() {
    const savedTheme = localStorage.getItem('bd_jobs_theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
  }

  function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('bd_jobs_theme', next);
    showToast(`Switched to ${next} mode`);
  }

  /**
   * Toast Helper
   */
  function showToast(msg) {
    if (!elements.toast) return;
    elements.toast.textContent = msg;
    elements.toast.classList.add('show');
    setTimeout(() => {
      elements.toast.classList.remove('show');
    }, 2800);
  }

  /**
   * Helper Utilities
   */
  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function truncate(str, len) {
    if (!str) return '';
    return str.length > len ? str.substring(0, len) + '...' : str;
  }

  function formatBankType(type) {
    const map = {
      central_recruitment: 'Govt / Central',
      state_owned: 'State-Owned Bank',
      specialized: 'Specialized Bank',
      private: 'Private Commercial Bank',
      islami: 'Islamic Shariah Bank',
      foreign: 'Foreign Commercial Bank',
      digital: 'Digital Bank',
      non_scheduled: 'Non-Scheduled Bank',
      nbfi: 'Non-Bank Financial Institution',
    };
    return map[type] || 'Financial Institution';
  }

  // Run on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
