#!/usr/bin/env python3
"""
Export travel itinerary to PDF format suitable for visa applications.
Requires: fpdf2

Usage:
  python3 export_travel_itinerary_pdf.py --trip '{"destination":"ICN","departure":"2026-10-15","...}'

Format:
  A4 page, professional layout with headers/footers, suitable for embassy submission.
"""

import argparse
import json
import sys
from datetime import datetime

try:
    from fpdf import FPDF
except ImportError:
    print("fpdf2 not installed. Run: pip install fpdf2")
    sys.exit(1)


class TravelItineraryPDF(FPDF):
    """Custom PDF class for travel itineraries."""

    def __init__(self, trip_data):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.trip_data = trip_data
        self.set_auto_page_break(auto=True, margin=15)
        self.set_font('Helvetica', size=11)

    def add_header(self):
        """Add header with trip info."""
        self.set_y(10)
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 10, 'Travel Itinerary', ln=True, align='C')

        self.set_font('Helvetica', size=9)
        self.set_text_color(100, 100, 100)
        today = datetime.now().strftime('%Y-%m-%d')
        self.cell(0, 5, f'Generated: {today}', ln=True, align='C')
        self.ln(5)

    def add_trip_summary(self):
        """Add trip summary section."""
        trip = self.trip_data
        itinerary = trip.get('itinerary', {})

        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 8, 'Trip Summary', ln=True)

        self.set_font('Helvetica', size=10)
        summary_data = [
            ('Destination', trip.get('destination', 'N/A')),
            ('Departure Date', trip.get('departure', 'N/A')),
            ('Return Date', trip.get('returnDate', 'N/A')),
            ('Duration', f"{trip.get('days', 0)} days"),
            ('Travelers', f"{trip.get('adults', 1)} adult(s), {trip.get('children', 0)} child(ren)"),
            ('Budget Level', trip.get('budget', 'N/A')),
            ('Weather', itinerary.get('weather', 'N/A')),
            ('Hotel Area', itinerary.get('hotelArea', 'N/A')),
            ('Estimated Budget', itinerary.get('estimatedBudget', 'N/A')),
        ]

        for label, value in summary_data:
            self.set_font('Helvetica', 'B', 9)
            self.cell(50, 6, f'{label}:', border=0)
            self.set_font('Helvetica', size=9)
            self.cell(0, 6, str(value), ln=True)

        self.ln(3)

    def add_daily_itinerary(self):
        """Add daily itinerary section."""
        itinerary = self.trip_data.get('itinerary', {})
        daily = itinerary.get('dailyItinerary', [])

        if not daily:
            return

        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 8, 'Daily Itinerary', ln=True)

        for idx, day in enumerate(daily):
            if self.get_y() > 250:
                self.add_page()

            self.set_font('Helvetica', 'B', 10)
            self.cell(0, 6, f"Day {idx + 1}", ln=True)

            self.set_font('Helvetica', size=9)
            activities = [
                ('Morning', day.get('morning', 'N/A')),
                ('Lunch', day.get('lunch', 'N/A')),
                ('Afternoon', day.get('afternoon', 'N/A')),
                ('Dinner', day.get('dinner', 'N/A')),
            ]

            for time, activity in activities:
                self.set_font('Helvetica', 'B', 8)
                self.cell(25, 5, f'  {time}:', border=0)
                self.set_font('Helvetica', size=8)
                self.multi_cell(0, 5, str(activity))

            if day.get('notes'):
                self.set_font('Helvetica', 'I', 8)
                self.multi_cell(0, 4, f"  Note: {day.get('notes')}")

            self.ln(2)

    def add_practical_info(self):
        """Add practical information."""
        itinerary = self.trip_data.get('itinerary', {})

        if self.get_y() > 250:
            self.add_page()

        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 8, 'Practical Information', ln=True)

        sections = [
            ('Transportation', itinerary.get('transportation', 'N/A')),
            ('Hotel Area', itinerary.get('hotelArea', 'N/A')),
            ('Weather Notes', itinerary.get('weatherNotes', 'N/A')),
            ('Local Tips', itinerary.get('localTips', 'N/A')),
            ('Emergency Numbers', itinerary.get('emergencyNumbers', 'N/A')),
            ('Airport Notes', itinerary.get('airportNotes', 'N/A')),
        ]

        self.set_font('Helvetica', size=9)
        for title, content in sections:
            if content and content != 'N/A':
                self.set_font('Helvetica', 'B', 9)
                self.cell(0, 5, title, ln=True)
                self.set_font('Helvetica', size=8)
                self.multi_cell(0, 4, str(content))
                self.ln(2)

    def add_packing_list(self):
        """Add packing list."""
        itinerary = self.trip_data.get('itinerary', {})
        packing = itinerary.get('packingList', [])

        if not packing:
            return

        if self.get_y() > 250:
            self.add_page()

        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 8, 'Packing List', ln=True)

        self.set_font('Helvetica', size=9)
        for i in range(0, len(packing), 2):
            item1 = packing[i] if i < len(packing) else ''
            item2 = packing[i + 1] if i + 1 < len(packing) else ''

            x = self.get_x()
            self.cell(100, 5, f'☐ {item1}', border=0)
            self.cell(0, 5, f'☐ {item2}', ln=True)

        self.ln(3)

    def add_visa_itinerary(self):
        """Add visa application itinerary table."""
        itinerary = self.trip_data.get('itinerary', {})
        visa = itinerary.get('visaItinerary', [])

        if not visa:
            return

        if self.get_y() > 220:
            self.add_page()

        self.set_font('Helvetica', 'B', 12)
        self.cell(0, 8, 'Visa Application Itinerary', ln=True)

        # Table header
        self.set_font('Helvetica', 'B', 8)
        self.set_fill_color(200, 200, 200)
        self.cell(35, 6, 'Date', border=1, fill=True)
        self.cell(20, 6, 'Day', border=1, fill=True)
        self.cell(85, 6, 'Activity', border=1, fill=True)
        self.cell(40, 6, 'Accommodation', border=1, fill=True, ln=True)

        # Table rows
        self.set_font('Helvetica', size=7)
        for entry in visa:
            self.cell(35, 5, entry.get('date', ''), border=1)
            self.cell(20, 5, entry.get('day', ''), border=1)
            self.cell(85, 5, entry.get('activity', '')[:60], border=1)
            self.cell(40, 5, entry.get('accommodation', ''), border=1, ln=True)

        self.ln(3)

    def add_footer(self):
        """Add footer with page numbers."""
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

    def generate(self):
        """Generate complete PDF."""
        self.add_page()
        self.add_header()
        self.add_trip_summary()
        self.add_daily_itinerary()
        self.add_practical_info()
        self.add_packing_list()
        self.add_visa_itinerary()
        return self.output()


def main():
    parser = argparse.ArgumentParser(description='Export travel itinerary to PDF')
    parser.add_argument('--trip', required=True, help='Trip data as JSON string')
    parser.add_argument('--output', default=None, help='Output file path (optional)')
    args = parser.parse_args()

    try:
        trip_data = json.loads(args.trip)
    except json.JSONDecodeError as e:
        print(f'Invalid JSON: {e}')
        sys.exit(1)

    pdf = TravelItineraryPDF(trip_data)
    pdf_data = pdf.generate()

    if args.output:
        with open(args.output, 'wb') as f:
            f.write(pdf_data)
        print(f'PDF saved to {args.output}')
    else:
        sys.stdout.buffer.write(pdf_data)


if __name__ == '__main__':
    main()
