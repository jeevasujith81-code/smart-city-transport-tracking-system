/**
 * CityTrack - Realtime Public Transport Tracking Frontend Logic
 * Enhanced with Trip Planner (A to B), Crowd Level Density Indicators, and Stop Arrival Alarms.
 */

const API_BASE = 'http://localhost:8000/api/v1';
const WS_URL = 'ws://localhost:8000/api/v1/ws/buses';

// State Management
let map;
let busMarkers = {}; // bus_id -> L.marker
let stopMarkers = {}; // stop_id -> L.marker
let routePolylines = {}; // route_id -> L.polyline
let activeRouteId = 'ALL';
let routesData = [];
let stopsData = [];
let busesData = [];
let selectedStopId = null;
let plannedRoutePolyline = null;

// Driver Telemetry State
let isDriverTracking = false;
let driverWatchId = null;
let driverPingsSent = 0;
let driverSimInterval = null;
let driverCrowdLevel = 'LOW';

// Arrival Alarm State
let activeAlarmStopId = null;
let activeAlarmStopName = null;
let alarmTriggeredBuses = new Set();

// WebSocket Instance
let wsSocket = null;

// Initialize App on DOM Load
document.addEventListener('DOMContentLoaded', () => {
  initMap();
  loadCityData();
  initWebSocket();
  startFallbackPolling();
});

// Helper: Haversine distance in kilometers
function getHaversineDistance(lat1, lon1, lat2, lon2) {
  const R = 6371; // km
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a = 
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

// Helper: Crowd Level HTML Badge
function getCrowdBadgeHTML(level) {
  const lvl = (level || 'LOW').toUpperCase();
  if (lvl === 'MEDIUM') {
    return `<span class="crowd-badge crowd-badge-MEDIUM"><i class="fa-solid fa-users"></i> Standing</span>`;
  } else if (lvl === 'HIGH') {
    return `<span class="crowd-badge crowd-badge-HIGH"><i class="fa-solid fa-user-group"></i> Busy</span>`;
  } else if (lvl === 'FULL') {
    return `<span class="crowd-badge crowd-badge-FULL"><i class="fa-solid fa-ban"></i> Full</span>`;
  }
  return `<span class="crowd-badge crowd-badge-LOW"><i class="fa-solid fa-user-check"></i> Seats</span>`;
}

// Tab Switcher
function switchTab(tabName) {
  const tabs = ['passenger', 'driver', 'admin'];
  tabs.forEach(t => {
    const view = document.getElementById(`view-${t}`);
    const btn = document.getElementById(`tab-${t}`);
    if (t === tabName) {
      view.classList.remove('hidden');
      btn.className = "tab-btn px-4 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 bg-indigo-600 text-white shadow";
    } else {
      view.classList.add('hidden');
      btn.className = "tab-btn px-4 py-1.5 rounded-lg text-sm font-medium text-slate-400 hover:text-slate-200 transition-all duration-200";
    }
  });

  if (tabName === 'passenger' && map) {
    setTimeout(() => map.invalidateSize(), 200);
  }
  if (tabName === 'driver') {
    populateDriverBusSelect();
  }
  if (tabName === 'admin') {
    renderAdminTable();
  }
}

// 1. Map Initialization
function initMap() {
  map = L.map('map', {
    zoomControl: false
  }).setView([12.9716, 77.5946], 12);

  L.control.zoom({ position: 'topright' }).addTo(map);

  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 19
  }).addTo(map);
}

// 2. Load Initial City Data
async function loadCityData() {
  try {
    const [routesRes, stopsRes, busesRes, alertsRes] = await Promise.all([
      fetch(`${API_BASE}/routes/`),
      fetch(`${API_BASE}/stops/`),
      fetch(`${API_BASE}/buses/`),
      fetch(`${API_BASE}/alerts/active`)
    ]);

    routesData = await routesRes.json();
    stopsData = await stopsRes.json();
    busesData = await busesRes.json();
    const alerts = await alertsRes.json();

    populateRouteSelect(routesData);
    populatePlannerDropdowns(stopsData);
    renderStops(stopsData);
    renderRoutesPolylines(routesData);
    renderBusesList(busesData);
    updateAdminMetrics();

    if (alerts && alerts.length > 0) {
      showAlertBanner(alerts[0].title + ' - ' + alerts[0].description);
    }
  } catch (err) {
    console.error('Error loading city transit data:', err);
  }
}

// 3. WebSocket Setup
function initWebSocket() {
  try {
    wsSocket = new WebSocket(WS_URL);

    wsSocket.onopen = () => {
      updateWSStatus(true, 'Live WebSocket Connected');
    };

    wsSocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'BUS_LOCATION_UPDATE' || data.type === 'location_update') {
        const payload = data.data || data;
        updateBusMarker(payload);
        checkProximityAlarm(payload);
      } else if (data.bus_id) {
        updateBusMarker(data);
        checkProximityAlarm(data);
      }
    };

    wsSocket.onerror = () => {
      updateWSStatus(false, 'WebSocket Reconnecting...');
    };

    wsSocket.onclose = () => {
      updateWSStatus(false, 'REST Telemetry Fallback');
      setTimeout(initWebSocket, 5000);
    };
  } catch (e) {
    updateWSStatus(false, 'REST Telemetry Active');
  }
}

function updateWSStatus(connected, text) {
  const indicator = document.getElementById('ws-indicator');
  const textEl = document.getElementById('ws-text');
  if (connected) {
    indicator.className = 'w-2 h-2 rounded-full bg-emerald-400 animate-pulse';
  } else {
    indicator.className = 'w-2 h-2 rounded-full bg-amber-400';
  }
  textEl.innerText = text;
}

// Fallback REST Polling
function startFallbackPolling() {
  setInterval(async () => {
    try {
      const res = await fetch(`${API_BASE}/buses/locations/active`);
      if (res.ok) {
        const locations = await res.json();
        locations.forEach(loc => {
          updateBusMarker(loc);
          checkProximityAlarm(loc);
        });
      }
    } catch (e) {
      // Ignore network drop
    }
  }, 4000);
}

// 4. Render Routes & Polylines
function renderRoutesPolylines(routes) {
  const colors = ['#6366f1', '#10b981', '#f59e0b', '#ec4899', '#06b6d4'];
  
  routes.forEach((route, index) => {
    if (route.polyline_coords) {
      try {
        const coords = typeof route.polyline_coords === 'string' ? JSON.parse(route.polyline_coords) : route.polyline_coords;
        const color = colors[index % colors.length];
        
        const polyline = L.polyline(coords, {
          color: color,
          weight: 4,
          opacity: 0.7,
          dashArray: '8, 8'
        }).addTo(map);

        polyline.bindTooltip(`<b>${route.route_code}</b>: ${route.route_name}`, { sticky: true });
        routePolylines[route.id] = polyline;
      } catch (e) {
        console.error('Error parsing polyline for route', route.id);
      }
    }
  });
}

function populateRouteSelect(routes) {
  const select = document.getElementById('route-select');
  select.innerHTML = '<option value="ALL">All City Routes (Live Map)</option>';
  routes.forEach(r => {
    const opt = document.createElement('option');
    opt.value = r.id;
    opt.innerText = `${r.route_code} - ${r.route_name}`;
    select.appendChild(opt);
  });
}

function onRouteSelect() {
  activeRouteId = document.getElementById('route-select').value;
  filterMapByRoute(activeRouteId);
}

function filterMapByRoute(routeId) {
  Object.keys(routePolylines).forEach(rId => {
    if (routeId === 'ALL' || rId == routeId) {
      routePolylines[rId].setStyle({ opacity: 0.9, weight: 5 });
    } else {
      routePolylines[rId].setStyle({ opacity: 0.15, weight: 2 });
    }
  });
  renderStopsExplorer();
}

// 5. Trip Planner (A to B)
function populatePlannerDropdowns(stops) {
  const originSelect = document.getElementById('planner-origin');
  const destSelect = document.getElementById('planner-dest');
  
  if (!originSelect || !destSelect) return;

  const optionsHTML = '<option value="">-- Choose Stop --</option>' + stops.map(s => `
    <option value="${s.id}">${s.stop_name} (${s.code})</option>
  `).join('');

  originSelect.innerHTML = optionsHTML;
  destSelect.innerHTML = optionsHTML;
}

async function planTrip() {
  const originId = document.getElementById('planner-origin').value;
  const destId = document.getElementById('planner-dest').value;
  const resultsContainer = document.getElementById('planner-results');

  if (!originId || !destId) {
    alert('Please select both Origin and Destination stops.');
    return;
  }
  if (originId === destId) {
    alert('Origin and Destination stops must be different.');
    return;
  }

  resultsContainer.classList.remove('hidden');
  resultsContainer.innerHTML = '<div class="text-xs text-indigo-400 py-2 italic flex items-center justify-center gap-1.5"><i class="fa-solid fa-spinner animate-spin"></i> Finding optimal routes...</div>';

  try {
    const res = await fetch(`${API_BASE}/planner/route?origin_stop_id=${originId}&destination_stop_id=${destId}`);
    if (!res.ok) {
      const err = await res.json();
      resultsContainer.innerHTML = `<div class="text-xs text-amber-400 bg-amber-500/10 p-2 rounded border border-amber-500/20">${err.detail || 'No direct routes found.'}</div>`;
      return;
    }

    const data = await res.json();
    if (data.total_routes_found === 0 || !data.options || data.options.length === 0) {
      resultsContainer.innerHTML = `<div class="text-xs text-amber-400 bg-amber-500/10 p-2 rounded border border-amber-500/20">No direct bus route connects ${data.origin_stop.name} to ${data.destination_stop.name}.</div>`;
      return;
    }

    resultsContainer.innerHTML = data.options.map(opt => `
      <div class="bg-slate-950 border border-indigo-500/30 rounded-lg p-2.5 space-y-2">
        <div class="flex items-center justify-between">
          <span class="font-bold text-white text-xs bg-indigo-600/30 text-indigo-300 px-2 py-0.5 rounded border border-indigo-500/30">${opt.route_code}</span>
          <span class="text-[11px] font-semibold text-emerald-400 flex items-center gap-1">
            <i class="fa-solid fa-clock text-[10px]"></i> ~${opt.estimated_travel_time_mins} min
          </span>
        </div>
        <div class="text-[11px] text-slate-300 flex justify-between">
          <span>${opt.stops_count} stop${opt.stops_count > 1 ? 's' : ''} (${opt.distance_km} km)</span>
          <span class="text-slate-400">${opt.active_buses.length} Bus${opt.active_buses.length !== 1 ? 'es' : ''} Active</span>
        </div>
        ${opt.active_buses.length > 0 ? `
          <div class="text-[10px] text-slate-400 pt-1 border-t border-slate-900 flex items-center justify-between">
            <span>Next Bus (${opt.active_buses[0].bus_number})</span>
            ${getCrowdBadgeHTML(opt.active_buses[0].crowd_level)}
          </div>
        ` : ''}
        <button type="button" onclick="highlightPlannedRoute('${opt.route_id}', '${encodeURIComponent(JSON.stringify(opt.polyline_coords))}')" class="w-full mt-1 py-1 bg-indigo-500/20 hover:bg-indigo-500/30 text-indigo-300 rounded text-[11px] font-semibold flex items-center justify-center gap-1 border border-indigo-500/30">
          <i class="fa-solid fa-route"></i> Highlight Route on Map
        </button>
      </div>
    `).join('');

  } catch (err) {
    resultsContainer.innerHTML = '<div class="text-xs text-rose-400">Failed to connect to route planner service.</div>';
  }
}

function highlightPlannedRoute(routeId, polylineEncoded) {
  if (plannedRoutePolyline) {
    map.removeLayer(plannedRoutePolyline);
    plannedRoutePolyline = null;
  }

  try {
    const coords = JSON.parse(decodeURIComponent(polylineEncoded));
    if (coords && coords.length > 0) {
      plannedRoutePolyline = L.polyline(coords, {
        color: '#22d3ee',
        weight: 6,
        opacity: 0.95
      }).addTo(map);

      map.fitBounds(plannedRoutePolyline.getBounds(), { padding: [40, 40] });
    }
  } catch (e) {
    console.error('Error drawing planned route polyline:', e);
  }
}

function resetTripPlanner() {
  document.getElementById('planner-origin').value = '';
  document.getElementById('planner-dest').value = '';
  const resultsContainer = document.getElementById('planner-results');
  resultsContainer.classList.add('hidden');
  resultsContainer.innerHTML = '';
  
  if (plannedRoutePolyline) {
    map.removeLayer(plannedRoutePolyline);
    plannedRoutePolyline = null;
  }
}

// 6. Render Stops on Map & Stop Alarms
function renderStops(stops) {
  stops.forEach(stop => {
    const customIcon = L.divIcon({
      className: 'stop-marker-wrapper',
      html: `<div class="stop-marker-pin" title="${stop.stop_name}"></div>`,
      iconSize: [14, 14],
      iconAnchor: [7, 7]
    });

    const marker = L.marker([stop.latitude, stop.longitude], { icon: customIcon }).addTo(map);
    marker.on('click', () => selectStop(stop));
    stopMarkers[stop.id] = marker;
  });

  renderStopsExplorer();
}

function selectStop(stop) {
  selectedStopId = stop.id;
  document.getElementById('selected-stop-card').classList.remove('hidden');
  document.getElementById('stop-card-name').innerText = stop.stop_name;
  document.getElementById('stop-card-area').innerText = stop.city_area || `Code: ${stop.code}`;
  
  updateAlarmButtonState();
  fetchStopETAs(stop.id);
  map.panTo([stop.latitude, stop.longitude]);
}

function closeStopCard() {
  document.getElementById('selected-stop-card').classList.add('hidden');
  selectedStopId = null;
}

function toggleStopAlarm() {
  if (!selectedStopId) return;

  const currentStop = stopsData.find(s => s.id === selectedStopId);
  const stopName = currentStop ? currentStop.stop_name : 'Selected Stop';

  if (activeAlarmStopId === selectedStopId) {
    activeAlarmStopId = null;
    activeAlarmStopName = null;
    alarmTriggeredBuses.clear();
    showAlertBanner('🔔 Stop Arrival Alarm Cancelled');
  } else {
    activeAlarmStopId = selectedStopId;
    activeAlarmStopName = stopName;
    alarmTriggeredBuses.clear();
    showAlertBanner(`🔔 Arrival Alarm Active for ${stopName}! You will be alerted when a bus approaches.`);
    playAlarmChime();
  }

  updateAlarmButtonState();
}

function updateAlarmButtonState() {
  const btn = document.getElementById('stop-alarm-btn');
  const btnText = document.getElementById('alarm-btn-text');
  if (!btn || !btnText) return;

  if (activeAlarmStopId && activeAlarmStopId === selectedStopId) {
    btn.className = 'text-[11px] font-semibold px-2 py-0.5 rounded-full border border-emerald-500 text-emerald-300 bg-emerald-500/20 alarm-active flex items-center gap-1';
    btnText.innerText = 'Alarm Set';
  } else {
    btn.className = 'text-[11px] font-semibold px-2 py-0.5 rounded-full border border-amber-500/40 text-amber-300 bg-amber-500/10 hover:bg-amber-500/20 transition-all flex items-center gap-1';
    btnText.innerText = 'Set Alarm';
  }
}

function playAlarmChime() {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) return;
    const ctx = new AudioContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    
    osc.type = 'sine';
    osc.frequency.setValueAtTime(587.33, ctx.currentTime); // D5
    osc.frequency.setValueAtTime(880.00, ctx.currentTime + 0.15); // A5
    
    gain.gain.setValueAtTime(0.25, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.5);
    
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.5);
  } catch (e) {
    // Audio synthesis fallback
  }
}

function checkProximityAlarm(busData) {
  if (!activeAlarmStopId || !busData || !busData.latitude || !busData.longitude) return;

  const targetStop = stopsData.find(s => s.id === activeAlarmStopId);
  if (!targetStop) return;

  const distanceKm = getHaversineDistance(
    busData.latitude, 
    busData.longitude, 
    targetStop.latitude, 
    targetStop.longitude
  );

  const busIdKey = busData.bus_id || busData.bus_number;

  // Alert if bus is within 1.0 km of the target stop
  if (distanceKm <= 1.0 && !alarmTriggeredBuses.has(busIdKey)) {
    alarmTriggeredBuses.add(busIdKey);
    playAlarmChime();
    
    const busNumStr = busData.bus_number || `BUS-${busData.bus_id}`;
    showAlertBanner(`🚨 BUS ARRIVAL ALERT: ${busNumStr} is ${distanceKm.toFixed(1)} km away from ${targetStop.stop_name}! Prepare to board.`);
  }
}

async function fetchStopETAs(stopId) {
  const container = document.getElementById('stop-eta-list');
  container.innerHTML = '<div class="text-xs text-slate-400 italic">Calculating ML arrival estimate...</div>';
  
  try {
    const res = await fetch(`${API_BASE}/stops/${stopId}/eta`);
    if (res.ok) {
      const etas = await res.json();
      if (etas.length === 0) {
        container.innerHTML = '<div class="text-xs text-slate-500 py-1">No buses currently approaching this stop.</div>';
        return;
      }
      
      container.innerHTML = etas.map(eta => `
        <div class="bg-slate-950/80 border border-slate-800 rounded-lg p-2.5 flex items-center justify-between">
          <div class="flex items-center space-x-2.5">
            <div class="bg-indigo-600/30 text-indigo-400 p-2 rounded-lg">
              <i class="fa-solid fa-bus text-sm"></i>
            </div>
            <div>
              <p class="text-xs font-bold text-white">${eta.bus_number || 'BUS-' + eta.bus_id}</p>
              <p class="text-[10px] text-slate-400">${eta.route_name || 'In Service'}</p>
            </div>
          </div>
          <div class="text-right">
            <span class="text-sm font-extrabold text-emerald-400">${Math.max(1, Math.round(eta.predicted_eta_minutes))} min</span>
            <div class="mt-0.5">${getCrowdBadgeHTML(eta.crowd_level)}</div>
          </div>
        </div>
      `).join('');
    }
  } catch (e) {
    container.innerHTML = '<div class="text-xs text-amber-400 py-1">Direct ETA Stream Active</div>';
  }
}

// 7. Realtime Bus Markers & Cards Update
function updateBusMarker(data) {
  const busId = data.bus_id;
  const lat = data.latitude;
  const lng = data.longitude;
  const speed = data.speed_kmh || 35;
  const busNum = data.bus_number || `BUS-${busId}`;
  const crowdLevel = data.crowd_level || 'LOW';

  if (!lat || !lng) return;

  if (busMarkers[busId]) {
    busMarkers[busId].setLatLng([lat, lng]);
  } else {
    const customIcon = L.divIcon({
      className: 'bus-marker-wrapper',
      html: `
        <div class="relative flex items-center justify-center">
          <div class="bus-marker-pulse"></div>
          <div class="bus-marker-pin">
            <i class="fa-solid fa-bus"></i>
          </div>
        </div>
      `,
      iconSize: [36, 36],
      iconAnchor: [18, 18]
    });

    const marker = L.marker([lat, lng], { icon: customIcon }).addTo(map);
    busMarkers[busId] = marker;
  }

  // Update Popup Content with Crowd Level
  busMarkers[busId].bindPopup(`
    <div class="p-1 space-y-1">
      <div class="flex items-center justify-between gap-2">
        <h4 class="font-bold text-indigo-400 text-sm">${busNum}</h4>
        ${getCrowdBadgeHTML(crowdLevel)}
      </div>
      <p class="text-xs text-slate-300">Speed: ${Math.round(speed)} km/h</p>
      <p class="text-[10px] text-emerald-400">Live GPS Telemetry Active</p>
    </div>
  `);

  updateBusCardData(busId, busNum, speed, lat, lng, crowdLevel);
}

function updateBusCardData(busId, busNum, speed, lat, lng, crowdLevel = 'LOW') {
  const container = document.getElementById('bus-cards-container');
  const countEl = document.getElementById('active-bus-count');
  
  let existingCard = document.getElementById(`bus-card-${busId}`);
  if (!existingCard) {
    const cardHtml = `
      <div id="bus-card-${busId}" onclick="focusBusOnMap(${busId})" class="bg-slate-900/90 border border-slate-800 hover:border-indigo-500/50 rounded-xl p-3 cursor-pointer transition-all duration-200 shadow-md hover:shadow-indigo-500/10 space-y-2">
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <div class="w-8 h-8 rounded-lg bg-indigo-600/20 text-indigo-400 flex items-center justify-center border border-indigo-500/30">
              <i class="fa-solid fa-bus text-sm"></i>
            </div>
            <div>
              <h4 class="font-bold text-sm text-white">${busNum}</h4>
              <p class="text-[10px] text-slate-400 flex items-center gap-1">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> Transmitting
              </p>
            </div>
          </div>
          <div class="text-right">
            <span class="text-xs font-bold text-indigo-300" id="bus-card-speed-${busId}">${Math.round(speed)} km/h</span>
            <div id="bus-card-crowd-${busId}" class="mt-0.5">${getCrowdBadgeHTML(crowdLevel)}</div>
          </div>
        </div>
      </div>
    `;
    
    if (container.children[0] && container.children[0].innerText.includes('Loading')) {
      container.innerHTML = '';
    }
    container.insertAdjacentHTML('beforeend', cardHtml);
  } else {
    const speedEl = document.getElementById(`bus-card-speed-${busId}`);
    const crowdEl = document.getElementById(`bus-card-crowd-${busId}`);
    if (speedEl) speedEl.innerText = `${Math.round(speed)} km/h`;
    if (crowdEl) crowdEl.innerHTML = getCrowdBadgeHTML(crowdLevel);
  }

  if (countEl) countEl.innerText = Object.keys(busMarkers).length;
}

function focusBusOnMap(busId) {
  if (busMarkers[busId]) {
    map.setView(busMarkers[busId].getLatLng(), 15);
    busMarkers[busId].openPopup();
  }
}

function renderStopsExplorer() {
  const container = document.getElementById('stops-container');
  container.innerHTML = stopsData.map(s => `
    <div onclick="selectStop({id: ${s.id}, stop_name: '${s.stop_name}', latitude: ${s.latitude}, longitude: ${s.longitude}, city_area: '${s.city_area || ''}'})" class="p-2 bg-slate-900/60 border border-slate-800 hover:border-slate-700 rounded-lg flex items-center justify-between cursor-pointer text-xs text-slate-300 transition">
      <span class="flex items-center gap-2">
        <i class="fa-solid fa-location-dot text-cyan-400 text-[10px]"></i>
        ${s.stop_name}
      </span>
      <span class="text-[10px] text-slate-500">${s.code}</span>
    </div>
  `).join('');
}

function renderBusesList(buses) {
  const container = document.getElementById('bus-cards-container');
  if (buses.length > 0) {
    buses.forEach(b => {
      updateBusCardData(b.id, b.bus_number, 35, 12.9716, 77.5946, b.crowd_level || 'LOW');
    });
  }
}

// 8. Driver Smartphone GPS Transmitter Mode
function populateDriverBusSelect() {
  const select = document.getElementById('driver-bus-select');
  select.innerHTML = busesData.map(b => `<option value="${b.id}">${b.bus_number} - (${b.model || 'Transit Bus'})</option>`).join('');
}

function setDriverCrowdLevel(level) {
  driverCrowdLevel = level;
  const levels = ['LOW', 'MEDIUM', 'HIGH', 'FULL'];
  
  levels.forEach(lvl => {
    const btn = document.getElementById(`crowd-btn-${lvl}`);
    if (!btn) return;

    if (lvl === level) {
      if (lvl === 'LOW') btn.className = 'crowd-sel-btn py-2 px-2 rounded-lg border border-emerald-500 bg-emerald-500/30 text-emerald-300 flex flex-col items-center gap-1 shadow-md shadow-emerald-500/20';
      if (lvl === 'MEDIUM') btn.className = 'crowd-sel-btn py-2 px-2 rounded-lg border border-amber-500 bg-amber-500/30 text-amber-300 flex flex-col items-center gap-1 shadow-md shadow-amber-500/20';
      if (lvl === 'HIGH') btn.className = 'crowd-sel-btn py-2 px-2 rounded-lg border border-orange-500 bg-orange-500/30 text-orange-300 flex flex-col items-center gap-1 shadow-md shadow-orange-500/20';
      if (lvl === 'FULL') btn.className = 'crowd-sel-btn py-2 px-2 rounded-lg border border-rose-500 bg-rose-500/30 text-rose-300 flex flex-col items-center gap-1 shadow-md shadow-rose-500/20';
    } else {
      btn.className = 'crowd-sel-btn py-2 px-2 rounded-lg border border-slate-700 bg-slate-950 text-slate-400 flex flex-col items-center gap-1 hover:border-slate-500';
    }
  });
}

function toggleDriverTracking() {
  const btnText = document.getElementById('driver-btn-text');
  const btn = document.getElementById('driver-toggle-btn');
  const busId = document.getElementById('driver-bus-select').value;

  if (!isDriverTracking) {
    isDriverTracking = true;
    btnText.innerText = 'Stop Telemetry Broadcast';
    btn.className = 'w-full py-4 rounded-xl font-bold text-white bg-rose-600 hover:bg-rose-500 shadow-lg shadow-rose-600/30 transition-all duration-200 flex items-center justify-center space-x-3 text-lg';

    if ('geolocation' in navigator) {
      driverWatchId = navigator.geolocation.watchPosition(
        (pos) => sendDriverLocation(busId, pos.coords.latitude, pos.coords.longitude, pos.coords.speed),
        (err) => startDriverSimulation(busId),
        { enableHighAccuracy: true }
      );
    } else {
      startDriverSimulation(busId);
    }
  } else {
    isDriverTracking = false;
    btnText.innerText = 'Start Trip & Broadcast Location';
    btn.className = 'w-full py-4 rounded-xl font-bold text-white bg-emerald-600 hover:bg-emerald-500 shadow-lg shadow-emerald-600/30 transition-all duration-200 flex items-center justify-center space-x-3 text-lg';

    if (driverWatchId) navigator.geolocation.clearWatch(driverWatchId);
    if (driverSimInterval) clearInterval(driverSimInterval);
  }
}

function startDriverSimulation(busId) {
  let lat = 12.9716;
  let lng = 77.5946;
  
  driverSimInterval = setInterval(() => {
    lat += (Math.random() - 0.5) * 0.002;
    lng += (Math.random() - 0.5) * 0.002;
    sendDriverLocation(busId, lat, lng, 35 + Math.random() * 10);
  }, 3000);
}

async function sendDriverLocation(busId, lat, lng, speedKmh) {
  driverPingsSent++;
  document.getElementById('driver-pings').innerText = driverPingsSent;
  document.getElementById('driver-speed').innerHTML = `${Math.round(speedKmh || 38)} <span class="text-xs font-normal text-slate-400">km/h</span>`;
  document.getElementById('driver-coords').innerText = `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
  document.getElementById('driver-last-ping').innerText = new Date().toLocaleTimeString();

  const payload = {
    bus_id: parseInt(busId),
    latitude: lat,
    longitude: lng,
    speed_kmh: speedKmh || 38,
    crowd_level: driverCrowdLevel,
    timestamp: new Date().toISOString()
  };

  try {
    await fetch(`${API_BASE}/trips/1/location`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
  } catch (e) {
    // Ignore offline buffering
  }

  updateBusMarker(payload);
}

// 9. Admin Fleet Management & Alert Broadcasts
function updateAdminMetrics() {
  document.getElementById('admin-active-buses').innerText = busesData.length;
  document.getElementById('admin-total-routes').innerText = routesData.length;
  document.getElementById('admin-total-stops').innerText = stopsData.length;
}

function renderAdminTable() {
  const tbody = document.getElementById('admin-bus-table');
  tbody.innerHTML = busesData.map(b => `
    <tr class="hover:bg-slate-900/60">
      <td class="py-3 px-4 font-bold text-white">${b.bus_number}</td>
      <td class="py-3 px-4 text-xs text-slate-400">${b.model}</td>
      <td class="py-3 px-4 text-xs text-indigo-400">Route #${b.assigned_route_id || 1}</td>
      <td class="py-3 px-4">
        ${getCrowdBadgeHTML(b.crowd_level)}
      </td>
      <td class="py-3 px-4 text-xs font-mono">38 km/h</td>
      <td class="py-3 px-4 text-xs text-slate-300">Driver #${b.assigned_driver_id || 1}</td>
    </tr>
  `).join('');
}

function openBroadcastModal() {
  document.getElementById('alert-modal').classList.remove('hidden');
}

function closeBroadcastModal() {
  document.getElementById('alert-modal').classList.add('hidden');
}

async function submitAlert(e) {
  e.preventDefault();
  const title = document.getElementById('alert-title-input').value;
  const desc = document.getElementById('alert-desc-input').value;
  const severity = document.getElementById('alert-severity-input').value;

  try {
    await fetch(`${API_BASE}/alerts/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: title,
        description: desc,
        severity: severity,
        route_id: 1
      })
    });
    
    closeBroadcastModal();
    showAlertBanner(`${title} - ${desc}`);
  } catch (err) {
    showAlertBanner(`${title} - ${desc}`);
    closeBroadcastModal();
  }
}

function showAlertBanner(text) {
  const banner = document.getElementById('alerts-banner');
  const bannerText = document.getElementById('alert-banner-text');
  bannerText.innerText = text;
  banner.classList.remove('hidden');
}

function dismissAlertBanner() {
  document.getElementById('alerts-banner').classList.add('hidden');
}
