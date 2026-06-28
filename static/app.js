const state = {
  roster: [],
  rules: [],
  onboardRuns: 0,
  autoRuns: 0,
  lastResultEl: null,
};

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? 'pending').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

window.addEventListener('DOMContentLoaded', async () => {
  bindTabs();
  bindActions();
  await refreshBrain();
  renderMetrics();
});

function bindTabs() {
  document.querySelectorAll('.tab').forEach(btn => {
    btn.addEventListener('click', () => showTab(btn.dataset.tab));
  });
}

function showTab(tab) {
  document.querySelectorAll('.tab').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  $('employeesPanel').classList.toggle('active', tab === 'employees');
  $('brainPanel').classList.toggle('active', tab === 'brain');
  if (tab === 'brain') renderBrainNetwork();
}

function bindActions() {
  document.querySelectorAll('.chip[data-trigger]').forEach(chip => {
    chip.addEventListener('click', () => submitIntake(chip.dataset.trigger));
  });
  document.querySelectorAll('.query-chip').forEach(chip => {
    chip.addEventListener('click', () => { $('brainQuery').value = chip.textContent; askBrain(); });
  });
  $('submitIntake').addEventListener('click', submitIntake);
  $('resetBrain').addEventListener('click', resetBrain);
  $('askBrain').addEventListener('click', askBrain);
  $('brainQuery').addEventListener('keydown', e => { if (e.key === 'Enter') askBrain(); });
}

async function api(path, body) {
  const controller = new AbortController();
  const t30 = setTimeout(() => setProcessing('Processing…'), 30000);
  const t60 = setTimeout(() => setProcessing('Taking longer than usual — click to retry'), 60000);
  try {
    const res = await fetch(path, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body || {}),
      signal: controller.signal,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Request failed');
    return data;
  } finally {
    clearTimeout(t30); clearTimeout(t60);
  }
}

async function submitIntake(triggerOverride) {
  const trigger = (triggerOverride || $('triggerInput').value).trim();
  if (!trigger) return;
  if (triggerOverride) $('triggerInput').value = trigger;
  setProcessing('Processing…');
  $('resultCard').classList.remove('empty');
  $('beats').innerHTML = ['PERCEIVE','REASON','ACT','HAND OFF'].map(b => `<div class="beat" data-beat="${b}">${b}</div>`).join('');
  $('resultContent').innerHTML = `<div class="trigger-strip">${esc(trigger)}</div><p class="muted">Agent is reading the trigger and building a cross-functional plan.</p>`;
  try {
    const data = await api('/api/onboard', {trigger});
    state.onboardRuns++;
    if (!data.needs_resolution) state.autoRuns++;
    renderRun(data, trigger, Boolean(data.matched_rule_id));
    if (!data.needs_resolution) addRoster(data.employee);
    if (data.matched_rule_id) {
      setProcessing('Company Brain matched');
      $('processingState').classList.add('matched');
      await refreshBrain();
      setTimeout(() => playRuleApplied(data), 1000);
    } else {
      setProcessing(data.needs_resolution ? 'Needs decision' : 'Onboarded');
      $('processingState').classList.remove('matched');
    }
    renderMetrics();
  } catch (err) {
    setProcessing('Ready');
    $('resultContent').innerHTML = `<div class="answer-box">Agent is thinking — try again. The product shell is stable; no workflow state was changed.<br><span class="muted">${esc(err.message)}</span></div>`;
  }
}

function renderRun(data, trigger, fast=false) {
  const beats = Array.from(document.querySelectorAll('.beat'));
  beats.forEach(b => b.classList.remove('active', 'matched'));
  const facts = data.facts || {};
  const factKeys = ['full_name','role_title','location','start_date','manager','department'];
  const factDelayBase = fast ? 0 : 800;
  const factStep = fast ? 0 : 150;
  const factsHtml = factKeys.map((k, i) => `
    <div class="fact" style="animation-delay:${factDelayBase + i * factStep}ms"><span>${label(k)}</span><b>${esc(facts[k] || 'pending')}</b></div>`).join('');
  const rowBase = fast ? 400 : 2000;
  const rowStep = fast ? 40 : 200;
  const planRows = (data.plan || []).map((row, i) => `
    <tr class="plan-row" style="animation-delay:${rowBase + i * rowStep}ms">
      <td><b>${esc(row.domain)}</b></td>
      <td>${esc(row.action)}<div class="muted">${esc(row.target)}</div></td>
      <td class="conf-cell"><div class="conf-bar-wrap"><div class="conf-bar ${row.confidence < 85 ? 'low' : ''}" style="width:${esc(row.confidence)}%"></div></div><span class="conf-num">${esc(row.confidence)}%</span></td>
      <td><span class="status ${row.learned ? 'learned' : ''}" data-final-status="${esc(row.status)}">${fast ? esc(row.status) : 'Queued'}</span></td>
      <td class="muted reason-cell">${esc(row.reason)}</td>
    </tr>`).join('');
  const matched = data.matched_rule_id ? `<div class="answer-box matched-box"><span class="status learned">Company Brain matched</span> Stored rule <b>${esc(data.matched_rule_id)}</b> resolved this case automatically. Corrected once, never asks again.</div>` : '';
  const resolution = data.needs_resolution ? renderResolution(data) : '';
  $('resultContent').innerHTML = `
    <div class="trigger-strip">${esc(trigger)}</div>
    ${matched}
    <div class="facts">${factsHtml}</div>
    <table class="plan-table"><thead><tr><th>Domain</th><th>Decision</th><th>Confidence</th><th>Status</th><th>Why</th></tr></thead><tbody>${planRows}</tbody></table>
    ${resolution}`;
  activateBeat('PERCEIVE', 0, data.matched_rule_id);
  activateBeat('REASON', fast ? 400 : 1800, data.matched_rule_id);
  activateBeat('ACT', fast ? 800 : 3000, data.matched_rule_id);
  if (data.needs_resolution) activateBeat('HAND OFF', 3600, false);
  const checkDelay = fast ? 820 : 3100;
  setTimeout(() => flipStatuses(), checkDelay);
  if (data.needs_resolution) {
    const panel = $('resolutionPanel');
    if (panel) panel.style.animationDelay = '3800ms';
  }
  state.lastResultEl = $('resultCard');
}

function activateBeat(name, delay, matched=false) {
  setTimeout(() => {
    const beat = document.querySelector(`.beat[data-beat="${name}"]`);
    if (!beat) return;
    beat.classList.add('active');
    if (matched && name !== 'HAND OFF') beat.classList.add('matched');
  }, delay);
}

function flipStatuses() {
  document.querySelectorAll('.status[data-final-status]').forEach((pill, i) => {
    setTimeout(() => {
      const finalStatus = pill.dataset.finalStatus || pill.textContent;
      pill.textContent = finalStatus.includes('Auto') || finalStatus.includes('Prepared') ? `✓ ${finalStatus}` : finalStatus;
      pill.classList.add('status-pop');
      setTimeout(() => pill.classList.remove('status-pop'), 340);
    }, i * 80);
  });
}

function renderResolution(data) {
  const employeeId = esc(data.employee.id);
  return `<section id="resolutionPanel" class="resolution" data-employee-id="${employeeId}">
    <h3>${esc(data.ambiguity.message)}</h3>
    <p>This sits at the boundary of two departments, so the agent refuses to guess. One decision cascades to IT access, Finance tier, and reporting line.</p>
    <div class="fork-wrap">
      <div class="fork-stem"></div>
      <div class="fork-branches">
        <div class="fork-branch fork-left" data-branch="Sales">
          <div class="fork-label">Sales</div>
          <div class="fork-effects">
            <div class="fork-effect"><span>IT</span> CRM, sales-core</div>
            <div class="fork-effect"><span>Finance</span> sales-field</div>
            <div class="fork-effect"><span>Reports to</span> Sales</div>
          </div>
          <button onclick="resolveAmbiguity('${employeeId}','Sales')">Assign to Sales</button>
        </div>
        <div class="fork-branch fork-right" data-branch="Engineering">
          <div class="fork-label">Engineering</div>
          <div class="fork-effects">
            <div class="fork-effect"><span>IT</span> GitHub, eng-core</div>
            <div class="fork-effect"><span>Finance</span> engineering-tools</div>
            <div class="fork-effect"><span>Reports to</span> Engineering</div>
          </div>
          <button class="secondary" onclick="resolveAmbiguity('${employeeId}','Engineering')">Assign to Engineering</button>
        </div>
      </div>
    </div>
  </section>`;
}

async function resolveAmbiguity(employeeId, department) {
  const panel = $('resolutionPanel');
  if (panel) {
    panel.querySelectorAll('.fork-branch').forEach(branch => {
      branch.classList.toggle('chosen', branch.dataset.branch === department);
      branch.classList.toggle('unchosen', branch.dataset.branch !== department);
    });
    const stem = panel.querySelector('.fork-stem');
    if (stem) stem.classList.add('fade-out');
  }
  setProcessing('Saving decision…');
  const data = await api('/api/resolve', {employee_id: employeeId, department});
  state.rules = data.brain.rules;
  state.roster = data.roster;
  renderRoster();
  setProcessing('Decision learned');
  $('processingState').classList.add('matched');
  setTimeout(() => renderResolvedPanel(data.rule), 300);
  setTimeout(() => { if (panel) playFlyIntoBrain(panel, data.rule); }, 500);
  setTimeout(() => {
    renderBrainNetwork(data.rule.id, true);
    pulseBrainTab();
  }, 950);
}

function renderResolvedPanel(rule) {
  const effects = rule.downstream_effects;
  const panel = $('resolutionPanel');
  if (!panel) return;
  panel.innerHTML = `<h3>Decision saved to Company Brain</h3>
    <p><span class="status learned">Learned</span> ${esc(rule.rule_text)}</p>
    <div class="context-grid">
      <div class="head">IT Groups</div><div class="head">Finance Tier</div><div class="head">Reporting</div><div class="head">Source</div>
      <div>${esc(effects.it_groups.join(', '))}</div><div>${esc(effects.finance_tier)}</div><div>${esc(effects.reporting_line)}</div><div>${esc(rule.source_employee)}</div>
    </div>`;
}

function playFlyIntoBrain(panel, rule) {
  const start = panel.getBoundingClientRect();
  const target = $('brainBadge').getBoundingClientRect();
  const fromX = start.left + start.width * .5;
  const fromY = start.top + start.height * .5;
  const toX = target.left + target.width * .5;
  const toY = target.top + target.height * .5;
  const midX = (fromX + toX) / 2;
  const midY = Math.min(fromY, toY) - 80;
  const token = document.createElement('div');
  token.className = 'fly-token';
  token.textContent = `${rule.source_role} → ${rule.department_resolved}`;
  token.style.setProperty('--from-x', `${fromX}px`);
  token.style.setProperty('--from-y', `${fromY}px`);
  token.style.setProperty('--mid-x', `${midX}px`);
  token.style.setProperty('--mid-y', `${midY}px`);
  token.style.setProperty('--to-x', `${toX}px`);
  token.style.setProperty('--to-y', `${toY}px`);
  $('animationLayer').appendChild(token);
  setTimeout(() => {
    $('brainBadge').classList.add('badge-land');
    setTimeout(() => $('brainBadge').classList.remove('badge-land'), 620);
  }, 900);
  setTimeout(() => {
    renderMetrics();
    landingRipple();
  }, 950);
  token.addEventListener('animationend', () => token.remove());
}

function landingRipple() {
  const rect = $('brainBadge').getBoundingClientRect();
  const ripple = document.createElement('div');
  ripple.className = 'landing-ripple';
  ripple.style.left = `${rect.left + rect.width / 2}px`;
  ripple.style.top = `${rect.top + rect.height / 2}px`;
  $('animationLayer').appendChild(ripple);
  ripple.addEventListener('animationend', () => ripple.remove());
}

function playRuleApplied(data) {
  pulseBrainTab();
  const ruleId = data.matched_rule_id;
  renderBrainNetwork(ruleId, false);
  const echo = document.createElement('div');
  echo.className = 'ghost-echo';
  echo.innerHTML = `<span class="status learned">Company Brain matched</span> Sales Engineer → Sales · Source: Priya Sharma`;
  $('resultCard').appendChild(echo);
  setTimeout(() => echo.remove(), 2100);
  const source = $('resultCard').getBoundingClientRect();
  const target = $('brainTab').getBoundingClientRect();
  const line = document.createElement('div');
  line.style.position = 'fixed';
  line.style.left = '0'; line.style.top = '0'; line.style.width = '100vw'; line.style.height = '100vh';
  line.innerHTML = `<svg width="100%" height="100%"><line class="edge trace" x1="${source.left + source.width * .72}" y1="${source.top + 40}" x2="${target.left + target.width * .5}" y2="${target.top + target.height * .5}" /></svg>`;
  $('animationLayer').appendChild(line);
  setTimeout(() => line.remove(), 1000);
}

function pulseBrainTab() {
  $('brainTab').classList.add('matched');
  setTimeout(() => $('brainTab').classList.remove('matched'), 1200);
}

async function refreshBrain() {
  const res = await fetch('/api/brain');
  const data = await res.json();
  state.rules = data.rules || [];
  renderBrainNetwork();
  renderMetrics();
}

function renderBrainNetwork(highlightId, learnedNew=false) {
  const svg = $('brainNetwork');
  const rules = state.rules || [];
  $('brainEmpty').style.display = rules.length ? 'none' : 'grid';
  $('brainBadge').textContent = rules.length;
  const dots = Array.from({length: 48}, (_, i) => {
    const x = 40 + (i % 12) * 70;
    const y = 36 + Math.floor(i / 12) * 88;
    return `<circle class="backdrop-dot" style="animation-delay:${(i * 137) % 6000}ms" cx="${x}" cy="${y}" r="1.3"/>`;
  }).join('');
  const hub = `<g class="hub" transform="translate(430,180)"><circle r="58"></circle><text y="-4">Company</text><text y="14">Judgment</text></g>`;
  if (!rules.length) { svg.innerHTML = dots + hub; return; }
  const positions = [[430,62],[200,160],[660,160],[270,300],[590,300]];
  let edges = '';
  let synapses = '';
  let nodes = '';
  rules.slice(0,5).forEach((rule, i) => {
    const [x,y] = positions[i];
    const matched = rule.id === highlightId;
    edges += `<line class="edge ${matched ? 'matched' : ''}" data-rule="${esc(rule.id)}" x1="430" y1="180" x2="${x}" y2="${y}"/>`;
    synapses += `<circle class="synapse" r="2.5" fill="#2563eb" opacity="0.35"><animateMotion dur="4s" repeatCount="indefinite" begin="${(i * 1.2).toFixed(1)}s" path="M430,180 L${x},${y}" /></circle>`;
    const cls = matched ? `node ${learnedNew ? 'learned' : 'matched'} pulse` : 'node';
    const enter = matched && learnedNew ? ' node-enter' : '';
    const effects = rule.downstream_effects || {};
    const groups = Array.isArray(effects.it_groups) ? effects.it_groups.slice(0,2).join(' · ') : 'access';
    nodes += `<g id="node-${esc(rule.id)}" class="${cls}" transform="translate(${x},${y})">
      <g class="node-body${enter}">
        <rect class="node-card" rx="20" ry="20" x="-100" y="-48" width="200" height="96"></rect>
        <rect class="node-accent" rx="20" ry="20" x="-100" y="-48" width="6" height="96"></rect>
        <text y="-14" class="node-title">${esc(rule.source_role)} → ${esc(rule.department_resolved)}</text>
        <text class="sub" y="8">Source: ${esc(rule.source_employee)}</text>
        <text class="sub" y="28">${esc(groups)} · ${esc(effects.finance_tier || '')}</text>
      </g>
    </g>`;
  });
  svg.innerHTML = dots + edges + synapses + hub + nodes;
}

async function askBrain() {
  const query = $('brainQuery').value.trim();
  if (!query) return;
  $('queryAnswer').textContent = 'Checking stored decisions…';
  try {
    const data = await api('/api/brain/query', {query});
    const source = data.sources && data.sources[0];
    if (source) {
      renderBrainNetwork(source.id, false);
      recallEdge(source.id);
    }
    await revealAnswer(data.answer, $('queryAnswer'));
    if (source) {
      const meta = document.createElement('div');
      meta.className = 'muted';
      meta.textContent = `Source: ${source.id} · ${source.timestamp}`;
      $('queryAnswer').appendChild(meta);
    }
  } catch (err) {
    $('queryAnswer').textContent = 'No decision recorded for that yet.';
  }
}

function recallEdge(ruleId) {
  document.querySelectorAll('.edge').forEach(e => {
    e.style.transition = 'opacity 300ms';
    e.style.opacity = '0.15';
  });
  setTimeout(() => {
    const edge = document.querySelector(`.edge[data-rule="${CSS.escape(ruleId)}"]`);
    if (edge) {
      edge.style.opacity = '1';
      edge.style.stroke = '#2563eb';
      edge.style.strokeWidth = '2.5';
    }
  }, 600);
  setTimeout(() => {
    document.querySelectorAll('.edge').forEach(e => {
      e.style.opacity = '';
      e.style.stroke = '';
      e.style.strokeWidth = '';
    });
  }, 3000);
}

async function revealAnswer(text, container) {
  const chunks = splitIntoChunks(text || 'No decision recorded for that yet.', 8);
  container.innerHTML = '';
  for (const chunk of chunks) {
    const span = document.createElement('span');
    span.className = 'answer-chunk';
    span.textContent = `${chunk} `;
    container.appendChild(span);
    await sleep(200);
    span.classList.add('visible');
  }
}

function splitIntoChunks(text, size) {
  const words = String(text).split(/\s+/).filter(Boolean);
  const chunks = [];
  for (let i = 0; i < words.length; i += size) chunks.push(words.slice(i, i + size).join(' '));
  return chunks.length ? chunks : [''];
}

function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

async function resetBrain() {
  await api('/api/brain/reset', {});
  state.rules = []; state.roster = []; state.onboardRuns = 0; state.autoRuns = 0;
  renderBrainNetwork(); renderRoster(); renderMetrics();
  $('resultContent').innerHTML = '<p class="muted">Brain reset. Start with Priya to create the first learned decision.</p>';
  $('beats').innerHTML = '';
  setProcessing('Ready');
  $('processingState').classList.remove('matched');
}

async function seedBrain() {
  const data = await api('/api/brain/seed', {});
  state.rules = data.rules || [];
  renderBrainNetwork();
  renderMetrics();
  pulseBrainTab();
  $('queryAnswer').textContent = 'Sample company decisions loaded. Sales Engineer is intentionally still unresolved so Priya can teach the brain live.';
}

function addRoster(employee) {
  if (!state.roster.some(r => r.id === employee.id)) state.roster.push(employee);
  renderRoster();
}

function renderRoster() {
  if (!state.roster.length) { $('roster').className = 'roster empty-row'; $('roster').textContent = 'No employees onboarded yet.'; return; }
  $('roster').className = 'roster';
  $('roster').innerHTML = state.roster.map(r => `<div class="roster-row">
    <b>${esc(r.name)}</b><span>${esc(r.role)}</span><span>${esc(r.location)}</span><span class="status ${r.status === 'Auto-resolved' ? 'learned' : ''}">${esc(r.status)}</span><button class="offboard" disabled>Offboard</button>
  </div>`).join('');
}

function renderMetrics() {
  $('metricEmployees').textContent = state.roster.length;
  $('metricDecisions').textContent = state.rules.length;
  const rate = state.onboardRuns ? Math.round((state.autoRuns / state.onboardRuns) * 100) : 0;
  $('metricAutonomy').textContent = `${rate}%`;
  $('brainBadge').textContent = state.rules.length;
  if ($('brainRuleCount')) $('brainRuleCount').textContent = state.rules.length;
  if ($('brainDeptCount')) $('brainDeptCount').textContent = new Set(state.rules.map(r => r.department_resolved).filter(Boolean)).size;
  if ($('brainUnresolvedCount')) $('brainUnresolvedCount').textContent = state.rules.some(r => String(r.source_role || '').toLowerCase() === 'sales engineer') ? '0' : '1';
}

function setProcessing(text) { $('processingState').textContent = text; }
function label(k) { return k.replace('_', ' '); }
