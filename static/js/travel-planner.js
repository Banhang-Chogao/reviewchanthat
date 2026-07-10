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
    'LHR': { city: 'London', country: 'UK', airport: 'Heathrow Airport' },
    'NRT': { city: 'Tokyo', country: 'Japan', airport: 'Narita International Airport' }
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

      document.getElementById('tpExportExcel').addEventListener('click', () => {
        this.exportExcel();
      });

      document.getElementById('tpExportMarkdown').addEventListener('click', () => {
        this.exportMarkdown();
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
        if (e.target.value === 'visa') {
          this.generateVisaItinerary();
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
      document.getElementById('tpError').style.display = 'none';
      document.getElementById('tpResult').style.display = 'block';

      // Update summary - use destination data from API
      const destData = tripData.destinationData || {};
      const city = destData.city || tripData.destination;
      const country = destData.country || '';
      document.getElementById('tpSummaryDest').textContent = country ? `${city}, ${country}` : city;
      document.getElementById('tpSummaryDuration').textContent = `${tripData.days} ngày`;
      document.getElementById('tpSummaryWeather').textContent = itinerary.weather || 'N/A';
      document.getElementById('tpSummaryBudget').textContent = itinerary.estimatedBudget || 'TBD';

      // Update daily itinerary
      const timeline = document.getElementById('tpTimeline');
      timeline.innerHTML = itinerary.dailyItinerary.map((day, idx) => `
        <div class="travel-planner__day-card">
          <div class="travel-planner__day-header">
            <h3 class="travel-planner__day-title">Day ${idx + 1}</h3>
            <span class="travel-planner__day-date">${this.formatDate(new Date(tripData.departure).getTime() + idx * 24 * 60 * 60 * 1000)}</span>
          </div>
          ${day.morning ? `<div class="travel-planner__time-block">
            <span class="travel-planner__time-label">Morning</span>
            <div class="travel-planner__activity">${day.morning}</div>
          </div>` : ''}
          ${day.lunch ? `<div class="travel-planner__time-block">
            <span class="travel-planner__time-label">Lunch</span>
            <div class="travel-planner__activity">${day.lunch}</div>
          </div>` : ''}
          ${day.afternoon ? `<div class="travel-planner__time-block">
            <span class="travel-planner__time-label">Afternoon</span>
            <div class="travel-planner__activity">${day.afternoon}</div>
          </div>` : ''}
          ${day.dinner ? `<div class="travel-planner__time-block">
            <span class="travel-planner__time-label">Dinner</span>
            <div class="travel-planner__activity">${day.dinner}</div>
          </div>` : ''}
          ${day.notes ? `<div class="travel-planner__activity-detail">${day.notes}</div>` : ''}
        </div>
      `).join('');

      // Update hotel & transportation
      document.getElementById('tpHotelArea').textContent = itinerary.hotelArea || 'TBD';
      document.getElementById('tpTransport').textContent = itinerary.transportation || 'TBD';

      // Update packing list
      const packingList = document.getElementById('tpPackingList');
      packingList.innerHTML = (itinerary.packingList || []).map(item => `<li>${item}</li>`).join('');

      // Update weather & tips
      const weatherTips = document.getElementById('tpWeatherTips');
      weatherTips.innerHTML = `
        <p><strong>Weather:</strong> ${itinerary.weatherNotes || 'N/A'}</p>
        <p><strong>Tips:</strong> ${itinerary.localTips || 'N/A'}</p>
      `;

      // Update emergency info
      const emergencyInfo = document.getElementById('tpEmergencyInfo');
      emergencyInfo.innerHTML = `
        <p><strong>Emergency:</strong> ${itinerary.emergencyNumbers || 'N/A'}</p>
        <p><strong>Airport Notes:</strong> ${itinerary.airportNotes || 'N/A'}</p>
      `;

      // Show visa section if applicable
      if (tripData.visaMode === 'visa') {
        this.displayVisaItinerary(itinerary);
      }

      // Scroll to result
      document.getElementById('tpResult').scrollIntoView({ behavior: 'smooth' });
    }

    displayVisaItinerary(itinerary) {
      const visaSection = document.getElementById('tpVisaSection');
      const visaTableBody = document.getElementById('tpVisaTableBody');

      visaTableBody.innerHTML = itinerary.visaItinerary.map(entry => `
        <tr>
          <td>${entry.date}</td>
          <td>${entry.day}</td>
          <td>${entry.activity}</td>
          <td>${entry.accommodation}</td>
        </tr>
      `).join('');

      visaSection.style.display = 'block';
    }

    generateVisaItinerary() {
      if (!this.currentTrip) return;
      this.displayVisaItinerary(this.currentTrip.itinerary);
    }

    exportPDF() {
      if (!this.currentTrip) return;

      const docTitle = `Travel-Itinerary-${this.currentTrip.destination}-${this.currentTrip.departure}`;
      const url = `/api/export/pdf?trip=${encodeURIComponent(JSON.stringify(this.currentTrip))}`;

      fetch(url)
        .then(r => r.blob())
        .then(blob => {
          const a = document.createElement('a');
          a.href = URL.createObjectURL(blob);
          a.download = `${docTitle}.pdf`;
          a.click();
        })
        .catch(err => this.showError('Export PDF failed: ' + err.message));
    }

    exportExcel() {
      if (!this.currentTrip) return;

      const docTitle = `Travel-Itinerary-${this.currentTrip.destination}`;
      const url = `/api/export/excel?trip=${encodeURIComponent(JSON.stringify(this.currentTrip))}`;

      fetch(url)
        .then(r => r.blob())
        .then(blob => {
          const a = document.createElement('a');
          a.href = URL.createObjectURL(blob);
          a.download = `${docTitle}.xlsx`;
          a.click();
        })
        .catch(err => this.showError('Export Excel failed: ' + err.message));
    }

    exportMarkdown() {
      if (!this.currentTrip) return;

      const md = this.generateMarkdown();
      const blob = new Blob([md], { type: 'text/markdown' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `Travel-Itinerary-${this.currentTrip.destination}.md`;
      a.click();
    }

    generateMarkdown() {
      const trip = this.currentTrip;
      const itinerary = trip.itinerary;
      const city = IATA_DATABASE[trip.destination]?.city || trip.destination;

      let md = `# Travel Itinerary: ${city}\n\n`;
      md += `**Departure:** ${trip.departure}\n`;
      md += `**Return:** ${trip.returnDate}\n`;
      md += `**Duration:** ${trip.days} days\n\n`;

      md += `## Summary\n\n`;
      md += `- Weather: ${itinerary.weather}\n`;
      md += `- Hotel Area: ${itinerary.hotelArea}\n`;
      md += `- Estimated Budget: ${itinerary.estimatedBudget}\n\n`;

      md += `## Daily Itinerary\n\n`;
      itinerary.dailyItinerary.forEach((day, idx) => {
        md += `### Day ${idx + 1}\n`;
        if (day.morning) md += `- **Morning:** ${day.morning}\n`;
        if (day.lunch) md += `- **Lunch:** ${day.lunch}\n`;
        if (day.afternoon) md += `- **Afternoon:** ${day.afternoon}\n`;
        if (day.dinner) md += `- **Dinner:** ${day.dinner}\n`;
        if (day.notes) md += `- *Notes:* ${day.notes}\n`;
        md += '\n';
      });

      md += `## Packing List\n\n`;
      itinerary.packingList.forEach(item => {
        md += `- ${item}\n`;
      });

      return md;
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
      document.getElementById('tpDestination').value = '';
      document.getElementById('tpDeparture').value = '';
      document.getElementById('tpReturn').value = '';
      document.getElementById('tpAdults').value = '1';
      document.getElementById('tpChildren').value = '0';
      document.getElementById('tpVisaMode').value = 'none';
      document.getElementById('tpDestinationInfo').style.display = 'none';
      document.getElementById('tpAdvancedFields').style.display = 'none';
      document.querySelector('.travel-planner__toggle-icon').classList.remove('rotated');
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

  // Initialize
  window.TravelPlanner = new TravelPlanner();
})();
