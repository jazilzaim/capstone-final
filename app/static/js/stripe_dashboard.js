// Argus API - Stripe-Inspired Interactive Frontend Logic

document.addEventListener('DOMContentLoaded', () => {
    initTestModeToggle();
    initRequestInspector();
    initStripeCodeTabs();
    initKeyMasking();
    initQuickSearch();
});

// 1. Stripe Test Mode Toggle Switch
function initTestModeToggle() {
    const toggleBtn = document.getElementById('stripe-testmode-toggle');
    if (!toggleBtn) return;

    // Load saved mode or default to test mode
    const isLive = localStorage.getItem('civic_mode') === 'live';
    setToggleState(toggleBtn, isLive);

    toggleBtn.addEventListener('click', () => {
        const currentlyLive = toggleBtn.classList.contains('live');
        const nextLive = !currentlyLive;
        setToggleState(toggleBtn, nextLive);
        localStorage.setItem('civic_mode', nextLive ? 'live' : 'test');

        showToast(
            nextLive ? 'Live Mode Active: Sourcing directly from Las Vegas, LA, Seattle & Phoenix portals' 
                     : 'Test Mode Active: Using simulated municipal sandbox data with 0ms gateway latency',
            nextLive ? 'success' : 'warning'
        );
    });
}

function setToggleState(el, isLive) {
    const label = el.querySelector('.stripe-testmode-label');
    if (isLive) {
        el.classList.add('live');
        if (label) label.textContent = 'Live mode';
    } else {
        el.classList.remove('live');
        if (label) label.textContent = 'Test mode';
    }
}

// 2. Stripe Request Inspector Drawer
function initRequestInspector() {
    const drawer = document.getElementById('request-drawer');
    const overlay = document.getElementById('drawer-overlay');
    const closeBtn = document.getElementById('drawer-close-btn');

    if (!drawer || !overlay) return;

    function closeDrawer() {
        drawer.classList.remove('open');
        overlay.classList.remove('open');
    }

    if (closeBtn) closeBtn.addEventListener('click', closeDrawer);
    overlay.addEventListener('click', closeDrawer);
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeDrawer();
    });

    // Attach click listeners to all request log rows
    document.querySelectorAll('.clickable-log-row').forEach(row => {
        row.addEventListener('click', () => {
            const reqId = row.getAttribute('data-req-id') || 'req_01HV789A';
            const method = row.getAttribute('data-method') || 'GET';
            const endpoint = row.getAttribute('data-endpoint') || '/api/v1/incidents';
            const status = row.getAttribute('data-status') || '200';
            const latency = row.getAttribute('data-latency') || '14.2';
            const city = row.getAttribute('data-city') || 'las_vegas';
            const queryParams = row.getAttribute('data-params') || '';
            const timestamp = row.getAttribute('data-time') || 'Just now';

            // Populate drawer elements
            const drawerReqId = document.getElementById('drawer-req-id');
            const drawerMethod = document.getElementById('drawer-method');
            const drawerEndpoint = document.getElementById('drawer-endpoint');
            const drawerStatus = document.getElementById('drawer-status');
            const drawerLatency = document.getElementById('drawer-latency');
            const drawerTimestamp = document.getElementById('drawer-timestamp');
            const drawerCity = document.getElementById('drawer-city');
            const drawerParams = document.getElementById('drawer-params');
            const drawerJson = document.getElementById('drawer-json');

            if (drawerReqId) drawerReqId.textContent = reqId;
            if (drawerMethod) drawerMethod.textContent = method;
            if (drawerEndpoint) drawerEndpoint.textContent = endpoint;
            if (drawerLatency) drawerLatency.textContent = `${latency} ms`;
            if (drawerTimestamp) drawerTimestamp.textContent = timestamp;
            if (drawerCity) drawerCity.textContent = city ? city.toUpperCase() : 'ALL CITIES';
            if (drawerParams) drawerParams.textContent = queryParams || '(none)';

            if (drawerStatus) {
                drawerStatus.textContent = `${status} ${status === '200' ? 'OK' : (status === '401' ? 'Unauthorized' : 'Rate Limited')}`;
                drawerStatus.className = `stripe-status-pill stripe-status-${status}`;
            }

            // Generate sample payload matching endpoint
            if (drawerJson) {
                const samplePayload = generateSamplePayload(endpoint, city, status);
                drawerJson.innerHTML = syntaxHighlightJson(JSON.stringify(samplePayload, null, 2));
            }

            drawer.classList.add('open');
            overlay.classList.add('open');
        });
    });
}

function generateSamplePayload(endpoint, city, status) {
    if (status === '401') {
        return {
            "status": "error",
            "error": {
                "code": "UNAUTHORIZED",
                "message": "Invalid or missing API key. Provide via X-API-Key header."
            }
        };
    }
    if (endpoint.includes('permits')) {
        return {
            "status": "success",
            "meta": { "total": 1, "city": city || "seattle", "cached": true, "response_time_ms": 18.2 },
            "data": [{
                "id": "SEA-PRM-678912",
                "city": city || "seattle",
                "permit_type": "Commercial Alteration",
                "status": "Issued",
                "description": "Tenant improvement for retail roastery",
                "valuation_usd": 210000.0,
                "contractor_or_applicant": "Sound Design Co",
                "location": { "address": "1420 5TH AVE", "latitude": 47.6062, "longitude": -122.3321 }
            }]
        };
    }
    if (endpoint.includes('businesses')) {
        return {
            "status": "success",
            "meta": { "total": 1, "city": city || "los_angeles", "cached": true, "response_time_ms": 19.5 },
            "data": [{
                "id": "LA-BIZ-101",
                "city": city || "los_angeles",
                "business_name": "BLUE BOTTLE COFFEE INC",
                "primary_category": "Food Services and Drinking Places",
                "naics_code": "722515",
                "license_number": "000287123",
                "status": "Active"
            }]
        };
    }
    // Default incidents
    return {
        "status": "success",
        "meta": { "total": 1, "city": city || "las_vegas", "cached": true, "response_time_ms": 14.2 },
        "data": [{
            "id": "LV-INC-2026-901",
            "city": city || "las_vegas",
            "city_name": "Las Vegas, NV",
            "source_system": "City of Las Vegas / LVMPD ArcGIS",
            "incident_type": "BURGLARY RESIDENCE",
            "category": "Property Crime",
            "occurred_at": "2026-09-10T14:30:00Z",
            "location": { "address": "2200 E CHARLESTON BLVD", "latitude": 36.159, "longitude": -115.118 },
            "status": "Report Filed"
        }]
    };
}

// 3. Multi-Language Code Tabs (Stripe Split-Screen Terminal)
function initStripeCodeTabs() {
    const tabs = document.querySelectorAll('.stripe-lang-tab');
    const codeDisplay = document.getElementById('stripe-code-content');
    if (!tabs.length || !codeDisplay) return;

    const snippets = {
        'curl': `curl -X GET "https://api.argus.dev/api/v1/incidents?city=all&category=Property+Crime" \\
  -H "X-API-Key: argus_live_7x89q2m10k4..." \\
  -H "Accept: application/json"`,
        'python': `import requests

url = "https://api.argus.dev/api/v1/incidents"
headers = {
    "X-API-Key": "argus_live_7x89q2m10k4..."
}
params = {
    "city": "all",
    "category": "Property Crime"
}

response = requests.get(url, headers=headers, params=params)
data = response.json()
print(f"Retrieved {len(data['data'])} incidents across 4 cities")`,
        'node': `const response = await fetch("https://api.argus.dev/api/v1/incidents?city=all", {
  headers: {
    "X-API-Key": "argus_live_7x89q2m10k4...",
    "Accept": "application/json"
  }
});

const data = await response.json();
console.log(data.data);`,
        'go': `package main

import (
	"fmt"
	"net/http"
	"io"
)

func main() {
	req, _ := http.NewRequest("GET", "https://api.argus.dev/api/v1/incidents?city=all", nil)
	req.Header.Set("X-API-Key", "argus_live_7x89q2m10k4...")
	
	client := &http.Client{}
	resp, _ := client.Do(req)
	defer resp.Body.Close()
	
	body, _ := io.ReadAll(resp.Body)
	fmt.Println(string(body))
}`
    };

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            const lang = tab.getAttribute('data-lang');
            codeDisplay.textContent = snippets[lang] || snippets['curl'];
        });
    });
}

// 4. API Key Masking & Reveal
function initKeyMasking() {
    document.querySelectorAll('.key-reveal-toggle').forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.getAttribute('data-target');
            const input = document.getElementById(targetId);
            if (!input) return;

            if (input.type === 'password') {
                input.type = 'text';
                btn.textContent = 'Hide';
            } else {
                input.type = 'password';
                btn.textContent = 'Reveal';
            }
        });
    });
}

// 5. Quick Search Focus Shortcut
function initQuickSearch() {
    const searchInput = document.getElementById('stripe-search-input');
    if (!searchInput) return;

    document.addEventListener('keydown', (e) => {
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
            e.preventDefault();
            searchInput.focus();
        }
    });
}

// 6. Toast Notification Helper
function showToast(msg, type = 'info') {
    let toast = document.getElementById('stripe-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'stripe-toast';
        toast.style.cssText = `
            position: fixed;
            bottom: 24px;
            right: 24px;
            padding: 12px 20px;
            border-radius: 8px;
            color: #fff;
            font-size: 0.88rem;
            font-weight: 500;
            z-index: 9999;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            opacity: 0;
            transform: translateY(10px);
            font-family: var(--font-stripe, sans-serif);
        `;
        document.body.appendChild(toast);
    }

    toast.style.background = type === 'success' ? '#065f46' : (type === 'warning' ? '#78350f' : '#1e1b4b');
    toast.style.border = `1px solid ${type === 'success' ? '#10b981' : (type === 'warning' ? '#f59e0b' : '#6366f1')}`;
    toast.textContent = msg;
    toast.style.opacity = '1';
    toast.style.transform = 'translateY(0)';

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
    }, 3500);
}
