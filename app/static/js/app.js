// Argus API - Developer Portal Client Logic

document.addEventListener('DOMContentLoaded', () => {
    initPlayground();
    initKeyGenerator();
    initCopyButtons();
});

// 1. API Playground Logic
function initPlayground() {
    const runBtn = document.getElementById('btn-run-query');
    if (!runBtn) return;

    const endpointSelect = document.getElementById('input-endpoint');
    const citySelect = document.getElementById('input-city');
    const queryInput = document.getElementById('input-query');
    const categorySelect = document.getElementById('input-category');
    const limitInput = document.getElementById('input-limit');
    const apiKeyInput = document.getElementById('input-api-key');

    const urlDisplay = document.getElementById('display-url');
    const statusBadge = document.getElementById('response-status');
    const latencyBadge = document.getElementById('response-latency');
    const jsonOutput = document.getElementById('json-output');

    // Code snippet blocks
    const curlOutput = document.getElementById('curl-output');
    const pythonOutput = document.getElementById('python-output');
    const jsOutput = document.getElementById('js-output');

    function buildUrl() {
        const endpoint = endpointSelect.value;
        const city = citySelect.value;
        const q = queryInput.value.trim();
        const cat = categorySelect ? categorySelect.value : '';
        const limit = limitInput.value.trim() || '10';

        const params = new URLSearchParams();
        if (city && city !== 'all') params.append('city', city);
        if (q) params.append('query', q);
        if (cat && cat !== 'all' && endpoint === '/api/v1/incidents') params.append('category', cat);
        if (limit) params.append('limit', limit);

        const paramStr = params.toString() ? '?' + params.toString() : '';
        const path = `${endpoint}${paramStr}`;
        if (urlDisplay) urlDisplay.textContent = path;

        updateSnippets(path, apiKeyInput.value.trim());
        return path;
    }

    function updateSnippets(path, key) {
        const fullUrl = `${window.location.origin}${path}`;
        const authHeader = key ? `-H "X-API-Key: ${key}"` : '';

        if (curlOutput) {
            curlOutput.textContent = `curl -X GET "${fullUrl}" \\\n  -H "Accept: application/json" ${authHeader ? '\\\n  ' + authHeader : ''}`;
        }
        if (pythonOutput) {
            pythonOutput.textContent = `import requests\n\nurl = "${fullUrl}"\nheaders = {\n    "Accept": "application/json",\n    "X-API-Key": "${key || 'YOUR_API_KEY'}"\n}\n\nresponse = requests.get(url, headers=headers)\ndata = response.json()\nprint(data)`;
        }
        if (jsOutput) {
            jsOutput.textContent = `const response = await fetch("${fullUrl}", {\n  headers: {\n    "Accept": "application/json",\n    "X-API-Key": "${key || 'YOUR_API_KEY'}"\n  }\n});\nconst data = await response.json();\nconsole.log(data);`;
        }
    }

    // Attach change listeners to dynamically update URL & code snippets
    [endpointSelect, citySelect, queryInput, categorySelect, limitInput, apiKeyInput].forEach(el => {
        if (el) {
            el.addEventListener('input', buildUrl);
            el.addEventListener('change', buildUrl);
        }
    });

    // Execute request
    runBtn.addEventListener('click', async () => {
        const path = buildUrl();
        const key = apiKeyInput.value.trim();

        runBtn.disabled = true;
        runBtn.textContent = 'Executing...';
        if (jsonOutput) jsonOutput.textContent = 'Loading response from municipal connectors...';

        const startTime = performance.now();
        try {
            const headers = { 'Accept': 'application/json' };
            if (key) headers['X-API-Key'] = key;

            const res = await fetch(path, { headers });
            const latency = Math.round(performance.now() - startTime);
            const data = await res.json();

            // Status badge
            if (statusBadge) {
                statusBadge.textContent = `${res.status} ${res.statusText}`;
                statusBadge.className = `badge ${res.ok ? 'badge-online' : 'badge-degraded'}`;
            }

            // Latency badge
            if (latencyBadge) {
                latencyBadge.textContent = `${latency} ms`;
            }

            // Syntax-highlighted output
            if (jsonOutput) {
                jsonOutput.innerHTML = syntaxHighlightJson(JSON.stringify(data, null, 2));
            }
        } catch (err) {
            if (statusBadge) {
                statusBadge.textContent = 'Network Error';
                statusBadge.className = 'badge badge-degraded';
            }
            if (jsonOutput) {
                jsonOutput.textContent = `Failed to fetch: ${err.message}`;
            }
        } finally {
            runBtn.disabled = false;
            runBtn.textContent = 'Execute Request';
        }
    });

    // Initial build and run once
    buildUrl();
    runBtn.click();

    // Tab switching
    const tabs = document.querySelectorAll('.console-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            const targetId = tab.getAttribute('data-target');
            document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
            const targetEl = document.getElementById(targetId);
            if (targetEl) targetEl.style.display = 'block';
        });
    });
}

// 2. Syntax Highlighter for JSON
function syntaxHighlightJson(json) {
    if (!json) return '';
    json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
        let cls = 'json-number';
        if (/^"/.test(match)) {
            if (/:$/.test(match)) {
                cls = 'json-key';
            } else {
                cls = 'json-string';
            }
        } else if (/true|false/.test(match)) {
            cls = 'json-boolean';
        } else if (/null/.test(match)) {
            cls = 'json-null';
        }
        return '<span class="' + cls + '">' + match + '</span>';
    });
}

// 3. API Key Self-Service Generator
function initKeyGenerator() {
    const keyForm = document.getElementById('form-generate-key');
    if (!keyForm) return;

    const resultBox = document.getElementById('key-result-box');
    const generatedKeyInput = document.getElementById('generated-key-val');
    const keyTierBadge = document.getElementById('generated-key-tier');

    keyForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = document.getElementById('key-name').value.trim();
        const email = document.getElementById('key-email').value.trim();
        const tier = document.getElementById('key-tier').value;

        try {
            const resp = await fetch('/api/v1/keys', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, email, tier })
            });
            const data = await resp.json();

            if (resp.ok && data.data) {
                if (generatedKeyInput) generatedKeyInput.value = data.data.api_key;
                if (keyTierBadge) keyTierBadge.textContent = `${data.data.tier.toUpperCase()} TIER (${data.data.rate_limit_per_min} req/min)`;
                if (resultBox) resultBox.style.display = 'block';
                resultBox.scrollIntoView({ behavior: 'smooth' });
            } else {
                alert(data.error ? data.error.message : 'Error generating key.');
            }
        } catch (err) {
            alert('Request failed: ' + err.message);
        }
    });

    // Verification tool
    const verifyBtn = document.getElementById('btn-verify-key');
    const verifyInput = document.getElementById('verify-key-input');
    const verifyOutput = document.getElementById('verify-output');

    if (verifyBtn && verifyInput && verifyOutput) {
        verifyBtn.addEventListener('click', async () => {
            const key = verifyInput.value.trim();
            if (!key) return;
            try {
                const resp = await fetch('/api/v1/keys/verify', {
                    headers: { 'X-API-Key': key }
                });
                const data = await resp.json();
                verifyOutput.style.display = 'block';
                verifyOutput.innerHTML = syntaxHighlightJson(JSON.stringify(data, null, 2));
            } catch (err) {
                verifyOutput.style.display = 'block';
                verifyOutput.textContent = 'Verification error: ' + err.message;
            }
        });
    }
}

// 4. One-Click Copy Buttons
function initCopyButtons() {
    document.querySelectorAll('.copy-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const targetSelector = btn.getAttribute('data-clipboard-target');
            let textToCopy = '';
            if (targetSelector) {
                const target = document.querySelector(targetSelector);
                textToCopy = target ? (target.value || target.textContent) : '';
            } else {
                textToCopy = btn.getAttribute('data-clipboard-text') || '';
            }

            if (textToCopy) {
                navigator.clipboard.writeText(textToCopy).then(() => {
                    const originalText = btn.textContent;
                    btn.textContent = 'Copied!';
                    btn.style.borderColor = '#10b981';
                    setTimeout(() => {
                        btn.textContent = originalText;
                        btn.style.borderColor = '';
                    }, 2000);
                });
            }
        });
    });
}
