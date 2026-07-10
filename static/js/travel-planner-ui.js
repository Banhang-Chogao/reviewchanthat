/**
 * Travel Planner UI Rendering Layer
 * Handles S-DNA design formatting for results display
 * Does NOT change business logic - only UI presentation
 */

(function() {
  'use strict';

  class TravelPlannerUI {
    /**
     * Render KPI summary cards
     */
    static renderSummaryCards(tripData, itinerary) {
      const container = document.getElementById('tpSummaryCards');
      if (!container) return;

      const destData = tripData.destinationData || {};
      const city = destData.city || tripData.destination;
      const startDate = new Date(tripData.departure);
      const endDate = new Date(tripData.returnDate);
      const days = Math.ceil((endDate - startDate) / (1000 * 60 * 60 * 24));

      const cards = [
        {
          label: 'Điểm đến',
          value: city,
          icon: '📍'
        },
        {
          label: 'Khoảng cách',
          value: `${days} ngày`,
          icon: '📅'
        },
        {
          label: 'Ngày khởi hành',
          value: startDate.toLocaleDateString('vi-VN'),
          icon: '✈️'
        },
        {
          label: 'Ngân sách dự tính',
          value: itinerary.estimatedBudget || 'TBD',
          icon: '💰'
        }
      ];

      container.innerHTML = cards.map(card => `
        <div class="travel-planner__kpi-card">
          <span style="font-size:1.5rem;display:block;margin-bottom:0.5rem">${card.icon}</span>
          <span class="travel-planner__kpi-label">${card.label}</span>
          <span class="travel-planner__kpi-value">${card.value}</span>
        </div>
      `).join('');
    }

    /**
     * Render daily timeline
     */
    static renderTimeline(itinerary, tripData) {
      const timelineEl = document.getElementById('tpTimeline');
      if (!timelineEl) return;

      const dailyItinerary = itinerary.dailyItinerary || [];
      const startDate = new Date(tripData.departure);

      timelineEl.innerHTML = dailyItinerary.map((day, idx) => {
        const date = new Date(startDate);
        date.setDate(date.getDate() + idx);
        const dateStr = date.toLocaleDateString('vi-VN');

        const activities = [
          { label: 'Sáng', value: day.morning },
          { label: 'Trưa', value: day.lunch },
          { label: 'Chiều', value: day.afternoon },
          { label: 'Tối', value: day.dinner }
        ].filter(a => a.value);

        return `
          <div class="travel-planner__day-card">
            <div class="travel-planner__day-header">Ngày ${idx + 1} — ${dateStr}</div>
            ${activities.map(a => `
              <div class="travel-planner__time-section">
                <span class="travel-planner__time-label">${a.label}</span>
                <div class="travel-planner__activity">${a.value}</div>
              </div>
            `).join('')}
            ${day.notes ? `<div style="font-size:0.85rem;color:#666;margin-top:0.5rem">📝 ${day.notes}</div>` : ''}
          </div>
        `;
      }).join('');

      document.getElementById('tpTimelineSection').style.display = 'block';
    }

    /**
     * Render info cards (hotel, transport, weather, tips, emergency)
     */
    static renderInfoCards(itinerary) {
      const container = document.getElementById('tpInfoCards');
      if (!container) return;

      const cards = [
        {
          title: '🏨 Khu vực lưu trú',
          content: itinerary.hotelArea || 'TBD'
        },
        {
          title: '🚕 Giao thông',
          content: itinerary.transportation || 'TBD'
        },
        {
          title: '🌤️ Thời tiết',
          content: (itinerary.weatherNotes || 'N/A') + '<br><small>' + (itinerary.weather || '') + '</small>'
        },
        {
          title: '💡 Mẹo địa phương',
          content: itinerary.localTips || 'N/A'
        },
        {
          title: '🆘 Liên hệ khẩn cấp',
          content: itinerary.emergencyNumbers || 'N/A'
        },
        {
          title: '✈️ Hướng dẫn sân bay',
          content: itinerary.airportNotes || 'N/A'
        }
      ];

      container.innerHTML = cards.map(card => `
        <div class="travel-planner__info-card">
          <h3 class="travel-planner__info-card__title">${card.title}</h3>
          <div class="travel-planner__info-card__content">${card.content}</div>
        </div>
      `).join('');
    }

    /**
     * Render packing checklist
     */
    static renderPackingList(itinerary) {
      const packingCard = document.getElementById('tpPackingCard');
      const packingChecklist = document.getElementById('tpPackingChecklist');

      if (!packingCard || !packingChecklist) return;

      const items = itinerary.packingList || [];
      if (items.length === 0) {
        packingCard.style.display = 'none';
        return;
      }

      packingChecklist.innerHTML = items.map((item, idx) => `
        <label class="travel-planner__checklist-item">
          <input type="checkbox" data-item="${idx}">
          <span class="travel-planner__checklist-label">${item}</span>
        </label>
      `).join('');

      packingCard.style.display = 'block';
    }

    /**
     * Render AI recommendations
     */
    static renderRecommendations(itinerary, tripData) {
      const container = document.getElementById('tpRecommendations');
      if (!container) return;
      const days = tripData?.days || itinerary?.days || 'N/A';

      const recommendations = [
        {
          severity: 'info',
          text: `Chuyến du lịch ${days} ngày. Thời gian lý tưởng để khám phá và thư giãn.`
        },
        {
          severity: 'success',
          text: `Ngân sách dự tính: ${itinerary.estimatedBudget || 'TBD'}. Hãy đặt trước các hoạt động chính.`
        },
        {
          severity: 'warning',
          text: `Kiểm tra yêu cầu visa trước khi đặt vé. Chuẩn bị tài liệu sớm.`
        }
      ];

      container.innerHTML = `
        <div style="margin-bottom:1.5rem">
          <h3 style="font-size:1.1rem;font-weight:700;margin-bottom:0.75rem">💡 Khuyến nghị</h3>
          <div class="travel-planner__recommendations">
            ${recommendations.map(rec => `
              <div class="travel-planner__rec-item travel-planner__rec-item--${rec.severity}">
                ${rec.text}
              </div>
            `).join('')}
          </div>
        </div>
      `;
    }


    /**
     * Display all results
     */
    static displayResults(itinerary, tripData) {
      // Render each section
      this.renderSummaryCards(tripData, itinerary);
      this.renderTimeline(itinerary, tripData);
      this.renderInfoCards(itinerary);
      this.renderPackingList(itinerary);
      this.renderRecommendations(itinerary, tripData);

      // Render professional visa itinerary document (only when visa mode is active)
      if (tripData.visaMode === 'visa' && window.VisaItineraryRenderer) {
        window.VisaItineraryRenderer.renderDocument(itinerary, tripData);
      }

      // Show result container
      document.getElementById('tpResult').style.display = 'block';
      document.getElementById('tpError').style.display = 'none';
      document.getElementById('tpProgress').style.display = 'none';

      // Scroll to results
      document.getElementById('tpResult').scrollIntoView({ behavior: 'smooth' });
    }

    /**
     * Update version badge
     */
    static updateVersionBadge(version) {
      const badge = document.getElementById('tpVersionBadge');
      if (badge) {
        badge.textContent = `Phiên bản dịch vụ: ${version}`;
      }
    }
  }

  // Expose globally
  window.TravelPlannerUI = TravelPlannerUI;
})();
