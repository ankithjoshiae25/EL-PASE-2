document.addEventListener('DOMContentLoaded', () => {
    console.log("App initialized");

    // Initialize Map - Centered on Bangalore
    const map = L.map('map', {
        zoomControl: false
    }).setView([12.9716, 77.5946], 13);

    // Google Maps Hybrid Tiles
    L.tileLayer('http://{s}.google.com/vt/lyrs=s,h&x={x}&y={y}&z={z}', {
        maxZoom: 20,
        subdomains: ['mt0', 'mt1', 'mt2', 'mt3'],
        attribution: '&copy; Google Maps'
    }).addTo(map);

    // Load Metro Stations
    async function loadMetroStations() {
        try {
            const response = await fetch('/api/metro-stations');
            const data = await response.json();
            if (data.stations) {
                const metroIcon = L.divIcon({
                    className: 'metro-icon',
                    html: '<div style="background:white; border-radius:50%; width:24px; height:24px; display:flex; align-items:center; justify-content:center; border:2px solid #6C63FF; box-shadow:0 2px 4px rgba(0,0,0,0.3);">🚇</div>',
                    iconSize: [24, 24],
                    iconAnchor: [12, 12]
                });

                data.stations.forEach(station => {
                    L.marker([station.lat, station.lon], { icon: metroIcon })
                        .bindPopup(`<strong>${station.name}</strong><br>Metro Station`)
                        .addTo(map);
                });
            }
        } catch (e) {
            console.warn("Failed to load metro stations", e);
        }
    }
    loadMetroStations();

    // Load Metro Lines (Tracks)
    let metroLinesData = [];
    async function loadMetroLines() {
        try {
            const response = await fetch('/api/metro-lines');
            const data = await response.json();
            if (data.lines) {
                metroLinesData = data.lines;
                console.log("Loaded metro lines:", metroLinesData.length);
            }
        } catch (e) {
            console.warn("Failed to load metro lines", e);
        }
    }
    loadMetroLines();

    // Load Bus Stops
    async function loadBusStops() {
        try {
            const response = await fetch('/api/bus-stops');
            const data = await response.json();
            if (data.stops) {
                const busIcon = L.divIcon({
                    className: 'bus-icon',
                    html: '<div style="background:white; border-radius:50%; width:20px; height:20px; display:flex; align-items:center; justify-content:center; border:2px solid #F59E0B; box-shadow:0 2px 4px rgba(0,0,0,0.3); font-size: 12px;">🚌</div>',
                    iconSize: [20, 20],
                    iconAnchor: [10, 10]
                });

                const busLayer = L.featureGroup();

                data.stops.forEach(stop => {
                    let popupContent = `<strong>${stop.name}</strong><br>Bus Stop`;
                    if (stop.routes && stop.routes.length > 0) {
                        popupContent += `<br><small>Routes: ${stop.routes.join(', ')}</small>`;
                    }
                    L.marker([stop.lat, stop.lon], { icon: busIcon })
                        .bindPopup(popupContent)
                        .addTo(busLayer);
                });

                busLayer.addTo(map);
            }
        } catch (e) {
            console.warn("Failed to load bus stops", e);
        }
    }
    loadBusStops();

    // UI Elements
    const searchBtn = document.getElementById('search-btn');
    const destinationInput = document.getElementById('destination-input');
    const resultsPanel = document.getElementById('results-panel');
    const routesList = document.getElementById('routes-list');
    const startInput = document.getElementById('start-input');

    // State
    let selectedStartCoords = null;
    let selectedDestCoords = null;
    let currentRouteLayer = null;

    // Global Setters for Map Popup
    window.setStart = (lat, lng, addrEncoded) => {
        const addr = decodeURIComponent(addrEncoded);
        startInput.value = addr;
        selectedStartCoords = [lat, lng];
        map.closePopup();
        L.marker([lat, lng], { icon: L.divIcon({ className: 'custom-icon', html: '🟢' }) }).addTo(map);
        console.log("Start set to:", addr, lat, lng);
    };

    window.setDest = (lat, lng, addrEncoded) => {
        const addr = decodeURIComponent(addrEncoded);
        destinationInput.value = addr;
        selectedDestCoords = [lat, lng];
        map.closePopup();
        L.marker([lat, lng], { icon: L.divIcon({ className: 'custom-icon', html: '🔴' }) }).addTo(map);
        console.log("Dest set to:", addr, lat, lng);
    };

    // Map Click Handler
    map.on('click', async (e) => {
        const { lat, lng } = e.latlng;
        let address = `${lat.toFixed(4)}, ${lng.toFixed(4)}`;

        try {
            const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`);
            const data = await response.json();
            if (data && data.display_name) {
                address = data.display_name.split(',').slice(0, 3).join(',');
            }
        } catch (err) {
            console.warn('Reverse geocode failed', err);
        }

        const safeAddr = encodeURIComponent(address);

        const popupContent = `
            <div style="text-align:center">
                <strong>${address}</strong><br>
                <div style="margin-top:8px; display:flex; gap:8px; justify-content:center">
                    <button onclick="setStart(${lat}, ${lng}, '${safeAddr}')" 
                        style="background:#10B981; color:white; border:none; padding:4px 8px; border-radius:4px; cursor:pointer">
                        Set Start 🟢
                    </button>
                    <button onclick="setDest(${lat}, ${lng}, '${safeAddr}')" 
                        style="background:#EF4444; color:white; border:none; padding:4px 8px; border-radius:4px; cursor:pointer">
                        Set Dest 🔴
                    </button>
                </div>
            </div>
        `;

        L.popup()
            .setLatLng(e.latlng)
            .setContent(popupContent)
            .openOn(map);
    });

    // Clear coords on manual input
    startInput.addEventListener('input', () => selectedStartCoords = null);
    destinationInput.addEventListener('input', () => selectedDestCoords = null);

    // Search Handler - Exposed to Window
    window.handleSearch = async function () {
        console.log("Search clicked");
        const query = destinationInput.value;
        const startQuery = startInput.value;

        if (!query) {
            alert("Please enter a destination");
            return;
        }

        searchBtn.textContent = '...';
        searchBtn.disabled = true;

        try {
            let url = `/api/search?destination=${encodeURIComponent(query)}&start=${encodeURIComponent(startQuery)}`;

            if (selectedStartCoords) {
                url += `&s_lat=${selectedStartCoords[0]}&s_lon=${selectedStartCoords[1]}`;
            }
            if (selectedDestCoords) {
                url += `&d_lat=${selectedDestCoords[0]}&d_lon=${selectedDestCoords[1]}`;
            }

            // Add Preferences
            try {
                const prefs = JSON.parse(localStorage.getItem('userPreferences') || '{}');
                if (prefs.priority) url += `&preference=${encodeURIComponent(prefs.priority)}`;
                if (prefs.mode) url += `&mode_preference=${encodeURIComponent(prefs.mode)}`;
                if (prefs.maxWalk) url += `&max_walk=${encodeURIComponent(prefs.maxWalk)}`;
            } catch (e) { console.warn("Error reading prefs", e); }


            console.log("Fetching:", url);
            const response = await fetch(url);
            if (!response.ok) throw new Error("Network response was not ok");

            const data = await response.json();
            console.log("Data received:", data);

            renderResults(data.routes, data.total_distance_km);
            resultsPanel.classList.remove('hidden');

            if (data.start_coords && data.destination_coords) {
                const group = new L.featureGroup([
                    L.marker(data.start_coords).bindPopup("Start"),
                    L.marker(data.destination_coords).bindPopup("Destination")
                ]);
                map.fitBounds(group.getBounds().pad(0.2));
            }

        } catch (error) {
            console.error('Search failed:', error);
            alert('Failed to fetch routes. Please try again.');
        } finally {
            searchBtn.textContent = 'Go';
            searchBtn.disabled = false;
        }
    };

    // Keep Enter key listeners
    destinationInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            closeAllLists();
            window.handleSearch();
        }
    });
    startInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            closeAllLists();
            window.handleSearch();
        }
    });

    // --- Autocomplete Logic ---

    function debounce(func, wait) {
        let timeout;
        return function (...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }

    function closeAllLists(elmnt) {
        const items = document.getElementsByClassName("autocomplete-items");
        for (let i = 0; i < items.length; i++) {
            if (elmnt != items[i] && elmnt != startInput && elmnt != destinationInput) {
                items[i].parentNode.removeChild(items[i]);
            }
        }
    }

    // Close autocomplete when clicking elsewhere
    document.addEventListener("click", function (e) {
        closeAllLists(e.target);
    });

    async function handleInput(inp, type) {
        const val = inp.value;
        closeAllLists();
        if (!val || val.length < 2) return;

        // Create container for items
        const listDiv = document.createElement("div");
        listDiv.setAttribute("id", inp.id + "autocomplete-list");
        listDiv.setAttribute("class", "autocomplete-items glass-panel");
        inp.parentNode.appendChild(listDiv);

        try {
            const response = await fetch(`/api/autocomplete?query=${encodeURIComponent(val)}`);
            const data = await response.json();

            data.results.forEach(item => {
                const itemDiv = document.createElement("div");
                itemDiv.className = "autocomplete-item";

                let icon = '📍';
                if (item.type === 'Metro Station') icon = '🚇';
                if (item.type === 'Bus Stop') icon = '🚌';
                if (item.type === 'Location') icon = '🏙️';

                itemDiv.innerHTML = `
                    <div class="item-icon">${icon}</div>
                    <div class="item-info">
                        <div class="item-name">${item.name}</div>
                        <div class="item-type">${item.type}</div>
                    </div>
                `;

                itemDiv.addEventListener("click", function () {
                    inp.value = item.name;

                    if (type === 'start') {
                        selectedStartCoords = [item.lat, item.lon];
                        console.log("Start Autoselected:", item);
                    } else {
                        selectedDestCoords = [item.lat, item.lon];
                        console.log("Dest Autoselected:", item);
                    }

                    closeAllLists();
                });

                listDiv.appendChild(itemDiv);
            });

        } catch (e) {
            console.warn("Autocomplete fetch error", e);
        }
    }

    startInput.addEventListener("input", debounce(function () {
        selectedStartCoords = null; // Clear prev selection
        handleInput(this, 'start');
    }, 400));

    destinationInput.addEventListener("input", debounce(function () {
        selectedDestCoords = null; // Clear prev selection
        handleInput(this, 'dest');
    }, 400));

    // Render Results
    function renderResults(routes, distance) {
        routesList.innerHTML = '';

        // Update Header with Distance
        const header = document.querySelector('.results-header');
        if (header) {
            header.innerHTML = `
                <div>
                    <h2>Best Routes</h2>
                    <div style="font-size: 0.9rem; color: var(--accent-color); margin-top: 4px;">
                        📏 Distance: ${distance} km
                    </div>
                </div>
                <span class="badge ai-badge">AI Recommended</span>
            `;
        }

        if (currentRouteLayer) {
            map.removeLayer(currentRouteLayer);
            currentRouteLayer = null;
        }

        routes.forEach((route, index) => {
            const card = document.createElement('div');
            card.className = 'route-card';
            card.style.animationDelay = `${index * 0.1}s`;

            let icon = '🚗';
            if (route.mode.includes('Metro')) icon = '🚇';
            if (route.mode.includes('Bus')) icon = '🚌';
            if (route.mode.includes('Walk')) icon = '🚶';
            if (route.mode.includes('Auto') || route.mode.includes('Namma Yatri')) icon = '🛺';
            if (route.mode.includes('Moto')) icon = '🛵';
            if (route.mode.includes('Cab')) icon = '🚕';

            let segmentsHtml = '';
            if (route.segments) {
                segmentsHtml = `<div class="route-segments-info">`;
                route.segments.forEach(seg => {
                    let segIcon = '🔹';
                    if (seg.mode === 'walk') segIcon = '🚶';
                    if (seg.mode === 'metro') segIcon = '🚇';
                    if (seg.mode === 'bus') segIcon = '🚌';
                    if (seg.mode === 'auto') segIcon = '🛺';
                    if (seg.mode === 'cab') segIcon = '🚕';

                    segmentsHtml += `
                        <div class="segment-step">
                            <div class="segment-icon">${segIcon}</div>
                            <div class="segment-text">
                                <div>${seg.instruction || ''}</div>
                                <div class="segment-highlight">${seg.identifier || ''}</div>
                            </div>
                        </div>
                    `;
                });
                segmentsHtml += `</div>`;
            }

            // Sub-Options Logic (Cab Direct)
            let extraHtml = '';
            if (route.sub_options) {
                extraHtml += `<div class="sub-options-container" style="margin-top:8px; padding-top:8px; border-top:1px solid rgba(255,255,255,0.1);">`;
                route.sub_options.forEach(opt => {
                    extraHtml += `
                        <div style="display:flex; justify-content:space-between; font-size:0.9rem; margin-bottom:4px;">
                            <span>${opt.name}</span>
                            <span style="font-weight:600;">₹${opt.cost}</span>
                        </div>
                    `;
                });
                extraHtml += `</div>`;
            }
            // Sub-Costs Logic (Metro Breakdown)
            else if (route.sub_costs) {
                const sc = route.sub_costs;
                extraHtml += `<div class="sub-options-container" style="margin-top:8px; padding-top:8px; border-top:1px solid rgba(255,255,255,0.1);">`;

                if (sc.leg1_auto > 0) {
                    extraHtml += `
                        <div style="display:flex; justify-content:space-between; font-size:0.85rem; margin-bottom:2px; color:var(--text-secondary);">
                            <span>Auto to Station</span>
                            <span>₹${sc.leg1_auto}</span>
                        </div>`;
                }
                if (sc.metro > 0) {
                    extraHtml += `
                        <div style="display:flex; justify-content:space-between; font-size:0.85rem; margin-bottom:2px; color:var(--text-secondary);">
                            <span>Metro Fare</span>
                            <span>₹${sc.metro}</span>
                        </div>`;
                }
                if (sc.leg3_auto > 0) {
                    extraHtml += `
                        <div style="display:flex; justify-content:space-between; font-size:0.85rem; margin-bottom:2px; color:var(--text-secondary);">
                            <span>Auto from Station</span>
                            <span>₹${sc.leg3_auto}</span>
                        </div>`;
                }
                extraHtml += `</div>`;
            }

            card.innerHTML = `
                <div class="route-header">
                    <div class="route-mode">
                        <span>${icon}</span>
                        <span>${route.mode}</span>
                    </div>
                    <div class="route-cost">₹${route.cost}</div>
                </div>
                <div class="route-details">
                    <div class="route-meta">
                        <span>⏱ ${route.duration} min</span>
                        <span class="safety-rating">🛡 ${route.safety}</span>
                    </div>
                </div>
                ${extraHtml}
                ${segmentsHtml}
            `;

            card.addEventListener('click', () => {
                drawRoute(route);
                document.querySelectorAll('.route-card').forEach(c => c.classList.remove('selected'));
                card.classList.add('selected');
            });

            routesList.appendChild(card);
        });

        if (routes.length > 0) {
            drawRoute(routes[0]);
            routesList.firstElementChild.classList.add('selected');
        }
    }

    // Draw Route
    async function drawRoute(route) {
        // Clear previous layer immediately to prevent overlap during async fetch
        if (currentRouteLayer) {
            map.removeLayer(currentRouteLayer);
            currentRouteLayer = null;
        }

        const layers = [];
        // Create a temporary group for this specific render to avoid race conditions
        const newLayerGroup = L.featureGroup();

        if (route.segments) {
            for (const segment of route.segments) {
                let color = '#6C63FF';
                let dashArray = null;

                if (segment.mode === 'walk') { color = '#22D3EE'; dashArray = '5, 10'; }
                if (segment.mode === 'metro') color = '#A855F7';
                if (segment.mode === 'bus') color = '#3B82F6';
                if (segment.mode === 'auto') color = '#F59E0B';
                if (segment.mode === 'cab' || segment.mode === 'moto') color = '#10B981';

                let latlngs = [segment.from, segment.to];

                // --- PATH FINDING LOGIC ---

                // 1. OSRM for Road/Walk
                if (['walk', 'auto', 'cab', 'moto', 'bike', 'bus'].includes(segment.mode)) {
                    // Check if we already have cached geometry for this segment
                    if (segment.cachedGeometry) {
                        latlngs = segment.cachedGeometry;
                    }
                    else {
                        try {
                            const start = `${segment.from[1]},${segment.from[0]}`;
                            const end = `${segment.to[1]},${segment.to[0]}`;
                            const profile = segment.mode === 'walk' ? 'walking' : 'driving';

                            // console.log(`Fetching OSRM: /api/proxy/osrm?start=${start}&end=${end}&mode=${profile}`);
                            const response = await fetch(`/api/proxy/osrm?start=${start}&end=${end}&mode=${profile}`);
                            const data = await response.json();

                            if (data.routes && data.routes[0]) {
                                latlngs = data.routes[0].geometry.coordinates.map(coord => [coord[1], coord[0]]);
                                segment.cachedGeometry = latlngs; // Cache it!
                            }
                        } catch (e) {
                            console.warn('OSRM fetch failed', e);
                        }
                    }
                }

                // 2. Metro Line Slicing from GeoJSON
                else if (segment.mode === 'metro' && metroLinesData.length > 0) {
                    if (segment.cachedGeometry) {
                        latlngs = segment.cachedGeometry;
                        // Identify color again just in case (though logical consistency suggests it should match)
                        const lineColorHint = (segment.line_color || '').toLowerCase();
                        if (lineColorHint.includes('purple')) color = '#9333EA';
                        if (lineColorHint.includes('green')) color = '#16A34A';
                    } else {
                        // ... (Existing Metro slicing logic) ...
                        const lineColorHint = (segment.line_color || '').toLowerCase();
                        const targetLine = metroLinesData.find(line => line.color.toLowerCase() === lineColorHint);

                        if (targetLine) {
                            const findClosestIndex = (target, path) => {
                                let minD = Infinity;
                                let idx = -1;
                                path.forEach((pt, i) => {
                                    const d = (pt[0] - target[0]) ** 2 + (pt[1] - target[1]) ** 2;
                                    if (d < minD) { minD = d; idx = i; }
                                });
                                return idx;
                            };

                            const i1 = findClosestIndex(segment.from, targetLine.path);
                            const i2 = findClosestIndex(segment.to, targetLine.path);

                            if (i1 !== -1 && i2 !== -1) {
                                const startIdx = Math.min(i1, i2);
                                const endIdx = Math.max(i1, i2);
                                latlngs = targetLine.path.slice(startIdx, endIdx + 1);

                                segment.cachedGeometry = latlngs; // Cache it!

                                if (targetLine.color === 'purple') color = '#9333EA';
                                if (targetLine.color === 'green') color = '#16A34A';
                            }
                        }
                    }
                }

                newLayerGroup.addLayer(L.polyline(latlngs, { color, weight: 6, opacity: 0.9, dashArray, lineCap: 'round' }));
                newLayerGroup.addLayer(L.circleMarker(segment.to, { radius: 5, color, fillColor: '#fff', fillOpacity: 1 }));
            }
        }

        // Final cleanup before adding new group (in case user clicked again fast)
        if (currentRouteLayer) {
            map.removeLayer(currentRouteLayer);
        }

        currentRouteLayer = newLayerGroup;
        currentRouteLayer.addTo(map);
        map.fitBounds(currentRouteLayer.getBounds().pad(0.2));
    }
});
