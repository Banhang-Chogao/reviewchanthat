# Part 5: Multi-Language Support (Vietnamese-First)

Enhance image generation for Vietnamese content and support multiple languages.

## Overview

Vietnamese-first approach:
- Vietnamese visual metaphors (hành trình, phát triển, etc.)
- Vietnamese color symbolism (đỏ = may mắn, vàng = quý báu)
- Cultural taboos (4 o'clock clocks, all-white, conflicting symbols)
- Regional audience targeting
- Lunar calendar awareness

## New Scripts

### multilingual_analysis.py

Enhances content analysis with language-specific insights.

**Features:**
- Vietnamese visual metaphors mapping
- Vietnamese color meanings
- Cultural visual taboos
- Audience profiles (du khách, công nghệ, tài chính, sinh viên)
- Regional adaptation notes

**Usage:**
```bash
# Analyze with Vietnamese enhancements
python3 scripts/multilingual_analysis.py --post content/posts/post.md --lang vi

# English analysis
python3 scripts/multilingual_analysis.py --post content/posts/post.md --lang en
```

**Output:**
```json
{
  "vietnamese_visual_metaphors": ["con đường", "bản đồ", "cột mốc"],
  "vietnamese_palette": ["nâu", "cam", "vàng (quý báu)"],
  "vietnamese_audience": "Nhà du lịch, người thích khám phá",
  "regional_notes": {
    "market": "Vietnam",
    "language": "Vietnamese",
    "cultural_notes": [
      "Lunar New Year themes preferred",
      "Buddhist/traditional imagery resonates",
      "Regional cities highly searchable"
    ],
    "visual_taboos": [
      "Avoid 4:00 clocks (unlucky)",
      "Avoid all-white (funeral)",
      "Avoid conflicting symbols"
    ]
  }
}
```

## Vietnamese Visual Metaphors

| Concept | Metaphors |
|---------|-----------|
| Hành trình (Journey) | con đường, bản đồ, cột mốc, gác đèn, chuyến đi |
| Phát triển (Growth) | cây mọc, hoa nở, cây phát triển, nụ cây |
| Công nghệ (Tech) | mạch điện, bánh răng, mạng lưới, nút cộng |
| Thời gian (Time) | đồng hồ, lịch, mùa, mặt trời, mặt trăng |
| Kết nối (Connection) | cầu, mạng, sợi chỉ, bàn tay |
| Thách thức (Challenge) | núi, vách đá, chướng ngại, cầu vượt |
| Kiến thức (Knowledge) | sách, đèn, chìa khóa, cửa |

## Vietnamese Color Symbolism

| Color | Meanings | Usage |
|-------|----------|-------|
| Đỏ | May mắn, phúc lộc, Tết | Lunar New Year, festive posts |
| Vàng | Quý báu, hoàng gia, giàu có | Premium products, luxury travel |
| Xanh lá | Tự nhiên, sự sống, mùa xuân | Nature, eco, growth |
| Xanh dương | Biển, trời, tự do | Travel, beach, exploration |
| Nâu | Mùa thu, cổ kính, yên bình | Autumn, nostalgic, peaceful |

## Vietnamese Audience Profiles

### Du Khách (Travelers)
- Keywords: du lịch, chuyến đi, điểm đến, khám phá
- Tone: travel, casual
- Visuals: landscapes, cultural sites, local food

### Công Nghệ (Tech Enthusiasts)
- Keywords: công nghệ, iphone, phần mềm, ứng dụng
- Tone: technical, analytical
- Visuals: clean, modern, innovation

### Tài Chính (Finance)
- Keywords: ngân hàng, tiền, đầu tư, tài chính
- Tone: formal, technical
- Visuals: professional, secure, trustworthy

### Sinh Viên (Students)
- Keywords: học, trường, giáo dục, kỹ năng
- Tone: casual, travel
- Visuals: practical, educational, relatable

## Vietnamese Visual Taboos

❌ **Avoid:**
- Clock showing 4:00 (unlucky number "tứ" sounds like death "tử")
- All-white design (associated with funerals)
- Clashing communist + South symbols (political sensitivity)
- Too-bright red on white (overwhelming, disrespectful)

✅ **Prefer:**
- Balanced compositions with space (feng shui)
- Warm earth tones (welcoming)
- Traditional patterns (cultural resonance)
- Multi-generational inclusion (family-oriented)

## Integration with Previous Parts

### Part 1: Analysis
Adds:
- `vietnamese_visual_metaphors`
- `vietnamese_audience`
- `regional_notes`

### Part 2: Generation
Uses:
- Enhanced metaphor mapping
- Color associations
- Audience-specific styling

### Part 3: Auditing
Checks:
- Visual taboo compliance
- Cultural appropriateness
- Regional relevance

## Example: Vietnamese Travel Post

```
Original (English):
- Topic: thailand_travel
- Palette: ocean-blue, sand-beige, sky-blue
- Composition: beach, tropical

Enhanced (Vietnamese):
- Topic: thailand_travel
- Vietnamese metaphors: [khám phá, chuyến đi]
- Vietnamese palette: [xanh dương (tự do), vàng (ấm áp)]
- Audience: du khách, người thích khám phá
- Regional notes: Beach tourism resonates; use warm lighting
```

## Future Enhancements

### Phase 6: Multi-Language
- Chinese (Mandarin, Cantonese)
- Japanese
- Thai
- Korean
- German

### Phase 7: Locale-Aware NER
- Vietnamese NER (pyvi, Vietnamese word segmentation)
- Regional entity recognition (Hà Nội → capital city, searchable)
- Local brand detection

### Phase 8: Accessibility
- WCAG compliance checking
- Alt text generation
- Color blindness simulation
- RTL language support (if needed for Arabic/Hebrew)

## Files

- `scripts/multilingual_analysis.py` — Multi-language enhancement (250 lines)
- `docs/MULTILINGUAL_PART5.md` — This file

Depends on:
- All prior parts (1-4)

## Architecture

```
Content Analysis (Part 1)
    ↓
Language-Specific Enhancement (Part 5)
    ↓
Prompt Builder (Part 2)
    ↓
Image Generation (Part 2)
    ↓
Audit with Cultural Checks (Part 3)
    ↓
Remediate if Needed (Part 4)
    ↓
Publish with Metadata
```

---

**Part 5 Complete!** All 5 phases implemented:
1. ✅ Content understanding layer
2. ✅ Self-hosted image generation
3. ✅ Image relevance auditing
4. ✅ Automatic remediation
5. ✅ Multi-language support

Full pipeline ready for production deployment.
