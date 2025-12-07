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
        if (e.key === 'Enter') window.handleSearch();
    });
    startInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') window.handleSearch();
    });

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
            if (route.mode.includes('Auto')) icon = '🛺';
            if (route.mode.includes('Moto')) icon = '🛵';

            let segmentsHtml = '';
            if (route.segments) {
                segmentsHtml = `<div class="route-segments-info">`;
                route.segments.forEach(seg => {
                    let segIcon = '🔹';
                    if (seg.mode === 'walk') segIcon = '🚶';
                    if (seg.mode === 'metro') segIcon = '🚇';
                    if (seg.mode === 'bus') segIcon = '🚌';

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
                    <div class="ai-score">AI Score: ${route.ai_score}/10</div>
                </div>
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
        if (currentRouteLayer) {
            map.removeLayer(currentRouteLayer);
        }

        const layers = [];

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

                if (['walk', 'auto', 'cab', 'moto', 'bike', 'bus'].includes(segment.mode)) {
                    try {
                        const start = `${segment.from[1]},${segment.from[0]}`;
                        const end = `${segment.to[1]},${segment.to[0]}`;
                        const profile = segment.mode === 'walk' ? 'walking' : 'driving';

                        const response = await fetch(`https://router.project-osrm.org/route/v1/${profile}/${start};${end}?overview=full&geometries=geojson`);
                        const data = await response.json();

                        if (data.routes && data.routes[0]) {
                            latlngs = data.routes[0].geometry.coordinates.map(coord => [coord[1], coord[0]]);
                        }
                    } catch (e) {
                        console.warn('OSRM fetch failed', e);
                    }
                }

                layers.push(L.polyline(latlngs, { color, weight: 5, opacity: 0.8, dashArray }));
                layers.push(L.circleMarker(segment.to, { radius: 4, color, fillColor: '#fff', fillOpacity: 1 }));
            }
        }

        currentRouteLayer = L.featureGroup(layers).addTo(map);
        map.fitBounds(currentRouteLayer.getBounds().pad(0.2));
    }
});
