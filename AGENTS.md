# Coding Rules

- Khi deploy tính năng mới, QA chỉ bắt tính năng đó, không bắt toàn site dẫn đến failed không cần thiết.
- Mỗi bài viết phải có tối thiểu 2 ảnh: 1 ảnh hero (cover) + ít nhất 1 ảnh minh họa nội dung. Bài kỹ thuật cũng không ngoại lệ.
- Content Direction workflow: auto mỗi 24 giờ (cron 22:47 UTC ≈ 05:47 Asia/Ho_Chi_Minh, mốc từ 2026-07-10). Không chạy sau mỗi post/deploy. Manual `workflow_dispatch` luôn được phép và không ảnh hưởng chu kỳ auto.
- Sau khi viết xong một bài blog (trên bất kỳ branch nào), phải chạy ngay `source .env && python3 scripts/select_images.py --post content/posts/<slug>.md --fix` để chọn ảnh từ Pexels/Pixabay API. Sau đó chạy script process/xử lý WebP, force-add file ảnh, cập nhật manifest. Không được bỏ qua bước này.
- **BẮT BUỘC:** Mọi bài viết trong `content/posts/` phải có trường `commit = "xxxxxxx"` trong front matter. Không có ngoại lệ. Kiểm tra trước khi push bằng lệnh: `grep -l "^commit" content/posts/*.md | wc -l` (phải == tổng số file .md). Nếu thiếu, chạy `python3 scripts/add_commit_id.py` rồi kiểm tra lại. Chạy script này ngay sau mỗi lần merge bài mới vào `main` — trước khi push commit tiếp theo. Format: `commit = "<7-ký-tự-đầu-của-hash>"` (TOML syntax, dùng dấu `=`, không dùng dấu `:`).

- Ảnh bài viết: chỉ lấy từ **Pexels** và **Pixabay** API (keys trong `.env`: `PEXELS_API_KEY`, `PIXABAY_API_KEY`). Không tự vẽ / self-generate placeholder. Không fake creator. Attribution bắt buộc khi provider trả photographer.
- QA blog trước deploy phải chạy kiểm tra ảnh cho bài trong scope thay đổi. Nếu bài thiếu/bể `image` hoặc `thumbnail`, phải gọi Pexels/Pixabay API để chọn ảnh thật, xử lý WebP + watermark attribution, cập nhật front matter/manifest, rồi mới accept deploy. Nếu không có key hoặc không tìm được ảnh hợp lệ thì fail deploy, không dùng fallback/self-generated.
- Source of truth trước deploy là `python scripts/rule.py --fix`: front matter bài viết phải là TOML (`+++`), date lưu canonical ISO `+07:00` cho Hugo, display date dùng `dd-mm-yyyy hh:mm:ss GMT +7`, mọi future date là fake và phải sửa về thời gian thật Asia/Ho_Chi_Minh trước deploy.

- Trước khi push code lên production (`main`), phải đọc lại toàn bộ quy tắc trong AGENTS.md và các quy tắc blog khác để đảm bảo tuân thủ đầy đủ.
- Bài viết không có ảnh (thiếu `image` hoặc `thumbnail` trong front matter) thì không được phép push lên `main` và deploy production.
- **WebP images now tracked in git** (as of 2026-07-11). File `.webp` trong `static/images/posts/` được commit thường thường. GitHub Actions checkout sẽ có WebP files → Hugo build render ảnh → Deploy thành công. Không cần force-add, không cần tricks. **Root cause fix:** `.gitignore` ignore WebP vì chúng generated (không source), nhưng GitHub Pages deploy cần WebP files available → Solution: commit WebP to git, regenerate WebP locally + in CI/CD khi cần optimize.
- **Không dùng YAML syntax (`key: value`) trong TOML front matter (`+++`).** Hugo dùng TOML parser. Sai syntax (ví dụ `commit: abc` thay vì `commit = "abc"`) sẽ làm parser fail tại dòng đó, khiến `rule.py --fix` không đọc được các field phía sau (categories, date, image...), dẫn đến deploy crash và date bị ghi đè thành thời gian chạy `rule.py`. Luôn dùng `key = "value"` (TOML) trong front matter.
- **Content Depth:** Mọi bài viết (cả VN và EN) phải có tối thiểu **3000 từ**. Sử dụng thước đo `wc -w` trên nội dung markdown (loại bỏ front matter) để kiểm tra. Internal links và external links là **optional** — không bắt buộc phải thêm vào. Nếu muốn thêm links:
  - External links: trỏ đến nguồn tham khảo uy tín bên ngoài để tăng giá trị SEO.
  - Internal links: **TUYỆT ĐỐI CẤM link placeholder/fake** dạng `/posts/placeholder-*`. Nếu không có bài viết thật cùng chủ đề, bỏ qua internal link — không tạo link ảo. Lý do: link placeholder sinh ra trong quá trình gen bài (prompt yêu cầu "thêm internal link SEO"), agent tạo link tới bài chưa tồn tại. Cách khắc phục: agent chỉ được tạo internal link khi có slug bài viết thật trong `content/posts/`. Nếu chưa có bài thật, không thêm internal link nào hết.
- **TUYỆT ĐỐI CẤM `![[IMAGE_API_QUERY:...]]` markers trong nội dung bài viết.** Không được viết, không được giữ lại, không được coi là placeholder tạm thời. Đây là marker chết — không script nào xử lý, không tự động replace. Nếu marker còn sót trong file `.md` khi push, coi như lỗi nghiêm trọng, phải fix ngay. Ảnh minh họa inline chỉ được chèn bằng Markdown `![](...)` thủ công với URL ảnh thật.

# Deployment Rule (từ 2026-07-10)

- **1 change = 1 branch = 1 deploy.** Mỗi tính năng / thay đổi phải được phát triển trên một nhánh riêng, tách biệt hoàn toàn với các nhánh tính năng khác.
- Không gộp chung nhiều tính năng vào cùng một nhánh deploy. Khi merge, chỉ merge đúng 1 nhánh tính năng duy nhất vào `main`.
- Deploy chỉ kích hoạt khi push commit tính năng lên `main`. Đảm bảo mỗi lần deploy chỉ mang đúng 1 thay đổi, tránh lẫn blog post, ảnh, hay bất kỳ file nào ngoài scope.
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
**Symptom:** Theme renders blank hero, deploy blocked
**Auto-Fix:** `python3 scripts/select_images.py --post content/posts/<slug>.md --fix`
**Prevention:** Never publish post without running image selection

### Failure #4: Wrong Timezone (+05:00, Z, or missing)
**Symptom:** Date sorting fails, posts appear out of order
**Auto-Fix:** `python3 scripts/qa_dates.py --fix-obvious`
**Prevention:** Always use `+07:00` for Vietnam timezone

### Failure #5: Future Date
**Symptom:** Post doesn't appear on homepage (scheduled but broken)
**Auto-Fix:** `python3 scripts/qa_dates.py --fix-obvious` (sets to now)
**Prevention:** Use `date = "2026-07-11T13:45:00+07:00"` (past/current time)

### Failure #6: Content < 3000 words
**Symptom:** Deploy blocks with content-depth check
**Auto-Fix:** Expand content manually (no auto-fix)
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
**Symptom:** Theme can't render hero, deploy fails
**Auto-Fix:** `python3 scripts/select_images.py --post content/posts/<slug>.md --fix`
**Prevention:** Image selection is NOT optional

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
**Prevention:**
- Deploy FIFO only (30s minimum spacing)
- Don't run `select_images.py` in parallel
- Stagger image selections across branches

## Best Practices to Avoid 99% of Failures

1. **Always run the Pre-Deploy Checklist** (10 commands, 2 minutes)
2. **TOML syntax only** - Never use `key: value` in `+++...+++`
3. **3000+ words** - Check before committing
4. **Real images only** - Use Pexels/Pixabay API, never fake
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
