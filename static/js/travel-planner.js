(function() {
  'use strict';

  const IATA_DATABASE = {
    'ICN': { city: 'Incheon', country: 'South Korea', airport: 'Incheon International Airport' },
    'NRT': { city: 'Tokyo', country: 'Japan', airport: 'Narita International Airport' },
    'HND': { city: 'Tokyo', country: 'Japan', airport: 'Haneda Airport' },
    'KIX': { city: 'Osaka', country: 'Japan', airport: 'Kansai International Airport' },
    'BKK': { city: 'Bangkok', country: 'Thailand', airport: 'Suvarnabhumi Airport' },
    'SIN': { city: 'Singapore', country: 'Singapore', airport: 'Singapore Changi Airport' },
    'SGN': { city: 'Ho Chi Minh City', country: 'Vietnam', airport: 'Tan Son Nhat Airport' },
    'HAN': { city: 'Hanoi', country: 'Vietnam', airport: 'Noi Bai International Airport' },
    'CDG': { city: 'Paris', country: 'France', airport: 'Charles de Gaulle Airport' },
    'DXB': { city: 'Dubai', country: 'UAE', airport: 'Dubai International Airport' },
      'LHR': { city: 'London', country: 'UK', airport: 'Heathrow Airport' }
    };

  const CITY_ALIASES = {
    'seoul': 'ICN',
    'tokyo': 'NRT',
    'bangkok': 'BKK',
    'singapore': 'SIN',
    'hanoi': 'HAN',
    'ho chi minh': 'SGN',
    'saigon': 'SGN',
    'paris': 'CDG',
    'dubai': 'DXB',
    'london': 'LHR',
    'osaka': 'KIX',
    'busan': 'PUS'
  };

  var ACCESS_HASH = '46eaa26621e4955c1675b55d446c6d03325f458b59a465f898d42924010e7286';
  var SESSION_KEY = 'travel_planner_unlocked';

  function sha256(str) {
    var buf = new TextEncoder().encode(str);
    return crypto.subtle.digest('SHA-256', buf).then(function(hash) {
      var hex = '';
      var bytes = new Uint8Array(hash);
      for (var i = 0; i < bytes.length; i++) hex += bytes[i].toString(16).padStart(2, '0');
      return hex;
    });
  }

  class TravelPlanner {
    constructor() {
      this.currentTrip = null;
      this.trips = [];
      this.loadTrips();
      this.initEventListeners();
    }

    initEventListeners() {
      // Listen for destination selection from destination search service
      window.addEventListener('destinationSelected', () => {
        this.updateGenerateButtonState();
      });

      // Listen for date changes
      document.getElementById('tpDeparture').addEventListener('change', () => {
        this.updateGenerateButtonState();
      });

      document.getElementById('tpReturn').addEventListener('change', () => {
        this.updateGenerateButtonState();
      });

      // Toggle advanced options
      document.getElementById('tpToggleAdvanced').addEventListener('click', () => {
        const advancedFields = document.getElementById('tpAdvancedFields');
        const icon = document.querySelector('.travel-planner__toggle-icon');
        const isHidden = advancedFields.style.display === 'none';
        advancedFields.style.display = isHidden ? 'block' : 'none';
        icon.classList.toggle('rotated');
      });

      // Generate button
      document.getElementById('tpGenerateBtn').addEventListener('click', () => {
        this.generateItinerary();
      });

      // Clear button
      document.getElementById('tpClearBtn').addEventListener('click', () => {
        this.clearForm();
      });

      // Export buttons
      document.getElementById('tpExportPDF').addEventListener('click', () => {
        this.exportPDF();
      });

      document.getElementById('tpExportPrint').addEventListener('click', () => {
        window.print();
      });

      // History buttons
      document.getElementById('tpNewTrip').addEventListener('click', () => {
        this.clearForm();
        document.getElementById('tpResult').style.display = 'none';
      });

      document.getElementById('tpDuplicateTrip').addEventListener('click', () => {
        if (this.currentTrip) {
          this.duplicateTrip();
        }
      });

      document.getElementById('tpDeleteTrip').addEventListener('click', () => {
        if (confirm('Xóa chuyến đi này?')) {
          this.deleteTrip();
        }
      });

      // Visa mode change
      document.getElementById('tpVisaMode').addEventListener('change', (e) => {
        if (e.target.value === 'visa' && this.currentTrip) {
          if (window.VisaItineraryRenderer) {
            window.VisaItineraryRenderer.renderDocument(
              this.currentTrip.itinerary,
              this.currentTrip
            );
          }
        }
      });
    }

    handleDestinationInput(value) {
      if (!value) {
        document.getElementById('tpDestinationList').style.display = 'none';
        return;
      }

      const query = value.toUpperCase().trim();
      const matches = [];

      // Check IATA codes
      for (const [code, info] of Object.entries(IATA_DATABASE)) {
        if (code.includes(query)) {
          matches.push({ code, ...info });
        }
      }

      // Check city aliases
      for (const [alias, code] of Object.entries(CITY_ALIASES)) {
        if (alias.includes(query.toLowerCase())) {
          const info = IATA_DATABASE[code];
          if (info && !matches.some(m => m.code === code)) {
            matches.push({ code, ...info });
          }
        }
      }

      if (matches.length === 0) {
        document.getElementById('tpDestinationList').style.display = 'none';
        return;
      }

      const list = document.getElementById('tpDestinationList');
      list.innerHTML = matches.map(m => `
        <div class="travel-planner__autocomplete-item" data-code="${m.code}" data-city="${m.city}" data-country="${m.country}">
          <strong>${m.code}</strong> - ${m.city}, ${m.country}
        </div>
      `).join('');

      list.style.display = 'block';

      list.querySelectorAll('.travel-planner__autocomplete-item').forEach(item => {
        item.addEventListener('click', () => {
          this.selectDestination(item.dataset.code, item.dataset.city, item.dataset.country);
        });
      });
    }

    selectDestination(code, city, country) {
      document.getElementById('tpDestination').value = code;
      document.getElementById('tpDestinationInfo').style.display = 'flex';
      document.getElementById('tpInfoCity').textContent = city;
      document.getElementById('tpInfoCountry').textContent = country;
      document.getElementById('tpDestinationList').style.display = 'none';
    }

    async generateItinerary() {
      // Get selected destination from destination search service
      const selectedDest = window.DestinationSearch?.getSelectedDestination?.();
      const departure = document.getElementById('tpDeparture').value;
      const returnDate = document.getElementById('tpReturn').value;

      // Validation
      if (!selectedDest) {
        this.showError('Vui lòng chọn điểm đến từ danh sách.');
        return;
      }

      if (!departure || !returnDate) {
        this.showError('Vui lòng chọn ngày đi và ngày về.');
        return;
      }

      if (new Date(departure) >= new Date(returnDate)) {
        this.showError('Ngày về phải sau ngày đi.');
        return;
      }

      const departureDate = new Date(departure);
      const returnDateObj = new Date(returnDate);
      const days = Math.ceil((returnDateObj - departureDate) / (1000 * 60 * 60 * 24));

      if (days > 30) {
        this.showError('Chuyến đi không được vượt quá 30 ngày.');
        return;
      }

      // Show progress
      this.showProgress();

      try {
        // Collect trip data with full destination info
        const tripData = {
          destination: selectedDest.iata || selectedDest.city,
          destinationData: selectedDest, // Full destination object
          departure,
          returnDate,
          adults: parseInt(document.getElementById('tpAdults').value) || 1,
          children: parseInt(document.getElementById('tpChildren').value) || 0,
          budget: document.querySelector('input[name="tpBudget"]:checked').value,
          purposes: Array.from(document.querySelectorAll('input[class="travel-planner__checkbox-input"]:checked'))
            .map(cb => cb.value),
          visaMode: document.getElementById('tpVisaMode').value,
          days
        };

        // Call AI engine
        const itinerary = await TravelAIEngine.generateItinerary(tripData);

        this.currentTrip = {
          id: Date.now(),
          ...tripData,
          itinerary,
          createdAt: new Date().toISOString()
        };

        this.saveTrips();
        this.displayResult(itinerary, tripData);
        this.hideProgress();
      } catch (error) {
        this.showError('Lỗi: ' + error.message);
        this.hideProgress();
      }
    }

    displayResult(itinerary, tripData) {
      if (window.TravelPlannerUI && window.TravelPlannerUI.displayResults) {
        window.TravelPlannerUI.displayResults(itinerary, tripData);
      }
    }

    exportPDF() {
      if (!this.currentTrip) return;
      window.print();
    }

    duplicateTrip() {
      if (!this.currentTrip) return;

      const trip = JSON.parse(JSON.stringify(this.currentTrip));
      trip.id = Date.now();
      trip.createdAt = new Date().toISOString();

      this.trips.push(trip);
      this.saveTrips();

      this.showSuccess('Chuyến đi đã được nhân bản');
    }

    deleteTrip() {
      if (!this.currentTrip) return;

      this.trips = this.trips.filter(t => t.id !== this.currentTrip.id);
      this.saveTrips();

      this.currentTrip = null;
      document.getElementById('tpResult').style.display = 'none';
      this.clearForm();
    }

    clearForm() {
      if (window.DestinationSearch) {
        window.DestinationSearch.clearSelection();
      }
      document.getElementById('tpDeparture').value = '';
      document.getElementById('tpReturn').value = '';
      document.getElementById('tpAdults').value = '1';
      document.getElementById('tpChildren').value = '0';
      document.getElementById('tpVisaMode').value = 'none';
      document.getElementById('tpAdvancedFields').style.display = 'none';
      document.getElementById('tpError').style.display = 'none';
    }

    showProgress() {
      document.getElementById('tpProgress').style.display = 'block';
      let progress = 0;
      const interval = setInterval(() => {
        progress += Math.random() * 30;
        if (progress > 90) progress = 90;
        document.getElementById('tpProgressFill').style.width = progress + '%';
      }, 300);

      // Simulate completion
      setTimeout(() => {
        clearInterval(interval);
        document.getElementById('tpProgressFill').style.width = '100%';
      }, 3000);
    }

    hideProgress() {
      setTimeout(() => {
        document.getElementById('tpProgress').style.display = 'none';
        document.getElementById('tpProgressFill').style.width = '0%';
      }, 500);
    }

    showError(message) {
      const errorEl = document.getElementById('tpError');
      document.getElementById('tpErrorText').textContent = message;
      errorEl.style.display = 'block';
      document.getElementById('tpResult').style.display = 'none';
    }

    showSuccess(message) {
      alert(message);
    }

    updateGenerateButtonState() {
      const selectedDest = window.DestinationSearch?.getSelectedDestination?.();
      const departure = document.getElementById('tpDeparture').value;
      const returnDate = document.getElementById('tpReturn').value;
      const generateBtn = document.getElementById('tpGenerateBtn');

      const isValid = selectedDest && departure && returnDate &&
        new Date(departure) < new Date(returnDate);

      generateBtn.disabled = !isValid;
      generateBtn.style.opacity = isValid ? '1' : '0.5';
    }

    formatDate(timestamp) {
      const date = new Date(timestamp);
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }

    loadTrips() {
      const stored = localStorage.getItem('travelPlannerTrips');
      this.trips = stored ? JSON.parse(stored) : [];
    }

    saveTrips() {
      localStorage.setItem('travelPlannerTrips', JSON.stringify(this.trips));
    }
  }

  // ─── Access Gate ─────────────────────────────────────
  function initGate() {
    var gate = document.getElementById('tpGate');
    var app = document.getElementById('tpApp');
    var input = document.getElementById('tpGateInput');
    var btn = document.getElementById('tpGateUnlock');
    var err = document.getElementById('tpGateError');
    var lockBtn = document.getElementById('tpLockBtn');
    var attemptCount = 0;
    var lastAttempt = 0;

    lockBtn.addEventListener('click', function() {
      sessionStorage.removeItem(SESSION_KEY);
      gate.style.display = 'flex';
      app.style.display = 'none';
      lockBtn.style.display = 'none';
      input.value = '';
      err.textContent = '';
      attemptCount = 0;
      input.focus();
    });

    if (sessionStorage.getItem(SESSION_KEY) === '1') {
      gate.style.display = 'none';
      app.style.display = '';
      lockBtn.style.display = '';
      window.TravelPlanner = new TravelPlanner();
      return;
    }

    function doUnlock() {
      var code = input.value.trim();
      if (!code || code.length !== 4) {
        err.textContent = 'Vui lòng nhập đủ 4 số.';
        return;
      }
      var now = Date.now();
      if (now - lastAttempt < 2000) {
        err.textContent = 'Quá nhanh. Vui lòng đợi 2 giây.';
        return;
      }
      lastAttempt = now;
      attemptCount++;
      if (attemptCount > 5) {
        err.textContent = 'Quá nhiều lần thử. Tải lại trang để thử lại.';
        btn.disabled = true;
        input.disabled = true;
        return;
      }
      sha256(code).then(function(hash) {
        if (hash === ACCESS_HASH) {
          sessionStorage.setItem(SESSION_KEY, '1');
          gate.style.display = 'none';
          app.style.display = '';
          lockBtn.style.display = '';
          window.TravelPlanner = new TravelPlanner();
        } else {
          err.textContent = 'Mã truy cập không đúng. Còn ' + (5 - attemptCount) + ' lần thử.';
          input.value = '';
          input.focus();
        }
      });
    }

    btn.addEventListener('click', doUnlock);
    input.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') doUnlock();
    });
    input.focus();
  }

  initGate();
})();
