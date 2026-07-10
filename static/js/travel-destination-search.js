(function() {
  'use strict';

  // Configuration
  const CONFIG = {
    debounceMs: 300,
    cacheExpiryMs: 30 * 60 * 1000, // 30 minutes
    maxResults: 10,
    minChars: 2,
    apiBaseUrl: '/api/destination/search',
    fallbackCities: {
      'ICN': { city: 'Seoul', country: 'South Korea', iata: 'ICN', timezone: 'Asia/Seoul', flag: '🇰🇷' },
      'NRT': { city: 'Tokyo', country: 'Japan', iata: 'NRT', timezone: 'Asia/Tokyo', flag: '🇯🇵' },
      'HND': { city: 'Tokyo Haneda', country: 'Japan', iata: 'HND', timezone: 'Asia/Tokyo', flag: '🇯🇵' },
      'KIX': { city: 'Osaka', country: 'Japan', iata: 'KIX', timezone: 'Asia/Tokyo', flag: '🇯🇵' },
      'BKK': { city: 'Bangkok', country: 'Thailand', iata: 'BKK', timezone: 'Asia/Bangkok', flag: '🇹🇭' },
      'CNX': { city: 'Chiang Mai', country: 'Thailand', iata: 'CNX', timezone: 'Asia/Bangkok', flag: '🇹🇭' },
      'SGN': { city: 'Ho Chi Minh City', country: 'Vietnam', iata: 'SGN', timezone: 'Asia/Ho_Chi_Minh', flag: '🇻🇳' },
      'HAN': { city: 'Hanoi', country: 'Vietnam', iata: 'HAN', timezone: 'Asia/Ho_Chi_Minh', flag: '🇻🇳' },
      'DAD': { city: 'Da Nang', country: 'Vietnam', iata: 'DAD', timezone: 'Asia/Ho_Chi_Minh', flag: '🇻🇳' },
      'CDG': { city: 'Paris', country: 'France', iata: 'CDG', timezone: 'Europe/Paris', flag: '🇫🇷' },
      'LHR': { city: 'London', country: 'United Kingdom', iata: 'LHR', timezone: 'Europe/London', flag: '🇬🇧' },
      'FCO': { city: 'Rome', country: 'Italy', iata: 'FCO', timezone: 'Europe/Rome', flag: '🇮🇹' },
      'BCN': { city: 'Barcelona', country: 'Spain', iata: 'BCN', timezone: 'Europe/Madrid', flag: '🇪🇸' },
      'MUC': { city: 'Munich', country: 'Germany', iata: 'MUC', timezone: 'Europe/Berlin', flag: '🇩🇪' },
      'AMS': { city: 'Amsterdam', country: 'Netherlands', iata: 'AMS', timezone: 'Europe/Amsterdam', flag: '🇳🇱' },
      'DXB': { city: 'Dubai', country: 'UAE', iata: 'DXB', timezone: 'Asia/Dubai', flag: '🇦🇪' },
      'AUH': { city: 'Abu Dhabi', country: 'UAE', iata: 'AUH', timezone: 'Asia/Dubai', flag: '🇦🇪' },
      'SIN': { city: 'Singapore', country: 'Singapore', iata: 'SIN', timezone: 'Asia/Singapore', flag: '🇸🇬' },
      'KUL': { city: 'Kuala Lumpur', country: 'Malaysia', iata: 'KUL', timezone: 'Asia/Kuala_Lumpur', flag: '🇲🇾' },
      'MNL': { city: 'Manila', country: 'Philippines', iata: 'MNL', timezone: 'Asia/Manila', flag: '🇵🇭' },
      'CGK': { city: 'Jakarta', country: 'Indonesia', iata: 'CGK', timezone: 'Asia/Jakarta', flag: '🇮🇩' },
      'DPS': { city: 'Bali', country: 'Indonesia', iata: 'DPS', timezone: 'Asia/Makassar', flag: '🇮🇩' },
      'PVG': { city: 'Shanghai', country: 'China', iata: 'PVG', timezone: 'Asia/Shanghai', flag: '🇨🇳' },
      'PEK': { city: 'Beijing', country: 'China', iata: 'PEK', timezone: 'Asia/Shanghai', flag: '🇨🇳' },
      'HKG': { city: 'Hong Kong', country: 'China', iata: 'HKG', timezone: 'Asia/Hong_Kong', flag: '🇭🇰' },
      'TPE': { city: 'Taipei', country: 'Taiwan', iata: 'TPE', timezone: 'Asia/Taipei', flag: '🇹🇼' },
      'SYD': { city: 'Sydney', country: 'Australia', iata: 'SYD', timezone: 'Australia/Sydney', flag: '🇦🇺' },
      'MEL': { city: 'Melbourne', country: 'Australia', iata: 'MEL', timezone: 'Australia/Melbourne', flag: '🇦🇺' },
      'JFK': { city: 'New York', country: 'United States', iata: 'JFK', timezone: 'America/New_York', flag: '🇺🇸' },
      'LAX': { city: 'Los Angeles', country: 'United States', iata: 'LAX', timezone: 'America/Los_Angeles', flag: '🇺🇸' },
      'SFO': { city: 'San Francisco', country: 'United States', iata: 'SFO', timezone: 'America/Los_Angeles', flag: '🇺🇸' },
      'ORD': { city: 'Chicago', country: 'United States', iata: 'ORD', timezone: 'America/Chicago', flag: '🇺🇸' },
      'DEL': { city: 'Delhi', country: 'India', iata: 'DEL', timezone: 'Asia/Kolkata', flag: '🇮🇳' },
      'BOM': { city: 'Mumbai', country: 'India', iata: 'BOM', timezone: 'Asia/Kolkata', flag: '🇮🇳' },
      'IST': { city: 'Istanbul', country: 'Turkey', iata: 'IST', timezone: 'Europe/Istanbul', flag: '🇹🇷' },
      'ZRH': { city: 'Zurich', country: 'Switzerland', iata: 'ZRH', timezone: 'Europe/Zurich', flag: '🇨🇭' },
      'CPH': { city: 'Copenhagen', country: 'Denmark', iata: 'CPH', timezone: 'Europe/Copenhagen', flag: '🇩🇰' },
      'ARN': { city: 'Stockholm', country: 'Sweden', iata: 'ARN', timezone: 'Europe/Stockholm', flag: '🇸🇪' },
      'MAD': { city: 'Madrid', country: 'Spain', iata: 'MAD', timezone: 'Europe/Madrid', flag: '🇪🇸' },
      'LIS': { city: 'Lisbon', country: 'Portugal', iata: 'LIS', timezone: 'Europe/Lisbon', flag: '🇵🇹' },
      'VIE': { city: 'Vienna', country: 'Austria', iata: 'VIE', timezone: 'Europe/Vienna', flag: '🇦🇹' },
      'FRA': { city: 'Frankfurt', country: 'Germany', iata: 'FRA', timezone: 'Europe/Berlin', flag: '🇩🇪' },
      'BER': { city: 'Berlin', country: 'Germany', iata: 'BER', timezone: 'Europe/Berlin', flag: '🇩🇪' },
      'PRG': { city: 'Prague', country: 'Czech Republic', iata: 'PRG', timezone: 'Europe/Prague', flag: '🇨🇿' },
      'BUD': { city: 'Budapest', country: 'Hungary', iata: 'BUD', timezone: 'Europe/Budapest', flag: '🇭🇺' },
      'ATH': { city: 'Athens', country: 'Greece', iata: 'ATH', timezone: 'Europe/Athens', flag: '🇬🇷' },
      'HEL': { city: 'Helsinki', country: 'Finland', iata: 'HEL', timezone: 'Europe/Helsinki', flag: '🇫🇮' }
    }
  };

  class DestinationSearch {
    constructor() {
      this.searchInput = document.getElementById('tpDestinationSearch');
      this.dropdownList = document.getElementById('tpDestinationList');
      this.skeletonLoader = document.getElementById('tpSearchSkeleton');
      this.emptyState = document.getElementById('tpSearchEmpty');
      this.errorState = document.getElementById('tpSearchError');
      this.selectedBadge = document.getElementById('tpDestinationSelected');
      this.retryBtn = document.getElementById('tpSearchRetry');

      this.currentQuery = '';
      this.selectedDestination = null;
      this.searchCache = new Map();
      this.debounceTimer = null;
      this.abortController = null;
      this.highlightedIndex = -1;

      this.initEventListeners();
      this.loadCacheFromStorage();
    }

    initEventListeners() {
      // Input event
      this.searchInput.addEventListener('input', (e) => this.handleInput(e));

      // Keyboard navigation
      this.searchInput.addEventListener('keydown', (e) => this.handleKeydown(e));

      // Click outside to close
      document.addEventListener('click', (e) => {
        if (!e.target.closest('.travel-planner__search-wrap')) {
          this.closeDropdown();
        }
      });

      // Retry button
      this.retryBtn.addEventListener('click', () => this.retry());

      // Clear selection
      document.getElementById('tpDestinationClear')?.addEventListener('click', () => {
        this.clearSelection();
      });
    }

    handleInput(e) {
      const query = e.target.value.trim();
      this.currentQuery = query;
      this.highlightedIndex = -1;

      clearTimeout(this.debounceTimer);

      if (query.length < CONFIG.minChars) {
        this.closeDropdown();
        return;
      }

      this.searchInput.setAttribute('aria-expanded', 'true');
      this.showSkeleton();

      this.debounceTimer = setTimeout(() => {
        this.search(query);
      }, CONFIG.debounceMs);
    }

    handleKeydown(e) {
      const isOpen = this.searchInput.getAttribute('aria-expanded') === 'true';

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          if (!isOpen) return;
          this.highlightedIndex = Math.min(
            this.highlightedIndex + 1,
            this.dropdownList.children.length - 1
          );
          this.updateHighlight();
          break;

        case 'ArrowUp':
          e.preventDefault();
          if (!isOpen) return;
          this.highlightedIndex = Math.max(this.highlightedIndex - 1, -1);
          this.updateHighlight();
          break;

        case 'Enter':
          e.preventDefault();
          if (this.highlightedIndex >= 0) {
            const item = this.dropdownList.children[this.highlightedIndex];
            const destination = JSON.parse(item.dataset.destination);
            this.selectDestination(destination);
          }
          break;

        case 'Escape':
          this.closeDropdown();
          break;
      }
    }

    updateHighlight() {
      Array.from(this.dropdownList.children).forEach((item, idx) => {
        if (idx === this.highlightedIndex) {
          item.setAttribute('aria-selected', 'true');
          item.focus();
        } else {
          item.setAttribute('aria-selected', 'false');
        }
      });
    }

    getCountryFlag(country) {
      const flagMap = {
        'South Korea': '🇰🇷', 'Japan': '🇯🇵', 'Thailand': '🇹🇭',
        'Vietnam': '🇻🇳', 'Singapore': '🇸🇬', 'France': '🇫🇷',
        'UAE': '🇦🇪', 'United Kingdom': '🇬🇧', 'China': '🇨🇳',
        'India': '🇮🇳', 'Australia': '🇦🇺', 'United States': '🇺🇸',
        'Malaysia': '🇲🇾', 'Philippines': '🇵🇭', 'Indonesia': '🇮🇩',
        'Taiwan': '🇹🇼', 'Hong Kong': '🇭🇰', 'Turkey': '🇹🇷',
        'Switzerland': '🇨🇭', 'Denmark': '🇩🇰', 'Sweden': '🇸🇪',
        'Italy': '🇮🇹', 'Spain': '🇪🇸', 'Germany': '🇩🇪',
        'Netherlands': '🇳🇱', 'Portugal': '🇵🇹', 'Austria': '🇦🇹',
        'Czech Republic': '🇨🇿', 'Hungary': '🇭🇺', 'Greece': '🇬🇷',
        'Finland': '🇫🇮'
      };
      return flagMap[country] || '🌍';
    }

    async search(query) {
      // Check cache first
      const cached = this.searchCache.get(query);
      if (cached && !this.isCacheExpired(cached.timestamp)) {
        this.displayResults(cached.results, query);
        return;
      }

      // Abort previous request
      if (this.abortController) {
        this.abortController.abort();
      }

      this.abortController = new AbortController();

      try {
        // Call aviationstack API directly
        const apiResults = await this.searchAviationstack(query);
        if (apiResults && apiResults.length > 0) {
          this.searchCache.set(query, {
            results: apiResults,
            timestamp: Date.now()
          });
          this.displayResults(apiResults, query);
          return;
        }
      } catch (error) {
        if (error.name === 'AbortError') return;
        console.warn('Aviationstack API failed:', error);
      }

      // Fallback to local city cache
      this.showFallbackResults(query);
    }

    async searchAviationstack(query) {
      const API_KEY = 'f03fa98d3d7917445de7afdec55ddb94';
      const API_URL = 'https://api.aviationstack.com/v1';

      try {
        let response = await fetch(
          `${API_URL}/cities?access_key=${API_KEY}&search=${encodeURIComponent(query)}&limit=10`,
          { signal: this.abortController.signal }
        );

        if (response.ok) {
          const data = await response.json();
          if (data.data && data.data.length > 0) {
            return data.data.map(city => ({
              city: city.city_name,
              country: city.country_name,
              iata: city.iata_code || '',
              timezone: city.timezone || '',
              flag: this.getCountryFlag(city.country_name),
              latitude: city.latitude,
              longitude: city.longitude
            }));
          }
        }

        // Try airports endpoint if cities returns nothing
        response = await fetch(
          `${API_URL}/airports?access_key=${API_KEY}&search=${encodeURIComponent(query)}&limit=10`,
          { signal: this.abortController.signal }
        );

        if (response.ok) {
          const data = await response.json();
          if (data.data && data.data.length > 0) {
            return data.data.map(airport => ({
              city: airport.city_name,
              airport_name: airport.airport_name,
              country: airport.country_name,
              iata: airport.iata_code || '',
              timezone: airport.timezone || '',
              flag: this.getCountryFlag(airport.country_name),
              latitude: airport.latitude,
              longitude: airport.longitude
            }));
          }
        }

        return [];
      } catch (error) {
        throw error;
      }
    }

    showFallbackResults(query) {
      const results = Object.values(CONFIG.fallbackCities).filter(city =>
        city.city.toLowerCase().includes(query.toLowerCase()) ||
        city.iata.toLowerCase().includes(query.toLowerCase())
      );

      if (results.length === 0) {
        this.showEmpty();
      } else {
        this.displayResults(results, query);
      }
    }

    displayResults(results, query) {
      this.hideSkeleton();
      this.hideError();

      if (results.length === 0) {
        this.showEmpty();
        return;
      }

      this.dropdownList.innerHTML = results
        .slice(0, CONFIG.maxResults)
        .map((dest, idx) => this.createItemHTML(dest, idx))
        .join('');

      this.dropdownList.style.display = 'block';
      this.attachItemListeners();
    }

    createItemHTML(dest, idx) {
      const flag = dest.flag || '✈️';
      const city = dest.city || dest.airport_name || 'Unknown';
      const country = dest.country || '';
      const iata = dest.iata || '';

      return `
        <div
          class="travel-planner__search-item"
          role="option"
          aria-selected="false"
          data-destination='${JSON.stringify(dest)}'
          tabindex="${idx === 0 ? '0' : '-1'}">
          <span class="travel-planner__search-flag">${flag}</span>
          <div class="travel-planner__search-text">
            <div class="travel-planner__search-city">
              ${city}
              <span class="travel-planner__search-code">${iata}</span>
            </div>
            <div class="travel-planner__search-country">${country}</div>
          </div>
        </div>
      `;
    }

    attachItemListeners() {
      this.dropdownList.querySelectorAll('.travel-planner__search-item').forEach(item => {
        item.addEventListener('click', () => {
          const destination = JSON.parse(item.dataset.destination);
          this.selectDestination(destination);
        });

        item.addEventListener('mouseenter', () => {
          this.highlightedIndex = Array.from(this.dropdownList.children).indexOf(item);
          this.updateHighlight();
        });
      });
    }

    selectDestination(destination) {
      this.selectedDestination = destination;
      this.searchInput.value = destination.city || destination.airport_name || '';
      this.displayBadge(destination);
      this.closeDropdown();
      this.saveSelection();

      // Trigger custom event for form
      window.dispatchEvent(new CustomEvent('destinationSelected', { detail: destination }));
    }

    displayBadge(destination) {
      const flag = destination.flag || '✈️';
      const city = destination.city || destination.airport_name || 'Unknown';
      const code = destination.iata || '';

      document.getElementById('tpDestinationName').textContent = city;
      document.getElementById('tpDestinationCode').textContent = code;
      document.getElementById('tpDestinationFlag').textContent = flag;
      this.selectedBadge.style.display = 'block';
    }

    clearSelection() {
      this.selectedDestination = null;
      this.searchInput.value = '';
      this.selectedBadge.style.display = 'none';
      this.closeDropdown();
      localStorage.removeItem('travelPlannerDestination');
      window.dispatchEvent(new CustomEvent('destinationSelected', { detail: null }));
    }

    showSkeleton() {
      this.dropdownList.style.display = 'none';
      this.emptyState.style.display = 'none';
      this.errorState.style.display = 'none';
      this.skeletonLoader.style.display = 'block';
    }

    hideSkeleton() {
      this.skeletonLoader.style.display = 'none';
    }

    showEmpty() {
      this.dropdownList.style.display = 'none';
      this.skeletonLoader.style.display = 'none';
      this.errorState.style.display = 'none';
      this.emptyState.style.display = 'block';
    }

    showError(message) {
      this.dropdownList.style.display = 'none';
      this.skeletonLoader.style.display = 'none';
      this.emptyState.style.display = 'none';
      document.getElementById('tpSearchErrorText').textContent = message;
      this.errorState.style.display = 'block';
    }

    hideError() {
      this.errorState.style.display = 'none';
    }

    retry() {
      this.search(this.currentQuery);
    }

    closeDropdown() {
      this.dropdownList.style.display = 'none';
      this.skeletonLoader.style.display = 'none';
      this.emptyState.style.display = 'none';
      this.errorState.style.display = 'none';
      this.searchInput.setAttribute('aria-expanded', 'false');
      this.highlightedIndex = -1;
    }

    isCacheExpired(timestamp) {
      return Date.now() - timestamp > CONFIG.cacheExpiryMs;
    }

    saveSelection() {
      if (this.selectedDestination) {
        localStorage.setItem('travelPlannerDestination', JSON.stringify(this.selectedDestination));
      }
    }

    loadCacheFromStorage() {
      const stored = localStorage.getItem('travelPlannerDestination');
      if (stored) {
        try {
          this.selectedDestination = JSON.parse(stored);
          this.displayBadge(this.selectedDestination);
        } catch (e) {
          console.warn('Failed to load stored destination:', e);
        }
      }
    }

    getSelectedDestination() {
      return this.selectedDestination;
    }
  }

  window.DestinationSearch = new DestinationSearch();
})();
