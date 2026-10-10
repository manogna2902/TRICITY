/**
 * DataWise AI - Client Application Logic
 * State management, deterministic analysis visualizer, interactive repair studio, and reports.
 */

const App = {
  state: {
    token: null,
    filename: null,
    originalAnalysis: null,
    initialScore: null,
    cleanedAnalysis: null,
    cleanedScore: null,
    report: null,
    auditLog: [],
    customRules: [],
    currentPreviewTab: 'original',
    charts: {
      radar: null,
      bar: null
    }
  },

  init() {
    this.bindEvents();
    this.handleRouting();
    this.restoreSession();
  },

  bindEvents() {
    // Navigation links
    document.querySelectorAll('.sidebar-nav .nav-item').forEach(link => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        const section = link.getAttribute('data-section');
        this.navigateTo(section);
      });
    });

    // Mobile menu toggle
    const menuToggle = document.getElementById('menu-toggle');
    if (menuToggle) {
      menuToggle.addEventListener('click', () => {
        document.getElementById('sidebar').classList.toggle('open');
      });
    }

    // Drag and Drop Zone
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');

    if (dropZone && fileInput) {
      ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
          e.preventDefault();
          e.stopPropagation();
          dropZone.classList.add('dragover');
        });
      });

      ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
          e.preventDefault();
          e.stopPropagation();
          dropZone.classList.remove('dragover');
        });
      });

      dropZone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
          this.handleFileSelected(files[0]);
        }
      });

      fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
          this.handleFileSelected(e.target.files[0]);
        }
      });
    }

    // Tabs navigation inside Data Quality
    document.querySelectorAll('.tabs-nav .tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const tabId = btn.getAttribute('data-tab');
        if (!tabId) return;
        document.querySelectorAll('.tabs-nav .tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        const targetPane = document.getElementById(tabId);
        if (targetPane) targetPane.classList.add('active');
      });
    });

    // Handle hash change
    window.addEventListener('hashchange', () => {
      this.handleRouting();
    });
  },

  handleRouting() {
    const hash = window.location.hash.replace('#', '') || 'overview';
    this.navigateTo(hash, false);
  },

  navigateTo(sectionId, updateHash = true) {
    // Hide all sections
    document.querySelectorAll('.content-section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.sidebar-nav .nav-item').forEach(n => n.classList.remove('active'));

    const targetSection = document.getElementById(`section-${sectionId}`);
    const targetNavItem = document.querySelector(`.sidebar-nav .nav-item[data-section="${sectionId}"]`);

    if (targetSection) {
      targetSection.classList.add('active');
    }
    if (targetNavItem) {
      targetNavItem.classList.add('active');
    }

    // Update titles
    const titles = {
      overview: { title: 'Dashboard Overview', sub: 'Turn messy data into trusted data with transparent statistical repairs.' },
      upload: { title: 'Upload Dataset', sub: 'Upload CSV or Excel files for immediate deterministic inspection.' },
      quality: { title: 'Data Quality Inspection', sub: 'Examine detailed findings, severity breakdown, and column profiling.' },
      clean: { title: 'Data Cleaning Studio', sub: 'Select automated repairs, preview impact, and safely transform datasets.' },
      reports: { title: 'Quality & Audit Reports', sub: 'Review before-and-after scorecards and export verified artifacts.' },
      about: { title: 'About DataWise AI', sub: 'Mission, mathematical quality algorithms, and technical architecture.' }
    };

    if (titles[sectionId]) {
      document.getElementById('page-title').textContent = titles[sectionId].title;
      document.getElementById('page-subtitle').textContent = titles[sectionId].sub;
    }

    if (updateHash) {
      window.location.hash = sectionId;
    }

    // Close mobile sidebar if open
    document.getElementById('sidebar').classList.remove('open');

    // Trigger chart update if entering overview
    if (sectionId === 'overview') {
      this.renderCharts();
    }
  },

  showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
      toast.remove();
    }, 4000);
  },

  // --- Session Management ---

  restoreSession() {
    const savedToken = sessionStorage.getItem('datawise_token');
    if (savedToken) {
      fetch(`/api/state/${savedToken}`)
        .then(res => res.json())
        .then(data => {
          if (data.success) {
            this.state.token = savedToken;
            this.state.filename = data.meta.filename;
            this.state.originalAnalysis = data.original_analysis;
            this.state.initialScore = data.initial_score;
            this.state.cleanedAnalysis = data.cleaned_analysis;
            this.state.cleanedScore = data.cleaned_score;
            this.state.report = data.report;
            this.state.auditLog = data.meta.operations_applied || [];

            this.updateAllViews();
          } else {
            sessionStorage.removeItem('datawise_token');
          }
        })
        .catch(() => {
          sessionStorage.removeItem('datawise_token');
        });
    }
  },

  saveSession(token, filename) {
    this.state.token = token;
    this.state.filename = filename;
    sessionStorage.setItem('datawise_token', token);
  },

  // --- File Upload ---

  selectedFile: null,

  handleFileSelected(file) {
    const validExts = ['csv', 'xlsx', 'xls'];
    const ext = file.name.split('.').pop().toLowerCase();
    if (!validExts.includes(ext)) {
      this.showToast('Invalid file format. Please upload a CSV or Excel file.', 'error');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      this.showToast('File exceeds 10 MB limit.', 'error');
      return;
    }

    this.selectedFile = file;
    document.getElementById('selected-file-name').textContent = file.name;
    document.getElementById('selected-file-size').textContent = `${(file.size / 1024).toFixed(1)} KB`;
    document.getElementById('selected-file-card').style.display = 'block';
  },

  clearSelectedFile() {
    this.selectedFile = null;
    document.getElementById('file-input').value = '';
    document.getElementById('selected-file-card').style.display = 'none';
  },

  uploadAndAnalyze() {
    if (!this.selectedFile) return;

    const btn = document.getElementById('upload-analyze-btn');
    const spinner = btn.querySelector('.btn-spinner');
    const btnText = btn.querySelector('.btn-text');

    btn.disabled = true;
    spinner.style.display = 'inline-block';
    btnText.textContent = 'Analyzing Quality...';

    const formData = new FormData();
    formData.append('file', this.selectedFile);

    fetch('/api/upload', {
      method: 'POST',
      body: formData
    })
      .then(res => res.json())
      .then(data => {
        btn.disabled = false;
        spinner.style.display = 'none';
        btnText.textContent = 'Upload & Analyze Dataset';

        if (data.success) {
          this.saveSession(data.token, data.filename);
          this.state.originalAnalysis = data.analysis;
          this.state.initialScore = data.score;
          this.state.cleanedAnalysis = null;
          this.state.cleanedScore = null;
          this.state.report = null;
          this.state.auditLog = [];

          this.updateAllViews();
          this.showToast('Dataset analyzed successfully!', 'success');
          this.navigateTo('quality');
        } else {
          this.showToast(data.error || 'Failed to process file.', 'error');
        }
      })
      .catch(err => {
        btn.disabled = false;
        spinner.style.display = 'none';
        btnText.textContent = 'Upload & Analyze Dataset';
        this.showToast(`Upload error: ${err.message}`, 'error');
      });
  },

  loadSampleData() {
    this.showToast('Loading synthetic demo dataset...', 'info');

    fetch('/api/sample', { method: 'POST' })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          this.saveSession(data.token, data.filename);
          this.state.originalAnalysis = data.analysis;
          this.state.initialScore = data.score;
          this.state.cleanedAnalysis = null;
          this.state.cleanedScore = null;
          this.state.report = null;
          this.state.auditLog = [];

          this.updateAllViews();
          this.showToast('Sample dataset loaded & analyzed!', 'success');
          this.navigateTo('overview');
        } else {
          this.showToast(data.error || 'Failed to load sample data.', 'error');
        }
      })
      .catch(err => {
        this.showToast(`Failed to load sample: ${err.message}`, 'error');
      });
  },

  resetSession() {
    if (!this.state.token) return;
    if (!confirm('Are you sure you want to reset all changes and revert to the raw original dataset?')) return;

    fetch('/api/reset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: this.state.token })
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          this.state.cleanedAnalysis = null;
          this.state.cleanedScore = null;
          this.state.report = null;
          this.state.auditLog = [];
          this.updateAllViews();
          this.showToast('Reset to raw dataset completed.', 'info');
          this.navigateTo('quality');
        } else {
          this.showToast(data.error || 'Failed to reset.', 'error');
        }
      })
      .catch(err => {
        this.showToast(`Reset error: ${err.message}`, 'error');
      });
  },

  // --- View Updates ---

  updateAllViews() {
    this.updateSidebarInfo();
    this.updateOverviewStats();
    this.updateQualityInspection();
    this.updateCleanerStudio();
    this.updateReportsScorecard();
    this.renderCharts();
  },

  updateSidebarInfo() {
    const filenameEl = document.getElementById('sidebar-filename');
    const statsEl = document.getElementById('sidebar-stats');
    const resetBtn = document.getElementById('sidebar-reset-btn');
    const counterBadge = document.getElementById('nav-issue-counter');

    if (this.state.filename && this.state.originalAnalysis) {
      filenameEl.textContent = this.state.filename;
      const rows = this.state.originalAnalysis.summary.total_rows;
      const cols = this.state.originalAnalysis.summary.total_cols;
      statsEl.textContent = `${rows} rows • ${cols} cols`;
      resetBtn.style.display = this.state.cleanedAnalysis ? 'block' : 'none';

      const totalIssues = this.state.originalAnalysis.issues.length;
      if (totalIssues > 0) {
        counterBadge.textContent = totalIssues;
        counterBadge.style.display = 'inline-block';
      } else {
        counterBadge.style.display = 'none';
      }
    } else {
      filenameEl.textContent = 'No dataset loaded';
      statsEl.textContent = 'Upload or try demo';
      resetBtn.style.display = 'none';
      counterBadge.style.display = 'none';
    }
  },

  updateOverviewStats() {
    if (!this.state.originalAnalysis || !this.state.initialScore) return;

    const summary = this.state.originalAnalysis.summary;
    const score = this.state.initialScore;

    document.getElementById('stat-total-rows').textContent = summary.total_rows.toLocaleString();
    document.getElementById('stat-total-cols').textContent = `${summary.total_cols} Columns`;

    document.getElementById('stat-total-issues').textContent = summary.total_issues_count;
    document.getElementById('stat-problematic-cells').textContent = `${summary.total_problematic_cells} flagged cells`;

    const dupCount = this.state.originalAnalysis.duplicate_analysis.duplicate_count;
    const dupPct = this.state.originalAnalysis.duplicate_analysis.duplicate_pct;
    document.getElementById('stat-duplicate-rows').textContent = dupCount;
    document.getElementById('stat-duplicate-pct').textContent = `${dupPct}% of records`;

    const missingCount = this.state.originalAnalysis.missing_analysis.total_missing;
    const missingPct = this.state.originalAnalysis.missing_analysis.overall_missing_pct;
    document.getElementById('stat-missing-values').textContent = missingCount;
    document.getElementById('stat-missing-pct').textContent = `${missingPct}% overall`;

    // Overview Score Dial
    const currentScore = this.state.cleanedScore ? this.state.cleanedScore.overall_score : score.overall_score;
    const currentGrade = this.state.cleanedScore ? this.state.cleanedScore.grade : score.grade;
    const currentStatus = this.state.cleanedScore ? `Cleaned: ${this.state.cleanedScore.status}` : score.status;

    document.getElementById('overview-score-val').textContent = currentScore;
    const gradeBadge = document.getElementById('overview-grade-badge');
    gradeBadge.textContent = `Grade: ${currentGrade}`;
    gradeBadge.className = `dial-grade ${currentScore >= 80 ? 'badge-cleaned' : 'badge-warning'}`;
    document.getElementById('overview-score-subtext').textContent = currentStatus;
  },

  updateQualityInspection() {
    if (!this.state.originalAnalysis || !this.state.initialScore) return;

    const score = this.state.initialScore;
    const analysis = this.state.originalAnalysis;

    document.getElementById('quality-score-val').textContent = score.overall_score;
    document.getElementById('quality-grade-val').textContent = score.grade;
    document.getElementById('quality-status-tag').textContent = `Quality Status: ${score.status}`;
    document.getElementById('quality-headline').textContent = `${score.status} • ${analysis.summary.total_issues_count} Issue(s) Detected`;
    document.getElementById('quality-formula-text').textContent = score.formula_explanation;

    // Pillar Scores
    const bd = score.breakdown;
    document.getElementById('pillar-missing-score').textContent = `${bd.missing.score}/100`;
    document.getElementById('pillar-missing-desc').textContent = bd.missing.details;

    document.getElementById('pillar-dup-score').textContent = `${bd.duplicates.score}/100`;
    document.getElementById('pillar-dup-desc').textContent = bd.duplicates.details;

    document.getElementById('pillar-invalid-score').textContent = `${bd.invalid.score}/100`;
    document.getElementById('pillar-invalid-desc').textContent = bd.invalid.details;

    document.getElementById('pillar-format-score').textContent = `${bd.formatting.score}/100`;
    document.getElementById('pillar-format-desc').textContent = bd.formatting.details;

    // Tab Counts
    document.getElementById('tab-issue-count').textContent = analysis.issues.length;
    document.getElementById('tab-col-count').textContent = analysis.column_profiles.length;
    document.getElementById('tab-outlier-count').textContent = analysis.outlier_analysis.total_outliers;

    // Render Issues Table
    this.renderIssuesTable(analysis.issues);

    // Render Column Profiler
    this.renderColumnProfiler(analysis.column_profiles);

    // Render Outliers
    this.renderOutliers(analysis.outlier_analysis);

    // Populate Rule Columns Select
    const colSelect = document.getElementById('rule-col-select');
    colSelect.innerHTML = '<option value="">Select Column</option>';
    analysis.summary.columns.forEach(col => {
      const opt = document.createElement('option');
      opt.value = col;
      opt.textContent = col;
      colSelect.appendChild(opt);
    });
  },

  renderIssuesTable(issues) {
    const tbody = document.getElementById('issues-table-body');
    if (!issues || issues.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-success">✓ Outstanding! No data quality issues detected.</td></tr>';
      return;
    }

    tbody.innerHTML = issues.map(iss => {
      const severityClass = iss.severity === 'critical' ? 'badge-critical' : (iss.severity === 'warning' ? 'badge-warning' : 'badge-info');
      const rowsSample = iss.affected_rows && iss.affected_rows.length > 0
        ? iss.affected_rows.slice(0, 8).map(r => `<span class="badge-code">Row ${r}</span>`).join(' ')
        : '<span class="text-muted">N/A</span>';

      return `
        <tr>
          <td><span class="badge ${severityClass}">${iss.severity}</span></td>
          <td><strong>${iss.title}</strong></td>
          <td><span class="badge-code">${iss.column}</span></td>
          <td><strong>${iss.count}</strong> <span class="text-muted">(${iss.percentage}%)</span></td>
          <td>${rowsSample}</td>
          <td>
            <div class="text-sm">${iss.description}</div>
            <div class="text-sm text-muted mt-1"><strong>Recommendation:</strong> ${iss.recommendation}</div>
          </td>
        </tr>
      `;
    }).join('');
  },

  filterIssuesTable() {
    if (!this.state.originalAnalysis) return;
    const filter = document.getElementById('issue-filter').value;
    const allIssues = this.state.originalAnalysis.issues;

    if (filter === 'all') {
      this.renderIssuesTable(allIssues);
    } else {
      const filtered = allIssues.filter(i => i.severity === filter);
      this.renderIssuesTable(filtered);
    }
  },

  renderColumnProfiler(profiles) {
    const tbody = document.getElementById('profiler-table-body');
    if (!profiles || profiles.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted">No profile information available.</td></tr>';
      return;
    }

    tbody.innerHTML = profiles.map(p => {
      let statsStr = '<span class="text-muted">N/A</span>';
      if (p.stats) {
        statsStr = `<span class="text-sm">Min: ${p.stats.min} | Max: ${p.stats.max} | Mean: ${p.stats.mean}</span>`;
      }

      const missingBadgeClass = p.missing_pct > 20 ? 'badge-critical' : (p.missing_pct > 0 ? 'badge-warning' : 'badge-cleaned');

      return `
        <tr>
          <td><strong>${p.name}</strong></td>
          <td><span class="badge-code">${p.inferred_type}</span></td>
          <td>${p.valid_count} / ${p.total_count}</td>
          <td><span class="badge ${missingBadgeClass}">${p.missing_count} (${p.missing_pct}%)</span></td>
          <td>${p.distinct_count}</td>
          <td>${statsStr}</td>
        </tr>
      `;
    }).join('');
  },

  renderOutliers(outlierAnalysis) {
    const container = document.getElementById('outliers-container');
    const outliersByCol = outlierAnalysis.outliers_by_column;

    if (!outliersByCol || Object.keys(outliersByCol).length === 0) {
      container.innerHTML = '<p class="text-muted">No statistical outliers detected (values within 1.5x IQR boundary).</p>';
      return;
    }

    let html = '<div class="outliers-grid">';
    for (const [col, info] of Object.entries(outliersByCol)) {
      const rowBadges = info.affected_rows_sample.map(r => `<span class="badge-code">Row ${r}</span>`).join(' ');
      html += `
        <div class="card mb-3 p-3">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <h4 class="mb-0">Column: <strong>${col}</strong></h4>
            <span class="badge badge-info">${info.count} Outliers Flagged</span>
          </div>
          <p class="text-sm text-secondary">
            <strong>IQR Bounds:</strong> Lower Bound: ${info.lower_bound} | Upper Bound: ${info.upper_bound} (Q1: ${info.q1}, Q3: ${info.q3})
          </p>
          <div class="mb-2">
            <strong>Sample Values:</strong> ${info.sample_values.join(', ')}
          </div>
          <div>
            <strong>Affected Rows:</strong> ${rowBadges}
          </div>
          <div class="text-sm text-muted mt-2">
            <em>${info.note}</em>
          </div>
        </div>
      `;
    }
    html += '</div>';
    container.innerHTML = html;
  },

  // --- Custom Rules ---

  handleRuleTypeChange() {
    const type = document.getElementById('rule-type-select').value;
    const minGroup = document.getElementById('rule-min-group');
    const maxGroup = document.getElementById('rule-max-group');
    const regexGroup = document.getElementById('rule-regex-group');

    minGroup.style.display = (type === 'range' || type === 'min') ? 'block' : 'none';
    maxGroup.style.display = (type === 'range' || type === 'max') ? 'block' : 'none';
    regexGroup.style.display = (type === 'regex') ? 'block' : 'none';
  },

  addCustomRule() {
    const col = document.getElementById('rule-col-select').value;
    const type = document.getElementById('rule-type-select').value;

    if (!col) {
      this.showToast('Please select a target column for the rule.', 'warning');
      return;
    }

    const rule = { column: col, rule_type: type };

    if (type === 'range') {
      const minVal = parseFloat(document.getElementById('rule-min-val').value);
      const maxVal = parseFloat(document.getElementById('rule-max-val').value);
      if (isNaN(minVal) || isNaN(maxVal)) {
        this.showToast('Please provide valid min and max numbers.', 'warning');
        return;
      }
      rule.min = minVal;
      rule.max = maxVal;
    } else if (type === 'min') {
      const minVal = parseFloat(document.getElementById('rule-min-val').value);
      if (isNaN(minVal)) {
        this.showToast('Please provide a valid min number.', 'warning');
        return;
      }
      rule.min = minVal;
    } else if (type === 'max') {
      const maxVal = parseFloat(document.getElementById('rule-max-val').value);
      if (isNaN(maxVal)) {
        this.showToast('Please provide a valid max number.', 'warning');
        return;
      }
      rule.max = maxVal;
    } else if (type === 'regex') {
      const pattern = document.getElementById('rule-regex-val').value.trim();
      if (!pattern) {
        this.showToast('Please provide a regex pattern.', 'warning');
        return;
      }
      rule.pattern = pattern;
    }

    this.state.customRules.push(rule);
    this.renderCustomRulesList();
    this.showToast(`Rule added on column '${col}'.`, 'success');
  },

  removeCustomRule(idx) {
    this.state.customRules.splice(idx, 1);
    this.renderCustomRulesList();
  },

  renderCustomRulesList() {
    const listEl = document.getElementById('active-rules-list');
    if (this.state.customRules.length === 0) {
      listEl.innerHTML = '<p class="text-muted text-sm">No custom rules added yet.</p>';
      return;
    }

    listEl.innerHTML = this.state.customRules.map((r, i) => `
      <div class="rule-chip">
        <span><strong>${r.column}</strong>: ${r.rule_type} (${r.min !== undefined ? 'min: ' + r.min : ''} ${r.max !== undefined ? 'max: ' + r.max : ''} ${r.pattern ? 'pat: ' + r.pattern : ''})</span>
        <button class="btn-icon" onclick="App.removeCustomRule(${i})" title="Remove Rule">✕</button>
      </div>
    `).join('');
  },

  // --- Cleaner Studio ---

  toggleCasingControls() {
    const checked = document.getElementById('clean-opt-casing').checked;
    document.getElementById('casing-sub-controls').style.display = checked ? 'block' : 'none';
  },

  toggleMissingControls() {
    const checked = document.getElementById('clean-opt-missing').checked;
    document.getElementById('missing-sub-controls').style.display = checked ? 'block' : 'none';
  },

  getCleaningConfig() {
    const removeDups = document.getElementById('clean-opt-duplicates').checked;
    const trimWs = document.getElementById('clean-opt-whitespace').checked;
    const optCasing = document.getElementById('clean-opt-casing').checked;
    const casingStrategy = document.getElementById('clean-casing-strategy').value;

    const optMissing = document.getElementById('clean-opt-missing').checked;
    const missingNumStrat = document.getElementById('missing-num-strategy').value;
    const missingTextStrat = document.getElementById('missing-text-strategy').value;
    const dropMissingRows = document.getElementById('missing-drop-rows').checked;

    const optDates = document.getElementById('clean-opt-dates').checked;
    const optNumerics = document.getElementById('clean-opt-numerics').checked;

    const columns = this.state.originalAnalysis ? this.state.originalAnalysis.summary.columns : [];

    // Build column strategies for missing values
    const columnStrategies = {};
    if (optMissing && !dropMissingRows) {
      const colProfiles = (this.state.originalAnalysis && this.state.originalAnalysis.column_profiles) || [];
      colProfiles.forEach(p => {
        if (p.inferred_type.startsWith('Numeric')) {
          columnStrategies[p.name] = { strategy: missingNumStrat };
        } else {
          columnStrategies[p.name] = { strategy: missingTextStrat, fill_value: 'Unknown' };
        }
      });
    }

    // Build numeric & date conversions
    const convertNumeric = [];
    if (optNumerics && this.state.originalAnalysis) {
      const numIssues = this.state.originalAnalysis.numeric_analysis.invalid_entries || {};
      Object.keys(numIssues).forEach(col => {
        convertNumeric.push({ column: col });
      });
    }

    const convertDates = [];
    if (optDates && this.state.originalAnalysis) {
      const dateIssues = this.state.originalAnalysis.date_analysis.invalid_dates || {};
      Object.keys(dateIssues).forEach(col => {
        convertDates.push({ column: col, format: 'YYYY-MM-DD' });
      });
    }

    return {
      remove_duplicates: removeDups,
      trim_whitespace: trimWs,
      trim_columns: columns,
      normalize_casing: {
        enabled: optCasing,
        strategy: casingStrategy,
        columns: columns
      },
      handle_missing: {
        global_strategy: dropMissingRows ? 'drop_rows' : 'none',
        column_strategies: columnStrategies
      },
      convert_numeric: convertNumeric,
      convert_dates: convertDates,
      filter_invalid_rules: {
        enabled: this.state.customRules.length > 0,
        rules: this.state.customRules
      }
    };
  },

  previewCleaning() {
    if (!this.state.token) {
      this.showToast('Please upload or load a dataset first.', 'warning');
      return;
    }

    this.showToast('Calculating preview impact...', 'info');
    const ops = this.getCleaningConfig();

    fetch('/api/preview-clean', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        token: this.state.token,
        operations: ops
      })
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          const alert = document.getElementById('preview-impact-alert');
          alert.style.display = 'block';

          const initScore = this.state.initialScore.overall_score;
          const newScore = data.new_score.overall_score;
          const deltaSign = data.score_delta >= 0 ? '+' : '';

          document.getElementById('impact-score-change').textContent =
            `Predicted Score: ${initScore} ➔ ${newScore} (${deltaSign}${data.score_delta} pts uplift)`;
          document.getElementById('impact-rows-change').textContent =
            `Projected Rows: ${data.projected_rows} (from ${this.state.originalAnalysis.summary.total_rows})`;

          const opCount = data.audit_log.length;
          document.getElementById('impact-audit-summary').textContent =
            `${opCount} operation(s) ready to be applied.`;

          this.renderPreviewTable(data.preview_cleaned_rows);
          this.switchPreviewTab('cleaned');
          this.showToast('Preview computed successfully!', 'success');
        } else {
          this.showToast(data.error || 'Preview failed.', 'error');
        }
      })
      .catch(err => {
        this.showToast(`Preview error: ${err.message}`, 'error');
      });
  },

  applyCleaning() {
    if (!this.state.token) {
      this.showToast('Please upload or load a dataset first.', 'warning');
      return;
    }

    this.showToast('Applying repairs and re-evaluating quality...', 'info');
    const ops = this.getCleaningConfig();

    fetch('/api/clean', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        token: this.state.token,
        operations: ops
      })
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          this.state.cleanedAnalysis = data.cleaned_analysis;
          this.state.cleanedScore = data.cleaned_score;
          this.state.report = data.report;
          this.state.auditLog = data.audit_log;

          this.updateAllViews();
          this.switchPreviewTab('cleaned');
          this.showToast(`Repairs applied successfully! Quality Score: ${data.cleaned_score.overall_score}/100`, 'success');
          this.navigateTo('reports');
        } else {
          this.showToast(data.error || 'Cleaning failed.', 'error');
        }
      })
      .catch(err => {
        this.showToast(`Cleaning error: ${err.message}`, 'error');
      });
  },

  switchPreviewTab(tab) {
    this.state.currentPreviewTab = tab;
    const btnOrig = document.getElementById('btn-show-original');
    const btnClean = document.getElementById('btn-show-cleaned');

    if (tab === 'original') {
      btnOrig.classList.add('active');
      btnClean.classList.remove('active');
      if (this.state.originalAnalysis) {
        this.renderPreviewTable(this.state.originalAnalysis.preview_rows);
      }
    } else {
      btnOrig.classList.remove('active');
      btnClean.classList.add('active');
      if (this.state.cleanedAnalysis) {
        this.renderPreviewTable(this.state.cleanedAnalysis.preview_rows);
      }
    }
  },

  renderPreviewTable(records) {
    const head = document.getElementById('preview-table-head');
    const body = document.getElementById('preview-table-body');

    if (!records || records.length === 0) {
      head.innerHTML = '<tr><th>#</th><th>Empty</th></tr>';
      body.innerHTML = '<tr><td colspan="2" class="text-center py-4 text-muted">No records available.</td></tr>';
      return;
    }

    const firstRow = records[0];
    const columns = Object.keys(firstRow).filter(k => k !== '_row_index');

    // Headers
    head.innerHTML = `<tr><th>#</th>${columns.map(c => `<th>${c}</th>`).join('')}</tr>`;

    // Rows
    body.innerHTML = records.map(r => {
      const cells = columns.map(col => {
        const val = r[col];
        const isMissing = val === '' || val === null || val === undefined;
        return isMissing
          ? '<td class="text-muted"><span class="badge badge-warning">null</span></td>'
          : `<td>${val}</td>`;
      }).join('');
      return `<tr><td><span class="badge-code">${r._row_index || '-'}</span></td>${cells}</tr>`;
    }).join('');
  },

  updateCleanerStudio() {
    if (this.state.originalAnalysis) {
      if (this.state.currentPreviewTab === 'original' || !this.state.cleanedAnalysis) {
        this.renderPreviewTable(this.state.originalAnalysis.preview_rows);
      } else {
        this.renderPreviewTable(this.state.cleanedAnalysis.preview_rows);
      }
    }
  },

  // --- Reports Section ---

  updateReportsScorecard() {
    if (!this.state.initialScore) return;

    const rep = this.state.report;
    const initScore = this.state.initialScore;
    const cleanScore = this.state.cleanedScore;

    // Before Card
    document.getElementById('rep-before-score').textContent = initScore.overall_score;
    document.getElementById('rep-before-grade').textContent = `Grade: ${initScore.grade}`;

    const origSummary = this.state.originalAnalysis.summary;
    document.getElementById('rep-before-rows').textContent = origSummary.total_rows;
    document.getElementById('rep-before-issues').textContent = origSummary.total_issues_count;
    document.getElementById('rep-before-missing').textContent = this.state.originalAnalysis.missing_analysis.total_missing;
    document.getElementById('rep-before-dups').textContent = this.state.originalAnalysis.duplicate_analysis.duplicate_count;

    // After Card
    if (cleanScore && this.state.cleanedAnalysis) {
      document.getElementById('rep-after-score').textContent = cleanScore.overall_score;
      document.getElementById('rep-after-grade').textContent = `Grade: ${cleanScore.grade}`;

      const cleanSummary = this.state.cleanedAnalysis.summary;
      document.getElementById('rep-after-rows').textContent = cleanSummary.total_rows;
      document.getElementById('rep-after-issues').textContent = cleanSummary.total_issues_count;
      document.getElementById('rep-after-missing').textContent = this.state.cleanedAnalysis.missing_analysis.total_missing;
      document.getElementById('rep-after-dups').textContent = this.state.cleanedAnalysis.duplicate_analysis.duplicate_count;

      const delta = roundDelta(cleanScore.overall_score - initScore.overall_score);
      document.getElementById('rep-delta-score').textContent = `+${delta} pts`;
    } else {
      document.getElementById('rep-after-score').textContent = '--';
      document.getElementById('rep-after-grade').textContent = 'Pending Repairs';
      document.getElementById('rep-after-rows').textContent = '--';
      document.getElementById('rep-after-issues').textContent = '--';
      document.getElementById('rep-after-missing').textContent = '--';
      document.getElementById('rep-after-dups').textContent = '--';
      document.getElementById('rep-delta-score').textContent = '+0.0 pts';
    }

    // Audit Trail
    const auditContainer = document.getElementById('audit-trail-container');
    const logs = this.state.auditLog;
    if (logs && logs.length > 0) {
      auditContainer.innerHTML = `
        <div class="audit-list">
          ${logs.map(log => `
            <div class="audit-item">
              <span class="audit-icon">✓</span>
              <div>
                <h5>${log.title || log.operation}</h5>
                <p>${log.description}</p>
              </div>
            </div>
          `).join('')}
        </div>
      `;
    } else {
      auditContainer.innerHTML = '<p class="text-muted">No cleaning operations have been applied yet.</p>';
    }
  },

  downloadExport(format) {
    if (!this.state.token) {
      this.showToast('No active dataset to export.', 'warning');
      return;
    }
    const version = this.state.cleanedAnalysis ? 'cleaned' : 'original';
    window.location.href = `/api/download/${this.state.token}/${format}?version=${version}`;
  },

  downloadReport(format) {
    if (!this.state.token) {
      this.showToast('No active session available.', 'warning');
      return;
    }
    if (!this.state.report) {
      this.showToast('Please apply repairs in the Clean Data studio first to generate a report.', 'warning');
      return;
    }
    window.location.href = `/api/report/${this.state.token}/${format}`;
  },

  // --- Charts Rendering ---

  renderCharts() {
    if (!this.state.initialScore) return;

    // 1. Radar Chart: Quality Pillars
    const radarCtx = document.getElementById('qualityRadarChart');
    if (radarCtx) {
      const bd = this.state.initialScore.breakdown;
      const initialPillars = [bd.missing.score, bd.duplicates.score, bd.invalid.score, bd.formatting.score];

      const datasets = [{
        label: 'Raw Dataset',
        data: initialPillars,
        fill: true,
        backgroundColor: 'rgba(239, 68, 68, 0.2)',
        borderColor: '#ef4444',
        pointBackgroundColor: '#ef4444',
        pointBorderColor: '#fff',
        pointHoverBackgroundColor: '#fff',
        pointHoverBorderColor: '#ef4444'
      }];

      if (this.state.cleanedScore) {
        const cbd = this.state.cleanedScore.breakdown;
        const cleanedPillars = [cbd.missing.score, cbd.duplicates.score, cbd.invalid.score, cbd.formatting.score];
        datasets.push({
          label: 'Cleaned Dataset',
          data: cleanedPillars,
          fill: true,
          backgroundColor: 'rgba(16, 185, 129, 0.2)',
          borderColor: '#10b981',
          pointBackgroundColor: '#10b981',
          pointBorderColor: '#fff',
          pointHoverBackgroundColor: '#fff',
          pointHoverBorderColor: '#10b981'
        });
      }

      if (this.state.charts.radar) {
        this.state.charts.radar.destroy();
      }

      this.state.charts.radar = new Chart(radarCtx, {
        type: 'radar',
        data: {
          labels: ['Completeness (Missing)', 'Uniqueness (Duplicates)', 'Validity (Types & Rules)', 'Consistency (Formatting)'],
          datasets: datasets
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            r: {
              angleLines: { color: '#e2e8f0' },
              grid: { color: '#e2e8f0' },
              suggestedMin: 0,
              suggestedMax: 100,
              ticks: { stepSize: 20, font: { family: 'Plus Jakarta Sans', size: 10 } },
              pointLabels: { font: { family: 'Plus Jakarta Sans', size: 11, weight: '600' } }
            }
          },
          plugins: {
            legend: { position: 'bottom', labels: { font: { family: 'Plus Jakarta Sans', size: 12 } } }
          }
        }
      });
    }

    // 2. Bar Chart: Issues by Category
    const barCtx = document.getElementById('issuesBarChart');
    if (barCtx) {
      const issues = this.state.originalAnalysis.issues || [];
      const counts = { missing: 0, duplicates: 0, invalid: 0, formatting: 0, outliers: 0, custom_rules: 0 };
      issues.forEach(i => {
        if (counts[i.category] !== undefined) {
          counts[i.category]++;
        }
      });

      if (this.state.charts.bar) {
        this.state.charts.bar.destroy();
      }

      this.state.charts.bar = new Chart(barCtx, {
        type: 'bar',
        data: {
          labels: ['Missing', 'Duplicates', 'Invalid Types', 'Formatting', 'Outliers', 'Rules'],
          datasets: [{
            label: 'Issues Flagged',
            data: [counts.missing, counts.duplicates, counts.invalid, counts.formatting, counts.outliers, counts.custom_rules],
            backgroundColor: [
              'rgba(147, 51, 234, 0.7)',
              'rgba(217, 119, 6, 0.7)',
              'rgba(220, 38, 38, 0.7)',
              'rgba(37, 99, 235, 0.7)',
              'rgba(59, 130, 246, 0.5)',
              'rgba(234, 88, 12, 0.7)'
            ],
            borderColor: [
              '#9333ea',
              '#d97706',
              '#dc2626',
              '#2563eb',
              '#3b82f6',
              '#ea580c'
            ],
            borderWidth: 1,
            borderRadius: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              beginAtZero: true,
              ticks: { stepSize: 1, font: { family: 'Plus Jakarta Sans', size: 11 } },
              grid: { color: '#f1f5f9' }
            },
            x: {
              grid: { display: false },
              ticks: { font: { family: 'Plus Jakarta Sans', size: 11, weight: '600' } }
            }
          },
          plugins: {
            legend: { display: false }
          }
        }
      });
    }
  }
};

function roundDelta(v) {
  return Math.round(v * 10) / 10;
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  App.init();
});
