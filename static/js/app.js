// Smart Metan Monitoring - Core Interactive Engine
// Uses Leaflet.js for beautiful dark maps

let map = null;
let markersLayer = null;
let userMarker = null;
let userCoords = null;
let stationsData = [];
let updateInterval = null;

// Boshlang'ich yuklash
document.addEventListener("DOMContentLoaded", () => {
    // 1. Geolokatsiyani olishga urinib ko'rish
    initGeolocator();

    // 2. Xaritani ishga tushirish (agar driver sahifasida bo'lsa)
    if (document.getElementById("map-container")) {
        initMap();
    }

    // 3. Stansiyalar ro'yxatini yuklash
    fetchStations();
    
    // Har 10 soniyada ma'lumotlarni yangilab turish (Real-time polling)
    updateInterval = setInterval(fetchStations, 10000);

    // 4. Offline/Online hodisalarini eshitish
    window.addEventListener("online", updateOnlineStatus);
    window.addEventListener("offline", updateOnlineStatus);
    updateOnlineStatus();

    // 5. Qidiruv va filtrlarni sozlash
    setupFilters();

    // 6. Viloyat va tumanlarni dinamik to'ldirish
    initRegionDropdowns();
});

// --- OFFLINE TIZIM DETEKTORI ---
function updateOnlineStatus() {
    const offlineToast = document.getElementById("offline-toast");
    if (!offlineToast) return;
    
    if (navigator.onLine) {
        offlineToast.classList.remove("show");
    } else {
        offlineToast.classList.add("show");
        // Offline paytida oxirgi kesh ma'lumotlarini yuklash
        const cached = localStorage.getItem("smartmetan_cached_stations");
        if (cached) {
            renderStationsList(JSON.parse(cached));
        }
    }
}

// --- GPS GEOLOCATOR ---
function initGeolocator() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                userCoords = {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude
                };
                localStorage.setItem("user_last_lat", userCoords.lat);
                localStorage.setItem("user_last_lng", userCoords.lng);
                
                // Ro'yxatni masofaga qarab qayta yuklash
                fetchStations();
                
                // Xaritadagi joylashuvimizni yangilash
                updateMapUserPosition();
            },
            (error) => {
                console.log("GPS ruxsat berilmadi yoki xatolik:", error);
                // Agar avval saqlangan joylashuv bo'lsa olish
                const savedLat = localStorage.getItem("user_last_lat");
                const savedLng = localStorage.getItem("user_last_lng");
                if (savedLat && savedLng) {
                    userCoords = {
                        lat: parseFloat(savedLat),
                        lng: parseFloat(savedLng)
                    };
                }
            }
        );
    }
}

function useCurrentLocation() {
    const locBtn = document.getElementById("location-btn");
    if (locBtn) {
        locBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Aniqlanmoqda...';
    }
    
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            (position) => {
                userCoords = {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude
                };
                fetchStations();
                updateMapUserPosition();
                
                // Xarita markazini o'zgartirish
                if (map) {
                    map.setView([userCoords.lat, userCoords.lng], 13);
                }
                
                if (locBtn) {
                    locBtn.innerHTML = '<i class="fas fa-location-arrow"></i> Joylashuv aniqlandi';
                    setTimeout(() => {
                        locBtn.innerHTML = '<i class="fas fa-location-arrow"></i> Mening joylashuvim';
                    }, 3000);
                }
            },
            (error) => {
                alert("GPS aniqlashda xatolik yuz berdi. Geolokatsiyaga ruxsat bering!");
                if (locBtn) locBtn.innerHTML = '<i class="fas fa-location-arrow"></i> Mening joylashuvim';
            }
        );
    }
}

// --- INTERAKTIV LEAFLET XARITASI ---
function initMap() {
    // Toshkent shahri markazi (Tashkent Center)
    const defaultCenter = [41.311081, 69.240562];
    
    map = L.map('map-container', {
        zoomControl: false
    }).setView(defaultCenter, 12);
    
    L.control.zoom({
        position: 'bottomright'
    }).addTo(map);

    // Premium To'q rangli (CartoDB Dark Matter) xarita kafelini yuklaymiz
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 20
    }).addTo(map);

    markersLayer = L.layerGroup().addTo(map);

    // Xaritani bosganda ariza yuborish uchun koordinatani auto-fill qilish
    map.on('click', (e) => {
        const lat = e.latlng.lat;
        const lng = e.latlng.lng;
        
        // Modal ochish va koordinatalarni kiritish
        openAddStationModal(lat, lng);
    });
}

function updateMapUserPosition() {
    if (!map || !userCoords) return;

    if (userMarker) {
        userMarker.setLatLng([userCoords.lat, userCoords.lng]);
    } else {
        // Moviy nurli doiraviy foydalanuvchi marker-nuqtasi
        const userIcon = L.divIcon({
            className: 'user-location-marker',
            html: '<div style="background-color: #00f0ff; width: 14px; height: 14px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 10px rgba(0,240,255,0.8); animate: pulse 2s infinite;"></div>',
            iconSize: [14, 14],
            iconAnchor: [7, 7]
        });
        userMarker = L.marker([userCoords.lat, userCoords.lng], { icon: userIcon }).addTo(map);
    }
}

// --- MA'LUMOTLARNI YUKLASH (AJAX) ---
function fetchStations() {
    let url = '/api/stations/';
    
    const params = new URLSearchParams();
    if (userCoords) {
        params.append('lat', userCoords.lat);
        params.append('lng', userCoords.lng);
    }
    
    const searchVal = document.getElementById("search-input")?.value;
    const regionVal = document.getElementById("region-filter")?.value;
    const districtVal = document.getElementById("district-filter")?.value;
    
    if (searchVal) params.append('search', searchVal);
    if (regionVal) params.append('region', regionVal);
    if (districtVal) params.append('district', districtVal);
    
    if (params.toString()) {
        url += '?' + params.toString();
    }

    if (!navigator.onLine) return; // Internet bo'lmasa so'rov yubormaymiz

    fetch(url)
        .then(response => response.json())
        .then(data => {
            stationsData = data.stations;
            // Keshga saqlab qo'yish offline ishlashi uchun
            localStorage.setItem("smartmetan_cached_stations", JSON.stringify(stationsData));
            
            renderStationsList(stationsData);
            renderMapMarkers(stationsData);
        })
        .catch(err => console.error("API xatolik:", err));
}

// --- STANSIYALAR RO'YXATINI EKRAVGA CHIQARISH ---
function renderStationsList(stations) {
    const listContainer = document.getElementById("stations-list-container");
    if (!listContainer) return;
    
    if (stations.length === 0) {
        listContainer.innerHTML = `
            <div class="glass-panel" style="text-align: center; padding: 2rem;">
                <i class="fas fa-search" style="font-size:2rem; color: var(--text-secondary); margin-bottom:0.75rem; display:block;"></i>
                <p style="color: var(--text-secondary);">Zapravkalar topilmadi.</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    stations.forEach(st => {
        const statusClass = st.status.toLowerCase();

        // Status badge label
        const statusLabels = {
            GREEN: '🟢 Kam navbat',
            YELLOW: '🟡 O\'rtacha',
            RED: '🔴 Ko\'p navbat',
            BLACK: '⚫ Yopiq',
            WHITE: '⚪ Noma\'lum'
        };
        const statusLabel = statusLabels[st.status] || st.status;

        // Power indicator
        const powerHtml = st.has_power
            ? `<span style="color:var(--neon-green); font-size:0.78rem;"><i class="fas fa-bolt"></i> Elektr bor</span>`
            : `<span style="color:var(--neon-red); font-size:0.78rem;"><i class="fas fa-bolt"></i> Tok o'chgan!</span>`;

        // Gas pressure
        const pressureMap = {
            HIGH: `<span style="color:var(--neon-green); font-size:0.78rem;"><i class="fas fa-tachometer-alt"></i> Bosim normal</span>`,
            LOW:  `<span style="color:var(--neon-yellow); font-size:0.78rem;"><i class="fas fa-tachometer-alt"></i> Bosim past</span>`,
            NONE: `<span style="color:var(--neon-red); font-size:0.78rem;"><i class="fas fa-tachometer-alt"></i> Gaz yo'q!</span>`
        };
        const pressureHtml = pressureMap[st.gas_pressure] || '';

        // Distance
        const distHtml = st.distance !== null
            ? `<span style="color:var(--neon-blue); font-size:0.8rem; font-weight:600;"><i class="fas fa-route"></i> ${st.distance < 1 ? Math.round(st.distance*1000)+' m' : st.distance+' km'}</span>`
            : '';

        // Navigation links
        const navGoogle = `https://www.google.com/maps/dir/?api=1&destination=${st.latitude},${st.longitude}`;
        const navYandex = `https://yandex.com/maps/?rtext=~${st.latitude},${st.longitude}`;

        // Phone
        const phoneHtml = st.phone
            ? `<a href="tel:${st.phone}" style="color:var(--neon-blue); text-decoration:none; font-size:0.8rem;"><i class="fas fa-phone"></i> ${st.phone}</a>`
            : '';

        // Status border color
        const borderColors = {
            GREEN: 'var(--neon-green)', YELLOW: 'var(--neon-yellow)',
            RED: 'var(--neon-red)', BLACK: '#374151', WHITE: 'rgba(255,255,255,0.2)'
        };
        const borderColor = borderColors[st.status] || 'rgba(255,255,255,0.1)';

        html += `
        <div class="glass-panel station-card status-${statusClass}"
             style="border-left: 4px solid ${borderColor}; cursor:pointer; padding: 1rem 1rem 1rem 1.2rem;"
             onclick="focusStationOnMap(${st.latitude}, ${st.longitude}, '${st.name.replace(/'/g,"\\\'")}')">

            <!-- Top row: Name + Status badge + Distance -->
            <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:0.5rem; flex-wrap:wrap; margin-bottom:0.6rem;">
                <div style="flex:1; min-width:0;">
                    <h4 style="font-size:1rem; font-weight:700; margin-bottom:0.15rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${st.name}</h4>
                    <p style="font-size:0.75rem; color:var(--text-secondary); line-height:1.3;">
                        <i class="fas fa-map-marker-alt" style="color:var(--neon-red);"></i> ${st.address}
                    </p>
                </div>
                <div style="display:flex; flex-direction:column; align-items:flex-end; gap:0.3rem; flex-shrink:0;">
                    <span class="status-badge ${statusClass}">${statusLabel}</span>
                    ${distHtml}
                </div>
            </div>

            <!-- Middle: ETA + Price -->
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.5rem; background:rgba(255,255,255,0.03); border-radius:10px; padding:0.6rem 0.75rem; margin-bottom:0.6rem;">
                <div>
                    <div style="font-size:0.7rem; color:var(--text-secondary); margin-bottom:0.1rem;">⏱ Kutish vaqti</div>
                    <div style="font-size:0.85rem; font-weight:600; color:var(--text-primary);">${st.estimated_wait}</div>
                </div>
                <div>
                    <div style="font-size:0.7rem; color:var(--text-secondary); margin-bottom:0.1rem;">💰 Gaz narxi</div>
                    <div style="font-size:0.85rem; font-weight:600; color:var(--neon-green);">${st.price.toLocaleString()} so'm/m³</div>
                </div>
            </div>

            <!-- Indicators row -->
            <div style="display:flex; flex-wrap:wrap; gap:0.75rem; margin-bottom:0.6rem;">
                ${powerHtml}
                ${pressureHtml}
                ${phoneHtml}
            </div>

            <!-- Navigation buttons -->
            <div style="display:flex; gap:0.5rem; margin-top:0.4rem;">
                <a href="${navYandex}" target="_blank" onclick="event.stopPropagation()"
                   style="flex:1; background:rgba(230,20,20,0.15); border:1px solid rgba(230,20,20,0.35); color:#ff6b6b; text-align:center; padding:0.45rem 0.3rem; border-radius:8px; font-size:0.75rem; text-decoration:none; font-weight:600; transition:all 0.2s;"
                   onmouseover="this.style.background='rgba(230,20,20,0.25)'" onmouseout="this.style.background='rgba(230,20,20,0.15)'">
                    <i class="fas fa-car"></i> Yandex
                </a>
                <a href="${navGoogle}" target="_blank" onclick="event.stopPropagation()"
                   style="flex:1; background:rgba(52,168,83,0.15); border:1px solid rgba(52,168,83,0.35); color:#4ade80; text-align:center; padding:0.45rem 0.3rem; border-radius:8px; font-size:0.75rem; text-decoration:none; font-weight:600; transition:all 0.2s;"
                   onmouseover="this.style.background='rgba(52,168,83,0.25)'" onmouseout="this.style.background='rgba(52,168,83,0.15)'">
                    <i class="fas fa-map"></i> Google
                </a>
            </div>

            <!-- Last updated -->
            <div style="font-size:0.7rem; color:var(--text-secondary); margin-top:0.5rem; text-align:right;">
                <i class="fas fa-sync-alt"></i> ${st.last_updated}
            </div>
        </div>
        `;
    });
    
    listContainer.innerHTML = html;
}


// --- XARITADAGI MARKERLARNI YANGILASH ---
function renderMapMarkers(stations) {
    if (!map || !markersLayer) return;
    
    markersLayer.clearLayers();
    
    stations.forEach(st => {
        // Statusga qarab marker rangi
        let markerColor = '#9ca3af'; // white/grey default
        if (st.status === 'GREEN') markerColor = '#00ff88';
        else if (st.status === 'YELLOW') markerColor = '#ffd600';
        else if (st.status === 'RED') markerColor = '#ff3366';
        else if (st.status === 'BLACK') markerColor = '#374151';
        
        const customIcon = L.divIcon({
            className: 'custom-station-icon',
            html: `<div style="background-color: ${markerColor}; width: 16px; height: 16px; border-radius: 50%; border: 3px solid #111318; box-shadow: 0 0 10px ${markerColor}99;"></div>`,
            iconSize: [16, 16],
            iconAnchor: [8, 8]
        });
        
        let marker = L.marker([st.latitude, st.longitude], { icon: customIcon }).addTo(markersLayer);
        
        // Popup oynasi tarkibi
        let navGoogle = `https://www.google.com/maps/dir/?api=1&destination=${st.latitude},${st.longitude}`;
        let navYandex = `https://yandex.com/maps/?rtext=~${st.latitude},${st.longitude}`;
        
        let popupHtml = `
            <div style="color: white; font-family: 'Inter', sans-serif; min-width: 200px;">
                <h4 style="margin: 0 0 5px 0; font-size: 1rem; color: var(--neon-blue);">${st.name}</h4>
                <p style="margin: 0 0 8px 0; font-size: 0.8rem; color: #ccc;">${st.address}</p>
                <div style="border-top: 1px solid rgba(255,255,255,0.1); padding-top: 8px; margin-top: 5px; font-size: 0.8rem;">
                    <div>🕒 <b>${st.estimated_wait}</b></div>
                    <div>💰 Narxi: <b>${st.price} so'm/m³</b></div>
                    <div style="margin-top: 3px;">⚡ Svet: ${st.has_power ? '🟢 Bor' : '🔴 O\'chgan'}</div>
                </div>
                <div style="margin-top: 10px; display: flex; gap: 8px;">
                    <a href="${navYandex}" target="_blank" style="flex:1; background: #e61414; color:white; text-align:center; padding: 5px; border-radius: 4px; font-size: 0.75rem; text-decoration:none; font-weight:bold;">Yandex Go</a>
                    <a href="${navGoogle}" target="_blank" style="flex:1; background: #34a853; color:white; text-align:center; padding: 5px; border-radius: 4px; font-size: 0.75rem; text-decoration:none; font-weight:bold;">Google Maps</a>
                </div>
            </div>
        `;
        
        marker.bindPopup(popupHtml, {
            closeButton: false,
            className: 'custom-leaflet-popup'
        });
    });
}

function focusStationOnMap(lat, lng, name) {
    if (!map) return;
    map.setView([lat, lng], 14);
    
    // Popupni ochish uchun tegishli markerni qidirib topamiz
    markersLayer.eachLayer(marker => {
        if (marker.getLatLng().lat === lat && marker.getLatLng().lng === lng) {
            marker.openPopup();
        }
    });
}

// --- FILTRLARNI O'RNATISH ---
function setupFilters() {
    const searchInput = document.getElementById("search-input");
    const regionFilter = document.getElementById("region-filter");
    const districtFilter = document.getElementById("district-filter");
    
    if (searchInput) searchInput.addEventListener("input", fetchStations);
    if (regionFilter) regionFilter.addEventListener("change", () => {
        const selectedRegion = regionFilter.value;
        populateDistrictsDropdown(selectedRegion, districtFilter, "Barcha tumanlar");
        fetchStations();
    });
    if (districtFilter) districtFilter.addEventListener("change", fetchStations);
}

// --- VILOYAT VA TUMANLARNI DINAMIK TO'LDIRISH TIZIMI ---
function initRegionDropdowns() {
    // 1. Haydovchi sahifasi filtri
    const rFilter = document.getElementById("region-filter");
    const dFilter = document.getElementById("district-filter");
    if (rFilter && dFilter) {
        populateRegionsDropdown(rFilter);
    }

    // 2. Haydovchi taklif qilish modal oynasi
    const mRegion = document.getElementById("modal-region");
    const mDistrict = document.getElementById("modal-district");
    if (mRegion && mDistrict) {
        populateRegionsDropdown(mRegion);
        mRegion.addEventListener("change", () => {
            populateDistrictsDropdown(mRegion.value, mDistrict, "— Tanlang —");
        });
    }

    // 3. Admin dashboard yangi zapravka qo'shish formasi
    const aRegion = document.getElementById("as-region");
    const aDistrict = document.getElementById("as-district");
    if (aRegion && aDistrict) {
        populateRegionsDropdown(aRegion);
        aRegion.addEventListener("change", () => {
            populateDistrictsDropdown(aRegion.value, aDistrict, "— Tanlang —");
        });
    }
}

function populateRegionsDropdown(selectElement) {
    if (!selectElement) return;
    // Boshlang'ich variantni saqlab qolamiz
    const defaultOpt = selectElement.options[0] ? selectElement.options[0].text : "— Tanlang —";
    selectElement.innerHTML = `<option value="">${defaultOpt}</option>`;
    
    Object.keys(UZ_REGIONS_DATA).sort().forEach(region => {
        const opt = document.createElement("option");
        opt.value = region;
        opt.textContent = region;
        selectElement.appendChild(opt);
    });
}

function populateDistrictsDropdown(region, selectElement, defaultText) {
    if (!selectElement) return;
    selectElement.innerHTML = `<option value="">${defaultText}</option>`;
    
    if (!region || !UZ_REGIONS_DATA[region]) {
        selectElement.disabled = true;
        return;
    }

    selectElement.disabled = false;
    UZ_REGIONS_DATA[region].sort().forEach(dist => {
        const opt = document.createElement("option");
        opt.value = dist;
        opt.textContent = dist;
        selectElement.appendChild(opt);
    });
}


// --- MODALLAR BOSHQARUVI ---
function openAddStationModal(lat, lng) {
    const modal = document.getElementById("add-station-modal");
    if (!modal) return;
    
    modal.classList.add("active");
    
    // Agar xaritadan bosilgan bo'lsa koordinatalarni kiritish
    if (lat && lng) {
        document.getElementById("modal-lat").value = lat.toFixed(6);
        document.getElementById("modal-lng").value = lng.toFixed(6);
        document.getElementById("modal-address").placeholder = `Koordinata tanlandi: ${lat.toFixed(4)}, ${lng.toFixed(4)}`;
    }
}

function closeAddStationModal() {
    const modal = document.getElementById("add-station-modal");
    if (modal) {
        modal.classList.remove("active");
    }
}

// Yangi zapravka arizasini yuborish
function submitStationSuggestion(event) {
    event.preventDefault();
    
    const name = document.getElementById("modal-name").value;
    const address = document.getElementById("modal-address").value;
    const lat = document.getElementById("modal-lat").value;
    const lng = document.getElementById("modal-lng").value;
    const phone = document.getElementById("modal-phone").value;
    const region = document.getElementById("modal-region").value;
    const district = document.getElementById("modal-district").value;
    
    const submitBtn = document.getElementById("modal-submit-btn");
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Yuborilmoqda...';
    
    fetch('/api/stations/add/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            name: name,
            address: address,
            latitude: lat,
            longitude: lng,
            phone: phone,
            region: region,
            district: district
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert(data.message);
            closeAddStationModal();
            document.getElementById("station-suggest-form").reset();
        } else {
            alert("Xatolik: " + data.error);
        }
    })
    .catch(err => {
        alert("Server bilan aloqa uzildi!");
    })
    .finally(() => {
        submitBtn.innerHTML = 'Taklif yuborish';
    });
}
