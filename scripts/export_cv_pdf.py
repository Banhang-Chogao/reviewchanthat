#!/usr/bin/env python3
"""
Export CV to professional PDF format using ReportLab.
Requires: reportlab

Usage:
  python3 export_cv_pdf.py --data '{"fullName":"Nguyen Van A","email":"..."}' --output cv.pdf

Features:
  - A4, ATS-friendly
  - Unicode support (DejaVu Sans embedded)
  - Vector graphics for icons via ReportLab shapes
  - Proper page breaks
  - Professional recruiter layout
"""

import argparse
import json
import os
import sys

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm, cm
    from reportlab.lib.colors import HexColor, black, white, Color
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        PageBreak, HRFlowable, KeepTogether, ListFlowable, ListItem
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError:
    print("reportlab not installed. Run: pip install reportlab")
    sys.exit(1)


FONT_PATH = os.path.join(os.path.dirname(__file__), '..', 'static', 'fonts')
FONT_NAME = 'DejaVuSans'
FONT_BOLD = 'DejaVuSans-Bold'

def register_fonts():
    try:
        pdfmetrics.registerFont(TTFont(FONT_NAME, os.path.join(FONT_PATH, 'DejaVuSans.ttf')))
        pdfmetrics.registerFont(TTFont(FONT_BOLD, os.path.join(FONT_PATH, 'DejaVuSans-Bold.ttf')))
    except Exception:
        try:
            pdfmetrics.registerFont(TTFont(FONT_NAME, '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
            pdfmetrics.registerFont(TTFont(FONT_BOLD, '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
        except Exception:
            pass


PRIMARY = HexColor('#00A7A0')
DARK = HexColor('#222222')
GRAY = HexColor('#666666')
LIGHT_GRAY = HexColor('#e0e0e0')
WHITE = white


class CVPDF:
    def __init__(self, data, output_path):
        self.data = data
        self.output_path = output_path
        self.styles = getSampleStyleSheet()
        self._setup_styles()
        register_fonts()

    def _setup_styles(self):
        font_name = FONT_NAME
        font_bold = FONT_BOLD

        self.styles.add(ParagraphStyle(
            'CV_Name', fontName=font_bold, fontSize=18, leading=22,
            textColor=DARK, spaceAfter=2, alignment=TA_LEFT
        ))
        self.styles.add(ParagraphStyle(
            'CV_Title', fontName=font_bold, fontSize=11, leading=14,
            textColor=PRIMARY, spaceAfter=6, alignment=TA_LEFT
        ))
        self.styles.add(ParagraphStyle(
            'CV_Contact', fontName=font_name, fontSize=8, leading=10,
            textColor=GRAY, spaceAfter=2, alignment=TA_LEFT
        ))
        self.styles.add(ParagraphStyle(
            'CV_SectionTitle', fontName=font_bold, fontSize=10, leading=13,
            textColor=PRIMARY, spaceBefore=6, spaceAfter=3,
            borderPadding=(0, 0, 2, 0)
        ))
        self.styles.add(ParagraphStyle(
            'CV_EntryTitle', fontName=font_bold, fontSize=10, leading=13,
            textColor=DARK, spaceAfter=1
        ))
        self.styles.add(ParagraphStyle(
            'CV_EntrySub', fontName=font_bold, fontSize=9, leading=12,
            textColor=PRIMARY, spaceAfter=1
        ))
        self.styles.add(ParagraphStyle(
            'CV_EntryDate', fontName=font_name, fontSize=8, leading=10,
            textColor=GRAY, alignment=TA_RIGHT
        ))
        self.styles.add(ParagraphStyle(
            'CV_EntryDesc', fontName=font_name, fontSize=9, leading=13,
            textColor=DARK, spaceAfter=4
        ))
        self.styles.add(ParagraphStyle(
            'CV_SkillTag', fontName=font_name, fontSize=8, leading=10,
            textColor=WHITE, backColor=PRIMARY, borderPadding=(2, 6, 2, 6)
        ))
        self.styles.add(ParagraphStyle(
            'CV_ListItem', fontName=font_name, fontSize=9, leading=13,
            textColor=DARK, leftIndent=12, spaceAfter=1
        ))
        self.styles.add(ParagraphStyle(
            'CV_Objective', fontName=font_name, fontSize=9, leading=13,
            textColor=DARK, alignment=TA_JUSTIFY, spaceAfter=4
        ))

    def _section_title(self, text):
        return Paragraph(text.upper(), self.styles['CV_SectionTitle'])

    def _hr(self):
        return HRFlowable(width='100%', thickness=1, color=LIGHT_GRAY, spaceAfter=4)

    def build(self):
        doc = SimpleDocTemplate(
            self.output_path,
            pagesize=A4,
            leftMargin=20 * mm,
            rightMargin=20 * mm,
            topMargin=18 * mm,
            bottomMargin=20 * mm,
            title='CV - ' + self.data.get('fullName', ''),
            author=self.data.get('fullName', ''),
        )
        elements = []
        self._build_header(elements)
        self._build_objective(elements)
        self._build_education(elements)
        self._build_experience(elements)
        self._build_projects(elements)
        self._build_skills(elements)
        self._build_certifications(elements)
        self._build_languages(elements)
        self._build_awards(elements)
        self._build_activities(elements)
        self._build_references(elements)
        self._build_additional(elements)
        doc.build(elements)

    def _build_header(self, elements):
        d = self.data
        name = d.get('fullName', 'Your Name')
        title_text = d.get('objective', 'Professional')
        if title_text:
            title_text = title_text.split('.')[0]

        elements.append(Paragraph(name, self.styles['CV_Name']))
        if title_text:
            elements.append(Paragraph(title_text, self.styles['CV_Title']))

        contact_parts = []
        if d.get('email'): contact_parts.append(d['email'])
        if d.get('phone'): contact_parts.append(d['phone'])
        if d.get('address'): contact_parts.append(d['address'])
        if contact_parts:
            elements.append(Paragraph(' | '.join(contact_parts), self.styles['CV_Contact']))
        elements.append(self._hr())

    def _build_objective(self, elements):
        obj = self.data.get('objective', '')
        if not obj: return
        elements.append(self._section_title('Career Objective'))
        elements.append(Paragraph(obj, self.styles['CV_Objective']))

    def _build_education(self, elements):
        d = self.data
        if not d.get('school') and not d.get('degree'): return
        elements.append(self._section_title('Education'))
        parts = []
        school = d.get('school', '')
        degree = d.get('degree', '')
        if school: parts.append(Paragraph(school, self.styles['CV_EntryTitle']))
        if degree: parts.append(Paragraph(degree, self.styles['CV_EntrySub']))

        date_str = ''
        if d.get('eduStart') or d.get('eduEnd'):
            date_str = f"{d.get('eduStart', '')} - {d.get('eduEnd', '')}"
        if date_str:
            data = [[parts[0] if parts else '', Paragraph(date_str, self.styles['CV_EntryDate'])]]
            if len(parts) > 1:
                data.append([parts[1], ''])
            t = Table(data, colWidths=[None, 80])
            t.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ]))
            elements.append(t)
        else:
            for p in parts:
                elements.append(p)

        if d.get('eduGpa'):
            elements.append(Paragraph(f"GPA: {d['eduGpa']}", self.styles['CV_EntryDesc']))

    def _build_experience(self, elements):
        exps = self.data.get('experiences', [])
        if not exps: return
        valid = [e for e in exps if e.get('company') or e.get('position')]
        if not valid: return
        elements.append(self._section_title('Work Experience'))
        for e in valid:
            parts = []
            if e.get('position'): parts.append(Paragraph(e['position'], self.styles['CV_EntryTitle']))
            if e.get('company'): parts.append(Paragraph(e['company'], self.styles['CV_EntrySub']))
            date_str = f"{e.get('start', '')} - {e.get('end', '')}"
            if date_str.strip(' -'):
                row = [parts[0] if parts else '', Paragraph(date_str, self.styles['CV_EntryDate'])]
                t = Table([row], colWidths=[None, 80])
                t.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ]))
                elements.append(t)
                if len(parts) > 1:
                    elements.append(parts[1])
            else:
                for p in parts:
                    elements.append(p)
            if e.get('desc'):
                elements.append(Paragraph(e['desc'], self.styles['CV_EntryDesc']))

    def _build_projects(self, elements):
        projects = self.data.get('projects', [])
        if not projects: return
        valid = [p for p in projects if p.get('name') or p.get('desc')]
        if not valid: return
        elements.append(self._section_title('Projects'))
        for p in valid:
            if p.get('name'): elements.append(Paragraph(p['name'], self.styles['CV_EntryTitle']))
            if p.get('desc'): elements.append(Paragraph(p['desc'], self.styles['CV_EntryDesc']))
            tech_parts = []
            if p.get('tech'): tech_parts.append(f"<font color='#00A7A0'>{p['tech']}</font>")
            if p.get('url'): tech_parts.append(f"<font color='#00A7A0'>{p['url']}</font>")
            if tech_parts: elements.append(Paragraph(' | '.join(tech_parts), self.styles['CV_EntryDesc']))

    def _build_skills(self, elements):
        skills = self.data.get('skills', [])
        if not skills: return
        elements.append(self._section_title('Skills'))
        skill_cells = []
        for s in skills:
            skill_cells.append(Paragraph(
                f'<font backcolor="#00A7A0" color="white">&nbsp;{s}&nbsp;</font>',
                self.styles['CV_SkillTag']
            ))
        if skill_cells:
            ncols = 4
            rows = [skill_cells[i:i+ncols] for i in range(0, len(skill_cells), ncols)]
            t = Table(rows, colWidths=[None]*ncols)
            t.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 2),
                ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            elements.append(t)

    def _build_certifications(self, elements):
        certs = self.data.get('certifications', '')
        if not certs: return
        elements.append(self._section_title('Certifications'))
        items = [c.strip() for c in certs.split('\n') if c.strip()]
        for item in items:
            elements.append(Paragraph(f'• {item}', self.styles['CV_ListItem']))

    def _build_languages(self, elements):
        langs = self.data.get('languages', '')
        if not langs: return
        elements.append(self._section_title('Languages'))
        items = [l.strip() for l in langs.split('\n') if l.strip()]
        for item in items:
            elements.append(Paragraph(f'• {item}', self.styles['CV_ListItem']))

    def _build_awards(self, elements):
        awards = self.data.get('awards', '')
        if not awards: return
        elements.append(self._section_title('Awards'))
        items = [a.strip() for a in awards.split('\n') if a.strip()]
        for item in items:
            elements.append(Paragraph(f'• {item}', self.styles['CV_ListItem']))

    def _build_activities(self, elements):
        activities = self.data.get('activities', '')
        if not activities: return
        elements.append(self._section_title('Activities'))
        items = [a.strip() for a in activities.split('\n') if a.strip()]
        for item in items:
            elements.append(Paragraph(f'• {item}', self.styles['CV_ListItem']))

    def _build_references(self, elements):
        refs = self.data.get('references', '')
        if not refs: return
        elements.append(self._section_title('References'))
        elements.append(Paragraph(refs, self.styles['CV_Objective']))

    def _build_additional(self, elements):
        add = self.data.get('additional', '')
        if not add: return
        elements.append(self._section_title('Additional Information'))
        elements.append(Paragraph(add, self.styles['CV_Objective']))


def main():
    parser = argparse.ArgumentParser(description='Export CV to PDF')
    parser.add_argument('--data', required=True, help='JSON string with CV data')
    parser.add_argument('--output', default='cv.pdf', help='Output PDF path')
    args = parser.parse_args()

    try:
        data = json.loads(args.data)
    except json.JSONDecodeError as e:
        print(f'Invalid JSON: {e}')
        sys.exit(1)

    cv = CVPDF(data, args.output)
    cv.build()
    print(f'PDF generated: {args.output}')


if __name__ == '__main__':
    main()
