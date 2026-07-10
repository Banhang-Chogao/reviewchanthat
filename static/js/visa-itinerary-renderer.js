(function() {
  'use strict';

  class VisaItineraryRenderer {
    /**
     * Render professional visa-suitable itinerary document
     * Using HTML tables for printing and Excel export
     */

    static renderDocument(itinerary, tripData) {
      const container = document.getElementById('tpVisaDocument');
      if (!container) return;

      const destData = tripData.destinationData || {};
      const city = destData.city || tripData.destination;
      const country = destData.country || '';
      const iata = destData.iata || '';
      const today = new Date().toLocaleDateString('en-US', {
        year: 'numeric', month: 'long', day: 'numeric'
      });

      container.innerHTML = `
        <div class="visa-itinerary-document">
          <!-- Header -->
          <div class="visa-header">
            <h1>VISA APPLICATION ITINERARY</h1>
            <p>Prepared for embassy submission · Generated: ${today}</p>
          </div>

          <!-- Applicant Information -->
          <div class="visa-section">
            <h2>Applicant Information</h2>
            ${this.renderApplicantTable(tripData, city, country, iata)}
          </div>

          <!-- Daily Itinerary -->
          <div class="visa-section">
            <h2>Daily Itinerary</h2>
            ${this.renderDailyItineraryTable(itinerary, tripData)}
          </div>

          <!-- Accommodation Plan -->
          <div class="visa-section">
            <h2>Accommodation Plan</h2>
            ${this.renderAccommodationTable(itinerary)}
          </div>

          <!-- Transportation Plan -->
          <div class="visa-section">
            <h2>Transportation Plan</h2>
            ${this.renderTransportationTable(itinerary)}
          </div>

          <!-- Estimated Budget -->
          <div class="visa-section">
            <h2>Estimated Budget</h2>
            ${this.renderBudgetTable(itinerary)}
          </div>

          <!-- Important Notes -->
          <div class="visa-section">
            <h2>Important Notes</h2>
            ${this.renderImportantNotesTable(itinerary, destData)}
          </div>
        </div>
      `;
    }

    static renderApplicantTable(tripData, city, country, iata) {
      const startDate = new Date(tripData.departure).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
      const endDate = new Date(tripData.returnDate).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
      const days = Math.ceil((new Date(tripData.returnDate) - new Date(tripData.departure)) / (1000 * 60 * 60 * 24));

      return `
        <table class="visa-table">
          <tbody>
            <tr>
              <td class="visa-table__label">Destination</td>
              <td class="visa-table__value">${city}, ${country}</td>
            </tr>
            <tr>
              <td class="visa-table__label">Airport</td>
              <td class="visa-table__value">${iata}</td>
            </tr>
            <tr>
              <td class="visa-table__label">Arrival Date</td>
              <td class="visa-table__value">${startDate}</td>
            </tr>
            <tr>
              <td class="visa-table__label">Departure Date</td>
              <td class="visa-table__value">${endDate}</td>
            </tr>
            <tr>
              <td class="visa-table__label">Total Days</td>
              <td class="visa-table__value">${days}</td>
            </tr>
            <tr>
              <td class="visa-table__label">Purpose</td>
              <td class="visa-table__value">${tripData.purposes?.join(', ') || 'Tourism'}</td>
            </tr>
          </tbody>
        </table>
      `;
    }

    static renderDailyItineraryTable(itinerary, tripData) {
      const startDate = new Date(tripData.departure);
      const days = itinerary.dailyItinerary || [];

      const rows = days.map((day, idx) => {
        const date = new Date(startDate);
        date.setDate(date.getDate() + idx);
        const dateStr = date.toLocaleDateString('en-US', {
          weekday: 'short', month: 'short', day: 'numeric'
        });

        return `
          <tr>
            <td class="visa-table__center">${idx + 1}</td>
            <td>${dateStr}</td>
            <td>${day.morning || '-'}</td>
            <td>${day.lunch || '-'}</td>
            <td>${day.afternoon || '-'}</td>
            <td>${day.dinner || '-'}</td>
            <td>${day.notes || '-'}</td>
          </tr>
        `;
      }).join('');

      return `
        <div class="visa-table-wrapper">
          <table class="visa-table visa-table--striped">
            <thead>
              <tr>
                <th>Day</th>
                <th>Date</th>
                <th>Morning</th>
                <th>Lunch</th>
                <th>Afternoon</th>
                <th>Dinner</th>
                <th>Remarks</th>
              </tr>
            </thead>
            <tbody>
              ${rows}
            </tbody>
          </table>
        </div>
      `;
    }

    static renderAccommodationTable(itinerary) {
      const accommodations = [
        {
          checkIn: itinerary.departure || '-',
          checkOut: itinerary.returnDate || '-',
          area: itinerary.hotelArea || '-',
          notes: itinerary.hotelNotes || '-'
        }
      ];

      const rows = accommodations.map(acc => `
        <tr>
          <td>${acc.checkIn}</td>
          <td>${acc.checkOut}</td>
          <td>${acc.area}</td>
          <td>${acc.notes}</td>
        </tr>
      `).join('');

      return `
        <div class="visa-table-wrapper">
          <table class="visa-table">
            <thead>
              <tr>
                <th>Check-in</th>
                <th>Check-out</th>
                <th>Recommended Area</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              ${rows}
            </tbody>
          </table>
        </div>
      `;
    }

    static renderTransportationTable(itinerary) {
      return `
        <div class="visa-table-wrapper">
          <table class="visa-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>From</th>
                <th>To</th>
                <th>Transport Method</th>
                <th>Estimated Duration</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Arrival</td>
                <td>${itinerary.airport || 'Airport'}</td>
                <td>${itinerary.hotelArea || 'Hotel'}</td>
                <td>${itinerary.arrivalTransport || 'Taxi/Shuttle'}</td>
                <td>1-2 hours</td>
              </tr>
              <tr>
                <td>Departure</td>
                <td>${itinerary.hotelArea || 'Hotel'}</td>
                <td>${itinerary.airport || 'Airport'}</td>
                <td>${itinerary.departureTransport || 'Taxi/Shuttle'}</td>
                <td>1-2 hours</td>
              </tr>
            </tbody>
          </table>
        </div>
      `;
    }

    static renderBudgetTable(itinerary) {
      const budget = itinerary.estimatedBudget || 'Not specified';
      const budgetLevel = itinerary.budget || 'Mid-range';

      return `
        <div class="visa-table-wrapper">
          <table class="visa-table">
            <thead>
              <tr>
                <th>Category</th>
                <th class="visa-table__right">Estimated Cost</th>
                <th>Currency</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Total Estimated Budget (${budgetLevel})</td>
                <td class="visa-table__right">${budget}</td>
                <td>${itinerary.currency || 'USD'}</td>
              </tr>
            </tbody>
          </table>
        </div>
      `;
    }

    static renderImportantNotesTable(itinerary, destData) {
      return `
        <div class="visa-table-wrapper">
          <table class="visa-table">
            <tbody>
              <tr>
                <td class="visa-table__label">Emergency Contact</td>
                <td>${itinerary.emergencyNumbers || 'Check local embassy website'}</td>
              </tr>
              <tr>
                <td class="visa-table__label">Travel Insurance</td>
                <td>Recommended for international travel</td>
              </tr>
              <tr>
                <td class="visa-table__label">Travel Documents</td>
                <td>Passport, visa (if required), travel insurance, vaccination records</td>
              </tr>
              <tr>
                <td class="visa-table__label">Currency</td>
                <td>${destData.currency || 'See local guidelines'}</td>
              </tr>
              <tr>
                <td class="visa-table__label">Timezone</td>
                <td>${destData.timezone || 'Check destination'}</td>
              </tr>
              <tr>
                <td class="visa-table__label">Local Tips</td>
                <td>${itinerary.localTips || 'Respect local customs and traditions'}</td>
              </tr>
            </tbody>
          </table>
        </div>
      `;
    }
  }

  window.VisaItineraryRenderer = VisaItineraryRenderer;
})();
