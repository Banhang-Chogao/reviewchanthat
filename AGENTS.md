# Coding Rules

- **TUYỆT ĐỐI KHÔNG tạo thêm Category mới.** Website chỉ có đúng **5 category chuẩn** (canonical), không bao giờ thêm cái thứ 6:
  1. **Review** (`review`)
  2. **Công nghệ** (`cong-nghe`)
  3. **Đời sống** (`doi-song`)
  4. **Tài chính** (`tai-chinh`)
  5. **Du lịch** (`du-lich`)
  - Source of truth: `data/categories.json` (5 items + bảng `aliases` để map biến thể về canonical). **Cấm sửa/append vào `items`.**
  - Nếu một bài không biết xếp vào đâu → **nhét vào category gần nhất đang có sẵn** (mặc định an toàn là **Đời sống** — "Lựa chọn tốt hơn mỗi ngày", đủ rộng cho hầu hết chủ đề đời thường). KHÔNG được đẻ ra category one-off mới.
  - Nếu gặp tên category lạ (one-off) trong bài → thêm entry vào `aliases` trỏ về 1 trong 5 canonical, KHÔNG tạo item mới.

- Khi deploy tính năng mới, QA chỉ bắt tính năng đó, không bắt toàn site dẫn đến failed không cần thiết.
- **LUÔN LUÔN — nhắc lại, LUÔN LUÔN — post bài kèm ảnh.** Đừng bao giờ để người dùng phải hậu kiểm thủ công bài nào thiếu ảnh (rất mệt). Bước chọn + xử lý ảnh là bắt buộc, chạy tự động ngay khi viết xong bài, KHÔNG được đẩy phần kiểm tra ảnh sang cho con người.
- Mỗi bài viết phải có tối thiểu 2 ảnh: 1 ảnh hero (cover) + ít nhất 1 ảnh minh họa nội dung. Bài kỹ thuật cũng không ngoại lệ.
- **Chất lượng bài viết (human-first, KHÔNG có mùi AI):** Bài blog phải có **chiều sâu thật**, độ dài **từ 2000–3000 từ trở lên**. Viết như một con người có trải nghiệm thật (human being), KHÔNG được có cảm giác "AI writing" (câu sáo rỗng, liệt kê máy móc, mở bài/kết bài công thức). Tuân thủ **luật bản quyền**, nội dung **chân thật** (Review Chân Thật), dựa trên trải nghiệm/kiểm chứng thật, không bịa.
- Content Direction workflow: auto mỗi 24 giờ (cron 22:47 UTC ≈ 05:47 Asia/Ho_Chi_Minh, mốc từ 2026-07-10). Không chạy sau mỗi post/deploy. Manual `workflow_dispatch` luôn được phép và không ảnh hưởng chu kỳ auto.
- Sau khi viết xong một bài blog (trên bất kỳ branch nào), phải chạy ngay `source .env && python3 scripts/select_images.py --post content/posts/<slug>.md --fix` để chọn ảnh từ Pexels/Pixabay API. Sau đó chạy script process/xử lý WebP, force-add file ảnh, cập nhật manifest. Không được bỏ qua bước này.
- **CRITICAL: COMMIT ID là MANDATORY cho MỌI bài viết. KHÔNG được bỏ qua dưới bất kỳ hình thức nào.**
  - **Quy tắc:** Mỗi post trong `content/posts/` phải có `commit = "xxxxxxx"` (7-ký-tự SHA). Không có ngoại lệ, không có post nào được phép thiếu commit ID.
  - **Bắt buộc sau mỗi bài mới:** Ngay sau khi viết xong bài → commit → chạy `python3 scripts/add_commit_id.py` trước khi push.
  - **Kiểm tra pre-deploy:** `grep "^commit = \"\"" content/posts/*.md | wc -l` phải = 0 (không post nào có commit trống). Nếu != 0, REJECT push, chạy `add_commit_id.py`, commit lại.
  - **Xử phạt:** Nếu push bài không có commit ID, deploy-doctor sẽ detect + tự động fix, tạo PR → nhân biết lỗi.
  - **Format:** TOML syntax: `commit = "abc123f"` (dấu `=`, có dấu ngoặc). Không bao giờ dùng YAML `commit: abc123f`.

- Ảnh bài viết: chỉ lấy từ **Pexels** và **Pixabay** API (keys trong `.env`: `PEXELS_API_KEY`, `PIXABAY_API_KEY`). Không tự vẽ / self-generate placeholder. Không fake creator. Attribution bắt buộc khi provider trả photographer.
- QA blog trước deploy phải chạy kiểm tra ảnh cho bài trong scope thay đổi. Nếu bài thiếu/bể `image` hoặc `thumbnail`, phải gọi Pexels/Pixabay API để chọn ảnh thật, xử lý WebP + watermark attribution, cập nhật front matter/manifest, rồi mới accept deploy.
- **Chiến lược khi API không trả ảnh — theo đúng thứ tự:**
  1. **Rate limit (429) → ĐỔI SOURCE.** Ta có **2 API** (Pexels + Pixabay). Nếu một provider bị rate limit, tự động chuyển sang provider còn lại; không dừng lại, không fail vội. Chỉ khi **cả hai** đều rate limit thì back off và retry sau (deploy FIFO, cách nhau ≥30s).
  2. **Tìm mãi vẫn không có ảnh hợp lệ → CHẤP NHẬN bài không ảnh (text-first).** KHÔNG bịa/fake/placeholder/self-generated ảnh. Bài không ảnh được publish như một **bài text-first**: load càng nhanh càng tốt, có lợi cho SEO về performance. Đây là kết quả hợp lệ, KHÔNG phải lỗi deploy.
  - Tuyệt đối không dùng fallback ảnh giả để "cho có". Thà không ảnh (text-first) còn hơn ảnh fake.
- Source of truth trước deploy là `python scripts/rule.py --fix`: front matter bài viết phải là TOML (`+++`), date lưu canonical ISO `+07:00` cho Hugo, display date dùng `dd-mm-yyyy hh:mm:ss GMT +7`, mọi future date là fake và phải sửa về thời gian thật Asia/Ho_Chi_Minh trước deploy.

- Trước khi push code lên production (`main`), phải đọc lại toàn bộ quy tắc trong AGENTS.md và các quy tắc blog khác để đảm bảo tuân thủ đầy đủ.
- Bài viết chỉ được publish khi **đã thực sự cố lấy ảnh qua cả 2 API (Pexels + Pixabay), đổi source khi bị rate limit**. Nếu sau khi đã thử hết mà vẫn không có ảnh hợp lệ → được phép push lên `main` như **bài text-first** (không ảnh, load nhanh, tốt cho SEO performance). Cái BỊ CẤM là push bài có ảnh **fake/placeholder/self-generated** hoặc bỏ qua bước lấy ảnh mà chưa thử hết 2 API.
- **WebP images now tracked in git** (as of 2026-07-11). File `.webp` trong `static/images/posts/` được commit thường thường. GitHub Actions checkout sẽ có WebP files → Hugo build render ảnh → Deploy thành công. Không cần force-add, không cần tricks. **Root cause fix:** `.gitignore` ignore WebP vì chúng generated (không source), nhưng GitHub Pages deploy cần WebP files available → Solution: commit WebP to git, regenerate WebP locally + in CI/CD khi cần optimize.
- **Không dùng YAML syntax (`key: value`) trong TOML front matter (`+++`).** Hugo dùng TOML parser. Sai syntax (ví dụ `commit: abc` thay vì `commit = "abc"`) sẽ làm parser fail tại dòng đó, khiến `rule.py --fix` không đọc được các field phía sau (categories, date, image...), dẫn đến deploy crash và date bị ghi đè thành thời gian chạy `rule.py`. Luôn dùng `key = "value"` (TOML) trong front matter.
- **Content Depth:** Mọi bài viết (cả VN và EN) phải có chiều sâu thật, độ dài **từ 2000–3000 từ trở lên** (tối thiểu tuyệt đối 2000 từ, nhắm mốc 3000 từ cho bài trụ cột). Sử dụng thước đo `wc -w` trên nội dung markdown (loại bỏ front matter) để kiểm tra. Viết giọng human-first, có trải nghiệm thật, không có mùi AI, tuân thủ bản quyền + Review Chân Thật. Internal links và external links là **optional** — không bắt buộc phải thêm vào. Nếu muốn thêm links:
  - External links: trỏ đến nguồn tham khảo uy tín bên ngoài để tăng giá trị SEO.
  - Internal links: **TUYỆT ĐỐI CẤM link placeholder/fake** dạng `/posts/placeholder-*`. Nếu không có bài viết thật cùng chủ đề, bỏ qua internal link — không tạo link ảo. Lý do: link placeholder sinh ra trong quá trình gen bài (prompt yêu cầu "thêm internal link SEO"), agent tạo link tới bài chưa tồn tại. Cách khắc phục: agent chỉ được tạo internal link khi có slug bài viết thật trong `content/posts/`. Nếu chưa có bài thật, không thêm internal link nào hết.
- **Footer macro là NGUỒN DUY NHẤT cho 4 mục cuối bài — cấm hardcode.** Bốn mục sau BẮT BUỘC do macro `layouts/partials/post-footer.html` sinh ra từ front matter, **áp dụng cho MỌI bài dù thuộc Category nào**:
  - **Liên kết nội bộ được sử dụng trong bài viết** ← `[[internal_links]]` (`ref`, `title`)
  - **Liên kết bên ngoài được sử dụng trong bài viết** ← `[[external_links]]` (`url`, `title`)
  - **FAQ - Câu hỏi thường gặp** ← `[[faq]]` (`question`, `answer`)
  - **Bản quyền & Ghi nguồn** ← `[attribution]` (`copyright`, `source_note`)
  - **TUYỆT ĐỐI KHÔNG hardcode** các heading/nội dung này trong thân bài viết (`.md` body). Không viết tay `## FAQ`, `## Liên kết nội bộ`, `## Bản quyền`... trong body. Chỉ điền dữ liệu vào front matter, macro tự render.
  - Nếu lỡ hardcode → **move nội dung hardcode đó vào đúng field front matter tương ứng** rồi xóa khỏi body. Dùng script: `python3 scripts/move_hardcoded_footer_sections.py --fix` (scan-only nếu bỏ `--fix`). Việc dọn nợ hàng loạt phải làm ở PR `qa-debt-fix` riêng, không gộp vào deploy tính năng khác.
- **TUYỆT ĐỐI CẤM `![[IMAGE_API_QUERY:...]]` markers trong nội dung bài viết.** Không được viết, không được giữ lại, không được coi là placeholder tạm thời. Đây là marker chết — không script nào xử lý, không tự động replace. Nếu marker còn sót trong file `.md` khi push, coi như lỗi nghiêm trọng, phải fix ngay. Ảnh minh họa inline chỉ được chèn bằng Markdown `![](...)` thủ công với URL ảnh thật.

# Deployment Rule (từ 2026-07-10)

- **1 change = 1 branch = 1 deploy.** Mỗi tính năng / thay đổi phải được phát triển trên một nhánh riêng, tách biệt hoàn toàn với các nhánh tính năng khác.
- Không gộp chung nhiều tính năng vào cùng một nhánh deploy. Khi merge, chỉ merge đúng 1 nhánh tính năng duy nhất vào `main`.
- Deploy chỉ kích hoạt khi push commit tính năng lên `main`. Đảm bảo mỗi lần deploy chỉ mang đúng 1 thay đổi, tránh lẫn blog post, ảnh, hay bất kỳ file nào ngoài scope.
- **Chỉ đẩy ĐÚNG scope của mình — cấm đẩy code người khác/nhánh khác.** Khi làm việc trên `main` hoặc một nhánh dùng chung bởi nhiều session, bạn CHỈ được quan tâm và commit/push **đúng phần scope của mình**. Lúc đẩy code lên live cũng vậy: chỉ `git add` + push đúng những file thuộc scope bạn đang làm. TUYỆT ĐỐI không tự ý stage/commit/push thay đổi của người khác, của session khác, hay file untracked ngoài scope (ví dụ bài viết dở của nhánh khác). Nếu `git status` có file lạ ngoài scope → để nguyên, không đụng tới. Ưu tiên `git add <đúng-file>` thay vì `git add .` / `git add -A`.
- **Deploy FIFO — xếp hàng chờ, không chạy đồng loạt.** Các deploy phải cách nhau tối thiểu **30 giây**. Không push nhiều commit liên tiếp lên `main` trong cùng một khoảnh khắc. Dùng `git push` kèm kiểm tra GitHub Actions queue trước khi push commit tiếp theo. Tránh rate limit GitHub API, Pixabay/Pexels, và tránh concurrent build chồng chéo.

# Deploy Failure Prevention & Auto-Healing (từ 2026-07-11)

## Pre-Deploy Checklist (Prevent 95% of failures)

**BẮT BUỘC chạy TRƯỚC khi `git push origin main`:**
```bash
# 1. Scan for all deployment issues
python3 scripts/deploy-failure-healer.py --scan

# 2. Auto-fix common issues
python3 scripts/deploy-failure-healer.py --fix-all

# 3. Validate dates (ISO 8601 +07:00)
python3 scripts/qa_dates.py

# 4. Validate frontmatter (TOML, no future dates)
python3 scripts/rule.py --fix

# 5. Check commit hashes on all posts
python3 scripts/add_commit_id.py

# 6. Verify no YAML syntax in TOML frontmatter
grep -n "commit:\|date:\|image:" content/posts/*.md | head -5

# 7. Verify no dead IMAGE_API_QUERY markers
grep -r "!\[\[IMAGE_API_QUERY:" content/posts/

# 8. Verify no placeholder links
grep -r "/posts/placeholder-" content/posts/

# 9. Count posts with commit hashes
echo "Total posts: $(ls content/posts/*.md | wc -l)"
echo "Posts with commit hash: $(grep -l "^commit = " content/posts/*.md | wc -l)"
```

If any check fails → **STOP** push and run deploy-failure-healer.py.

## Common Deployment Failures & Auto-Fixes

### Failure #1: YAML Syntax in TOML Frontmatter
**Symptom:** Hugo parse error on deployment, "commit: abc" instead of commit = "abc"
**Auto-Fix:** `python3 scripts/deploy-failure-healer.py --fix-all`
**Prevention:** ALWAYS use TOML syntax `key = "value"` in `+++...+++` blocks

### Failure #2: Missing Commit Hash
**Symptom:** Post fails QA check, can't track version
**Auto-Fix:** `python3 scripts/add_commit_id.py`
**Prevention:** Run after EVERY merge to main

### Failure #3: Missing Hero Image or Thumbnail
**Symptom:** Theme renders blank hero
**Auto-Fix:** `python3 scripts/select_images.py --post content/posts/<slug>.md --fix` (tự đổi source Pexels↔Pixabay khi rate limit)
**Prevention:** Never publish post without running image selection. Nếu đã thử **cả 2 API** mà vẫn không có ảnh hợp lệ → publish text-first (không ảnh), KHÔNG chèn ảnh fake. Đây không phải lỗi deploy.

### Failure #4: Wrong Timezone (+05:00, Z, or missing)
**Symptom:** Date sorting fails, posts appear out of order
**Auto-Fix:** `python3 scripts/qa_dates.py --fix-obvious`
**Prevention:** Always use `+07:00` for Vietnam timezone

### Failure #5: Future Date
**Symptom:** Post doesn't appear on homepage (scheduled but broken)
**Auto-Fix:** `python3 scripts/qa_dates.py --fix-obvious` (sets to now)
**Prevention:** Use `date = "2026-07-11T13:45:00+07:00"` (past/current time)

### Failure #6: Content < 2000 words
**Symptom:** Deploy blocks with content-depth check (dưới ngưỡng tối thiểu 2000 từ; nhắm 2000–3000+)
**Auto-Fix:** Expand content manually (no auto-fix). Viết sâu, human-first, không nhồi chữ vô nghĩa.
**Prevention:** Check `tail -n +29 content/posts/<slug>.md | wc -w` before commit

### Failure #7: Fake Internal Links (/posts/placeholder-*)
**Symptom:** Links point to non-existent posts, breaks SEO
**Auto-Fix:** `python3 scripts/deploy-failure-healer.py --fix-all`
**Prevention:** Only link to posts that actually exist in content/posts/

### Failure #8: Dead IMAGE_API_QUERY Markers
**Symptom:** `![[IMAGE_API_QUERY:...]]` renders as broken markdown
**Auto-Fix:** `python3 scripts/deploy-failure-healer.py --fix-all`
**Prevention:** NEVER commit posts with IMAGE_API_QUERY markers

### Failure #9: WebP Images Missing on GitHub Pages (FIXED)
**Root Cause:** `.gitignore` ignored `static/images/posts/*.webp` because they're generated files. Local Hugo build had WebP (via process_images.py), but GitHub Actions checkout had no WebP → Deploy failed.

**Solution (as of 2026-07-11):** 
- Removed `static/images/posts/*.webp` from `.gitignore`
- WebP files now committed to git
- GitHub Actions checkout includes WebP
- Hugo build & deploy work without extra CI/CD steps

**Prevention:** Ensure `.gitignore` does NOT block `static/images/posts/*.webp`. If .gitignore needs updating, AGENTS.md + deployment-doctor will catch + fix automatically.

### Failure #10: No image in frontmatter
**Symptom:** Theme can't render hero
**Auto-Fix:** `python3 scripts/select_images.py --post content/posts/<slug>.md --fix` — thử Pexels trước, **rate limit → đổi sang Pixabay** (và ngược lại).
**Prevention:** Image selection is NOT optional — luôn phải CHẠY. Nhưng nếu cả 2 API đều không ra ảnh hợp lệ, bài được phép ship dạng text-first (không ảnh). Không bao giờ fake ảnh để lấp chỗ trống.

## Deploy Conflict & Build Failure Resolution

### Git Merge Conflicts (during branch merges)

**Strategy:** Always use `git checkout --theirs` for:
- `content/posts/` (take incoming branch's post updates)
- `data/images.json` (take incoming image metadata)
- `data/image-selection-report.json` (take incoming report)

**Reason:** These files change frequently; incoming branch is usually newer.

```bash
git checkout --theirs content/posts/ data/ && git add content/posts/ data/
```

### Build Failures During CI/CD

**Step 1:** Check the failing log
```bash
git log --oneline origin/main -10  # Recent commits
git diff origin/main HEAD          # What changed
```

**Step 2:** Identify failure type
- TOML parse error → Run `rule.py --fix`
- Missing images → Run `select_images.py --fix`
- Date issues → Run `qa_dates.py --fix-obvious`
- Commit hash missing → Run `add_commit_id.py`

**Step 3:** Run auto-healer on affected commits
```bash
python3 scripts/deploy-failure-healer.py --fix-all
```

**Step 4:** Create a fix commit
```bash
git add .
git commit -m "fix: resolve deploy failure via auto-healer"
git push origin main
```

### Hugo Build Fails

**Common cause:** TOML parser stops at first syntax error
**Symptoms:** 
- "error parsing front matter"
- "line X: expected =, got :" 
- Fields after error line are ignored

**Quick fix:**
```bash
# Find the line with YAML syntax
grep -n "commit:\|date:\|image:" content/posts/*.md

# Replace with TOML
# commit: abc  →  commit = "abc"
# date: 2026   →  date = "2026-07-11T13:45:00+07:00"
```

### Rate Limit Failures (API calls)

**Symptoms:** "429 Too Many Requests" from Pexels/Pixabay
**Cause:** Multiple deploys pushing image API calls in parallel
**Resolution (thứ tự bắt buộc):**
1. **Rate limit 1 provider → ĐỔI SOURCE ngay** sang provider còn lại (Pexels↔Pixabay). Ta có 2 API, đừng dừng ở provider đầu.
2. Cả 2 provider đều 429 → back off, retry sau (deploy FIFO ≥30s).
3. Thử hết mà vẫn không có ảnh → ship text-first (không ảnh), KHÔNG fake. Không phải lỗi.
**Prevention:**
- Deploy FIFO only (30s minimum spacing)
- Don't run `select_images.py` in parallel
- Stagger image selections across branches

## Best Practices to Avoid 99% of Failures

1. **Always run the Pre-Deploy Checklist** (10 commands, 2 minutes)
2. **TOML syntax only** - Never use `key: value` in `+++...+++`
3. **2000–3000+ words, human-first** - Chiều sâu thật, không mùi AI, tuân thủ bản quyền. Check before committing
4. **Real images only** - Use Pexels/Pixabay API, đổi source khi rate limit; never fake. Không ra ảnh → ship text-first, không placeholder giả
5. **Chỉ 5 category chuẩn** - Không tạo category mới; content lạ → nhét vào category gần nhất (mặc định Đời sống)
5. **Commit hash tracking** - Run add_commit_id.py after every merge
6. **Vietnam timezone** - Always +07:00, never +05:00 or Z
7. **No placeholder links** - Only link to existing posts
8. **No IMAGE_API_QUERY** - Remove all markers before push
9. **Deploy one at a time** - 30s minimum between pushes
10. **Force-add WebP images** - `git add -f static/images/posts/<slug>.webp`

## Deploy Failure SLA

| Failure Type | Detection | Auto-Fix | Time to Recover |
|------|-----------|----------|-----------------|
| YAML syntax error | Pre-deploy | ✅ Yes | < 1 min |
| Missing commit hash | Pre-deploy | ✅ Yes | < 1 min |
| Missing image | Pre-deploy | ✅ Yes | < 2 min |
| Wrong timezone | Pre-deploy | ✅ Yes | < 1 min |
| Future date | Pre-deploy | ✅ Yes | < 1 min |
| Fake links | Pre-deploy | ✅ Yes | < 2 min |
| IMAGE_API_QUERY | Pre-deploy | ✅ Yes | < 1 min |
| Content depth | Pre-deploy | ❌ Manual | N/A |
| WebP tracking | Pre-deploy | ✅ Yes | < 1 min |

**Goal: 0 deploy failures** through automated pre-deploy validation.
