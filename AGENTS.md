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
  - **Bắt buộc sau mỗi bài mới (SCOPE ONLY):** Ngay sau khi viết xong bài → commit → chạy `python3 scripts/add_commit_id.py --post content/posts/<slug>.md` (lặp `--post` nếu nhiều slug) **trước khi push**. **CẤM** chạy không có `--post` (full-tree ~400 post, rất chậm, đụng file ngoài scope).
  - **Kiểm tra pre-deploy (theo scope):** `grep '^commit = ""' content/posts/<slug>.md` trên từng slug trong diff — không `grep content/posts/*.md` toàn repo trừ khi debt-fix.
  - **Xử phạt:** Nếu push bài không có commit ID, deploy-doctor sẽ detect + tự động fix, tạo PR → nhân biết lỗi.
  - **Format:** TOML syntax: `commit = "abc123f"` (dấu `=`, có dấu ngoặc). Không bao giờ dùng YAML `commit: abc123f`.

- Ảnh bài viết: chỉ lấy từ **Pexels** và **Pixabay** API (keys trong `.env`: `PEXELS_API_KEY`, `PIXABAY_API_KEY`). Không tự vẽ / self-generate placeholder. Không fake creator. Attribution bắt buộc khi provider trả photographer.
- QA blog trước deploy phải chạy kiểm tra ảnh cho bài trong scope thay đổi. Nếu bài thiếu/bể `image` hoặc `thumbnail`, phải gọi Pexels/Pixabay API để chọn ảnh thật, xử lý WebP + watermark attribution, cập nhật front matter/manifest, rồi mới accept deploy.
- **Chiến lược khi API không trả ảnh — theo đúng thứ tự:**
  1. **Rate limit (429) → ĐỔI SOURCE.** Ta có **2 API** (Pexels + Pixabay). Nếu một provider bị rate limit, tự động chuyển sang provider còn lại; không dừng lại, không fail vội. Chỉ khi **cả hai** đều rate limit thì back off và retry sau (deploy FIFO, cách nhau ≥30s).
  2. **Tìm mãi vẫn không có ảnh hợp lệ → CHẤP NHẬN bài không ảnh (text-first).** KHÔNG bịa/fake/placeholder/self-generated ảnh. Bài không ảnh được publish như một **bài text-first**: load càng nhanh càng tốt, có lợi cho SEO về performance. Đây là kết quả hợp lệ, KHÔNG phải lỗi deploy.
  - Tuyệt đối không dùng fallback ảnh giả để "cho có". Thà không ảnh (text-first) còn hơn ảnh fake.
- Source of truth trước deploy (theo scope): `python3 scripts/rule.py --fix --post content/posts/<slug>.md` — front matter bài viết phải là TOML (`+++`), date lưu canonical ISO `+07:00` cho Hugo, display date dùng `dd-mm-yyyy hh:mm:ss GMT +7`, mọi future date là fake và phải sửa về thời gian thật Asia/Ho_Chi_Minh trước deploy. **Không** chạy `rule.py --fix` full-tree khi chỉ sửa vài bài.

- Trước khi push code lên production (`main`), phải đọc lại toàn bộ quy tắc trong AGENTS.md và các quy tắc blog khác để đảm bảo tuân thủ đầy đủ.
- Bài viết chỉ được publish khi **đã thực sự cố lấy ảnh qua cả 2 API (Pexels + Pixabay), đổi source khi bị rate limit**. Nếu sau khi đã thử hết mà vẫn không có ảnh hợp lệ → được phép push lên `main` như **bài text-first** (không ảnh, load nhanh, tốt cho SEO performance). Cái BỊ CẤM là push bài có ảnh **fake/placeholder/self-generated** hoặc bỏ qua bước lấy ảnh mà chưa thử hết 2 API.
- **WebP images now tracked in git** (as of 2026-07-11). File `.webp` trong `static/images/posts/` được commit thường thường. GitHub Actions checkout sẽ có WebP files → Hugo build render ảnh → Deploy thành công. Không cần force-add, không cần tricks. **Root cause fix:** `.gitignore` ignore WebP vì chúng generated (không source), nhưng GitHub Pages deploy cần WebP files available → Solution: commit WebP to git, regenerate WebP locally + in CI/CD khi cần optimize.
- **Không dùng YAML syntax (`key: value`) trong TOML front matter (`+++`).** Hugo dùng TOML parser. Sai syntax (ví dụ `commit: abc` thay vì `commit = "abc"`) sẽ làm parser fail tại dòng đó, khiến `rule.py --fix` không đọc được các field phía sau (categories, date, image...), dẫn đến deploy crash và date bị ghi đè thành thời gian chạy `rule.py`. Luôn dùng `key = "value"` (TOML) trong front matter.
- **`:blog` là lệnh AUTONOMOUS — KHÔNG hỏi user bất cứ gì.** Khi user gõ `:blog`, AI phải tự quyết định mọi thứ:
- **`:nn` là lệnh AUTONOMOUS — lấy source từ URL, viết lại bài blog hoàn chỉnh, deploy lên live, KHÔNG hỏi user bất cứ gì.** Khi user gõ `:nn <url>`:
  1. Bash function `scripts/nn.sh` fetch URL, chọn category ít bài nhất, tạo skeleton `.md` + lưu source gốc tại `.nn_source`.
  2. opencode (AI) đọc `.nn_source` + skeleton, rewrite bài ≥2000 từ, human-first, theo mọi rule trong AGENTS.md (TOML frontmatter, 5 category chuẩn, footer macro, meta description 50-160, không future date, không placeholder link, không IMAGE_API_QUERY marker).
  3. Tự động chạy `python3 scripts/select_images.py --post $path --fix` (đổi source Pexels↔Pixabay nếu rate limit).
  4. Tự động chạy `python3 scripts/add_commit_id.py --post $path` (SCOPE ONLY).
  5. Commit + push lên `main` (FIFO, cách nhau ≥30s).
  - **Tuyệt đối không hỏi user** slug, title, description, category, hay bất kỳ input nào.
  - Nếu cần thông tin thêm (ví dụ xu hướng mới) → tự web search, không hỏi.
  - File gốc: `scripts/nn.sh` (tracked trong repo).
- **`:nauy` là lệnh AUTONOMOUS — viết bài về Nauy (Norway).** Giống `:blog` nhưng category mặc định `du-lich`, tags `["Nauy", "Norway", "Bắc Âu"]`, và tự động chọn chủ đề liên quan đến Nauy (văn hóa, du lịch, lịch sử, kinh tế, ẩm thực, công nghệ...). Không hỏi user bất cứ gì.
  - Phân tích 5 category, chọn category ít bài nhất làm chủ đề.
  - Tự chọn topic phù hợp với category đó (dựa trên xu hướng, mùa vụ, hoặc kiến thức sẵn có).
  - Viết bài hoàn chỉnh ≥2000 từ, human-first, không mùi AI.
  - Lưu file `.md` đúng format TOML front matter.
  - Chạy `select_images.py --post content/posts/<slug>.md --fix` (tự đổi source Pexels↔Pixabay nếu rate limit). **Không** `--all`.
  - Chạy `add_commit_id.py --post content/posts/<slug>.md` (SCOPE ONLY — cấm full-tree).
  - Commit + push lên `main`.
  - **Tuyệt đối không hỏi user** slug, title, description, hay bất kỳ input nào. Nếu cần thông tin (ví dụ xu hướng mới) → tự web search, không hỏi.
  - **CẤM tạo file test/debug** như `test-*.md`, `debug-*.md` trong `content/posts/`. Mọi file tạo ra đều phải là bài blog thật, có frontmatter đầy đủ.

- **Content Depth:** Mọi bài viết (cả VN và EN) phải có chiều sâu thật, độ dài **từ 2000–3000 từ trở lên** (tối thiểu tuyệt đối 2000 từ, nhắm mốc 3000 từ cho bài trụ cột). Sử dụng thước đo `wc -w` trên nội dung markdown (loại bỏ front matter) để kiểm tra. Viết giọng human-first, có trải nghiệm thật, không có mùi AI, tuân thủ bản quyền + Review Chân Thật. Internal links và external links là **optional** — không bắt buộc phải thêm vào. Nếu muốn thêm links:
  - External links: trỏ đến nguồn tham khảo uy tín bên ngoài để tăng giá trị SEO.
  - Internal links: **TUYỆT ĐỐI CẤM link placeholder/fake** dạng `/posts/placeholder-*`. Nếu không có bài viết thật cùng chủ đề, bỏ qua internal link — không tạo link ảo. Lý do: link placeholder sinh ra trong quá trình gen bài (prompt yêu cầu "thêm internal link SEO"), agent tạo link tới bài chưa tồn tại. Cách khắc phục: agent chỉ được tạo internal link khi có slug bài viết thật trong `content/posts/`. Nếu chưa có bài thật, không thêm internal link nào hết.
- **CẤM future date — mọi bài phải có `date` ≤ thời điểm hiện tại (Asia/Ho_Chi_Minh).** Front matter đặt ngày ở tương lai là **fake**: qa_dates coi đó là lỗi (`future date`) và deployment doctor bắt ở Rule 5 (`future_date`, severity ERROR). Hậu quả nếu lọt: `qa_dates.py` FAIL → CI chặn deploy, **toàn bộ commit đứng sau cũng không lên được production** cho tới khi ngày được sửa. Cách chống + fix (scope): `python3 scripts/qa_dates.py --post content/posts/<slug>.md --fix-obvious` — **clamp future date** về `now` thật trên post trong scope (không full-tree). Full `qa_dates.py --fix-obvious` chỉ khi debt-fix/CI. `pre-deploy-validate.sh --fix` sau khi auto-fix sẽ **verify lại**, không báo "fixed" khống. Dung sai `FUTURE_TOLERANCE = 5 phút` (lệch đồng hồ nhỏ được bỏ qua). Khi tạo bài mới: luôn để `date` = thời gian thật lúc publish, **không đặt lịch tương lai** (Hugo `buildFuture` không dùng ở repo này).
- **Meta description phải dài 50–160 ký tự (chuẩn SEO).** Field `description` trong front matter TOML là đoạn snippet Google hiển thị: **>160 ký tự bị cắt cụt (`…`) ngoài SERP, <50 ký tự phí chỗ**. Quy tắc viết: giữ **từ khóa chính + năm** ở đầu câu, bỏ từ lặp/thừa, nhắm **~150–158 ký tự** để có biên an toàn, **không dùng dấu ngoặc kép bên trong** (tránh phải escape trong TOML). Không viết description kiểu đoạn mở bài dài rồi để bị cắt giữa chừng — phải là câu tóm tắt trọn nghĩa. Deployment doctor (`deploy-failure-healer.py`, Rule 9 `meta_description_length`) tự bắt bài ngoài khoảng 50–160 khi scan pre-deploy, severity WARNING. **Không auto-fix bằng script** (viết lại cần ngữ nghĩa, không bịa máy móc) — phải sửa tay rồi mới accept deploy.
- **Footer macro là NGUỒN DUY NHẤT cho 4 mục cuối bài — cấm hardcode.** Bốn mục sau BẮT BUỘC do macro `layouts/partials/post-footer.html` sinh ra từ front matter, **áp dụng cho MỌI bài dù thuộc Category nào**:
  - **Liên kết nội bộ được sử dụng trong bài viết** ← `[[internal_links]]` (`ref`, `title`)
  - **Liên kết bên ngoài được sử dụng trong bài viết** ← `[[external_links]]` (`url`, `title`)
  - **FAQ - Câu hỏi thường gặp** ← `[[faq]]` (`question`, `answer`)
  - **Bản quyền & Ghi nguồn** ← `[attribution]` (`copyright`, `source_note`)
  - **TUYỆT ĐỐI KHÔNG hardcode** các heading/nội dung này trong thân bài viết (`.md` body). Không viết tay `## FAQ`, `## Liên kết nội bộ`, `## Bản quyền`... trong body. Chỉ điền dữ liệu vào front matter, macro tự render.
  - Nếu lỡ hardcode → **move nội dung hardcode đó vào đúng field front matter tương ứng** rồi xóa khỏi body. Dùng script: `python3 scripts/move_hardcoded_footer_sections.py --fix` (scan-only nếu bỏ `--fix`). Việc dọn nợ hàng loạt phải làm ở PR `qa-debt-fix` riêng, không gộp vào deploy tính năng khác.
  - **`[[internal_links]]` trong front matter PHẢI được đề cập trong body bài viết.** Macro `post-footer.html` render label "Liên kết nội bộ được sử dụng trong bài viết" — nếu link không xuất hiện trong body (dạng markdown link `](...)` hoặc slug/title trong nội dung), coi là spam. Script `scripts/strip_unused_internal_links.py --write` tự động xoá các entry không có trong body. Deployment doctor bắt ở Rule 14 (`unused_internal_links`, severity WARNING) và Fix 5 tự động chạy trong `--fix-all`.
  - **`scripts/enhan_links.py`** chỉ thêm `[[internal_links]]` vào frontmatter — không tự động chèn gì vào body. Body links là trách nhiệm người viết (embedded tự nhiên trong câu văn, như ví dụ VPN trong bài mẫu). `strip_unused_internal_links.py` sẽ dọn các FM entry không có body reference. Workflow: `build_internal_link_graph.py --write` → `enhan_links.py insert` → `strip_unused_internal_links.py --write`.
- **TUYỆT ĐỐI CẤM `![[IMAGE_API_QUERY:...]]` markers trong nội dung bài viết.** Không được viết, không được giữ lại, không được coi là placeholder tạm thời. Đây là marker chết — không script nào xử lý, không tự động replace. Nếu marker còn sót trong file `.md` khi push, coi như lỗi nghiêm trọng, phải fix ngay. Ảnh minh họa inline chỉ được chèn bằng Markdown `![](...)` thủ công với URL ảnh thật.
- **Ảnh inline (`![](/images/posts/<slug>-inline.webp)`) resolve qua render hook, KHÔNG hardcode baseURL.** Site chạy dưới subpath `/reviewchanthat/`; hook `layouts/_default/_markup/render-image.html` (trim `/` đầu rồi `relURL`) tự thêm baseURL đúng cho cả production lẫn local dev. Vì vậy body cứ viết path gốc-tuyệt-đối `/images/posts/...` như bình thường — **đừng** tự chèn `/reviewchanthat/` vào body (sẽ hỏng khi dev local). Nếu hook bị xóa, ảnh inline toàn site 404. Kiểm tra bằng `python3 scripts/qa_inline_images.py` (xem Failure #11). Khi verify live phải soi `<img src>` trong HTML có `/reviewchanthat/`, không chỉ curl file ảnh thấy 200.

# Deployment Rule (từ 2026-07-10)

- **1 change = 1 branch = 1 deploy.** Mỗi tính năng / thay đổi phải được phát triển trên một nhánh riêng, tách biệt hoàn toàn với các nhánh tính năng khác.
- Không gộp chung nhiều tính năng vào cùng một nhánh deploy. Khi merge, chỉ merge đúng 1 nhánh tính năng duy nhất vào `main`.
- Deploy chỉ kích hoạt khi push commit tính năng lên `main`. Đảm bảo mỗi lần deploy chỉ mang đúng 1 thay đổi, tránh lẫn blog post, ảnh, hay bất kỳ file nào ngoài scope.
- **Chỉ đẩy ĐÚNG scope của mình — cấm đẩy code người khác/nhánh khác.** Khi làm việc trên `main` hoặc một nhánh dùng chung bởi nhiều session, bạn CHỈ được quan tâm và commit/push **đúng phần scope của mình**. Lúc đẩy code lên live cũng vậy: chỉ `git add` + push đúng những file thuộc scope bạn đang làm. TUYỆT ĐỐI không tự ý stage/commit/push thay đổi của người khác, của session khác, hay file untracked ngoài scope (ví dụ bài viết dở của nhánh khác). Nếu `git status` có file lạ ngoài scope → để nguyên, không đụng tới. Ưu tiên `git add <đúng-file>` thay vì `git add .` / `git add -A`.
- **Deploy FIFO — xếp hàng chờ, không chạy đồng loạt.** Các deploy phải cách nhau tối thiểu **30 giây**. Không push nhiều commit liên tiếp lên `main` trong cùng một khoảnh khắc. Dùng `git push` kèm kiểm tra GitHub Actions queue trước khi push commit tiếp theo. Tránh rate limit GitHub API, Pixabay/Pexels, và tránh concurrent build chồng chéo.

# SCOPE-ONLY scripts (từ 2026-07-16) — BẮT BUỘC

**Mỗi khi commit / merge / pre-push: CHỈ check và chạy script `*.py` trên file trong scope thay đổi. CẤM quét / fix toàn bộ blog.**

## Lệnh tắt merge scope

```bash
# Check only (posts trong diff origin/main...HEAD + working tree)
bash scripts/merge_scope.sh
# hoặc alias shell: :merge-scope

# Check + autofix CHỈ scope
bash scripts/merge_scope.sh --fix
# :merge-scope --fix

# Check rồi merge branch hiện tại → main (local; nhớ push FIFO)
bash scripts/merge_scope.sh --merge
# :merge-scope --merge

# Ép danh sách post
SCOPE_POSTS="content/posts/a.md content/posts/b.md" bash scripts/merge_scope.sh --fix
```

Lý do: full-tree (`add_commit_id.py`, `rule.py --fix`, `qa_dates.py`, `deploy-failure-healer.py --fix-all`, `strip_unused_internal_links.py --write`, `process_images.py`, `select_images.py --all`…) trên ~400 post **rất chậm**, dễ đụng file ngoài scope, và sinh diff rác.

## Cách lấy scope

```bash
# Post .md trong working tree / commit sắp push
git diff --name-only --cached -- content/posts/
git diff --name-only HEAD -- content/posts/
git diff --name-only origin/main...HEAD -- content/posts/
```

Gán biến (ví dụ 1–n slug):

```bash
# Một bài
POST="content/posts/<slug>.md"
SLUG="<slug>"

# Nhiều bài — lặp --post / --slug
POSTS=(content/posts/a.md content/posts/b.md)
```

## Script: dùng flag scope (không full-tree)

| Việc | Lệnh ĐÚNG (scope) | CẤM khi commit/merge feature |
|------|-------------------|------------------------------|
| Ảnh | `select_images.py --post $POST --fix` | `--all` |
| WebP | `process_images.py --slug $SLUG` | không flag (cả manifest) |
| Commit ID | `add_commit_id.py --post $POST` | không `--post` / chỉ `--all` khi debt |
| Dates | `qa_dates.py --post $POST` (+ `--fix-obvious` nếu cần) | không `--post` |
| Front matter | `rule.py --fix --post $POST` | `rule.py --fix` full |
| Healer | `deploy-failure-healer.py --scan --post $POST` / `--fix-all --post $POST` | `--scan` / `--fix-all` không `--post` |
| Internal links | `strip_unused_internal_links.py --write --post $POST` | `--write` full |
| Footer hardcode | `move_hardcoded_footer_sections.py --fix --post $POST` | `--fix` full |
| Inline images | `qa_inline_images.py` (hook global OK) + chỉ soi body post trong scope | — |

**Ngoại lệ full-tree** (chỉ khi user/PR `qa-debt-fix` / CI gate toàn site yêu cầu rõ): `--all`, không `--post`, `pre-deploy-validate.sh` full. Agent **không** tự full-tree sau mỗi bài/feature.

**Sau khi script chạy:** `git status` — nếu có file `.md` ngoài scope bị sửa → `git checkout -- <file-ngoài-scope>` trước khi commit.

# Deploy Failure Prevention & Auto-Healing (từ 2026-07-11)

## Pre-Deploy Checklist (Prevent 95% of failures) — **SCOPE-ONLY**

**BẮT BUỘC chạy TRƯỚC khi `git push origin main` — chỉ trên file trong scope (thay `<slug>` / lặp `--post`):**
```bash
# 0. Xác định scope (bắt buộc)
git diff --name-only origin/main...HEAD -- content/posts/
POST="content/posts/<slug>.md"   # hoặc nhiều --post
SLUG="<slug>"

# 1–2. Scan + fix chỉ post trong scope
python3 scripts/deploy-failure-healer.py --scan --post "$POST"
python3 scripts/deploy-failure-healer.py --fix-all --post "$POST"

# 3. Dates (ISO 8601 +07:00) — scope
python3 scripts/qa_dates.py --post "$POST"

# 4. Frontmatter TOML — scope (không full SAFE_FIX khi có --post)
python3 scripts/rule.py --fix --post "$POST"

# 5. Commit hash — CHỈ post trong scope
python3 scripts/add_commit_id.py --post "$POST"

# 6–8. Grep chỉ file scope (không content/posts/* toàn repo)
grep -n "commit:\|date:\|image:" "$POST" || true
grep -n "!\[\[IMAGE_API_QUERY:" "$POST" || true
grep -n "/posts/placeholder-" "$POST" || true

# 9. Unused [[internal_links]] — scope
python3 scripts/strip_unused_internal_links.py --dry-run --post "$POST"

# 10. Hardcoded footer — scope
python3 scripts/move_hardcoded_footer_sections.py --post "$POST" || echo "⚠ fix with --fix --post"

# 11. Empty .md chỉ trong scope (hoặc untracked mới)
# (không find toàn content/posts trừ khi debt-fix)

# 12. Commit field trên post scope
grep -n '^commit = ' "$POST"

# 13. Inline images (hook global) + path ảnh của slug
python3 scripts/qa_inline_images.py
ls -la "static/images/posts/${SLUG}.webp" 2>/dev/null || true
```

**Nhiều post trong 1 commit:** lặp `--post path1 --post path2` (các script hỗ trợ `action=append`).

If any check fails → **STOP** push and run deploy-failure-healer **với `--post`**, không `--fix-all` full-tree.

## Common Deployment Failures & Auto-Fixes

### Failure #1: YAML Syntax in TOML Frontmatter
**Symptom:** Hugo parse error on deployment, "commit: abc" instead of commit = "abc"
**Auto-Fix:** `python3 scripts/deploy-failure-healer.py --fix-all`
**Prevention:** ALWAYS use TOML syntax `key = "value"` in `+++...+++` blocks

### Failure #2: Missing Commit Hash
**Symptom:** Post fails QA check, can't track version
**Auto-Fix:** `python3 scripts/add_commit_id.py --post content/posts/<slug>.md` (SCOPE ONLY)
**Prevention:** Run after EVERY merge — chỉ post trong scope, cấm full-tree

### Failure #3: Missing Hero Image or Thumbnail
**Symptom:** Theme renders blank hero
**Auto-Fix:** `python3 scripts/select_images.py --post content/posts/<slug>.md --fix` (tự đổi source Pexels↔Pixabay khi rate limit)
**Prevention:** Never publish post without running image selection. Nếu đã thử **cả 2 API** mà vẫn không có ảnh hợp lệ → publish text-first (không ảnh), KHÔNG chèn ảnh fake. Đây không phải lỗi deploy.

### Failure #4: Wrong Timezone (+05:00, Z, or missing)
**Symptom:** Date sorting fails, posts appear out of order
**Auto-Fix:** `python3 scripts/qa_dates.py --post content/posts/<slug>.md --fix-obvious`
**Prevention:** Always use `+07:00` for Vietnam timezone

### Failure #5: Future Date
**Symptom:** Post doesn't appear on homepage (scheduled but broken)
**Auto-Fix:** `python3 scripts/qa_dates.py --post content/posts/<slug>.md --fix-obvious` (sets to now)
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

### Failure #13: Hardcoded Footer Sections in Body

**Symptom:** Bài viết có `[[internal_links]]`, `[[external_links]]`, `[[faq]]`, `[attribution]` hoặc heading `## Câu hỏi thường gặp` / `## FAQ` / `## Bản quyền` trong **body markdown** (sau `+++` thay vì trong front matter). Macro `layouts/partials/post-footer.html` không đọc được → các section này render raw text, thiếu styling, thiếu cấu trúc.

**Root Cause:** Khi viết bài (thủ công hoặc AI), các section footer được hardcode trực tiếp vào body thay vì điền vào TOML front matter. Điều này xảy ra phổ biến ở template cũ và AI-generated content không tuân thủ quy tắc macro.

**Detection:** `python3 scripts/move_hardcoded_footer_sections.py` (exit code != 0 nếu còn hardcoded sections). 
**Auto-Fix:** `python3 scripts/move_hardcoded_footer_sections.py --fix` — tự động move nội dung vào front matter đúng field và xóa khỏi body. Nếu có section khó parse (FAQ compact), script báo WARN và bỏ qua để xử lý thủ công.

**Prevention:**
- **`:hard9`** — phím tắt vĩnh viễn: quét + tự động fix toàn bộ (`~/.zshrc`).
- **`deploy-failure-healer.py` Rule 13 + Fix 5** — tự động phát hiện và sửa trong pipeline `--fix-all`.
- Khi viết bài mới: **LUÔN** đặt `[[internal_links]]`, `[[external_links]]`, `[[faq]]`, `[attribution]` trong `+++...+++` (front matter), KHÔNG viết trong body. Macro tự render 4 mục cuối bài.
- Nếu phát hiện heading `## Câu hỏi thường gặp` / `## Liên kết nội bộ` / `## Liên kết bên ngoài` / `## Bản quyền` trong body → đó là lỗi, phải move ngay.

### Failure #12: Empty/Zero-Byte .md Files
**Symptom:** Hugo build fails with "error parsing front matter" or `rule.py --fix` reports "still not TOML" on a post with 0 bytes. CI deploy fails, Autofix on Deploy Failure can't recover.

**Root Cause:** Test/debug `.md` files committed with no content (empty file). These don't have `+++...+++` frontmatter, so Hugo's TOML parser fails. `rule.py --fix` can't auto-fix because there's nothing to parse. Build pipeline stops at pre-deploy validate → no artifacts generated → deploy failure.

**Auto-Fix:** `python3 scripts/deploy-failure-healer.py --fix-all` detects 0-byte files and deletes them automatically.

**Prevention (pre-deploy checklist bổ sung):**
```bash
# Check for empty .md files — nếu != 0 thì REJECT push
find content/posts/ -name "*.md" -empty | wc -l
# Auto-delete nếu có:
find content/posts/ -name "*.md" -empty -delete && echo "Deleted empty files"
```

**Rule kỷ luật:**
- CẤM commit file `.md` rỗng/0 byte. Mọi file trong `content/posts/` phải có frontmatter TOML hợp lệ.
- `:blog` tạo sẵn skeleton đủ frontmatter → không tạo file rỗng.
- Sau mỗi lần fix deploy failure, ghi nhận nguyên nhân + auto-fix vào scripts + AGENTS.md để lần sau hệ thống tự xử lý.

### Failure #11: Broken Inline Images (baseURL subpath / missing file)
**Symptom:** Ảnh **inline** trong thân bài (`![](/images/posts/x.webp)`) hiển thị vỡ trên live, dù ảnh hero vẫn hiện bình thường.
**Root cause (2 loại):**
1. **baseURL subpath.** Site chạy dưới `baseURL = .../reviewchanthat/` với `canonifyURLs=false`. Ảnh inline dùng path gốc-tuyệt-đối `/images/posts/x.webp` giữ nguyên path đó trong `<img src>` → trình duyệt tải `github.io/images/...` (thiếu `/reviewchanthat/`) → **404**. Ảnh hero KHÔNG bị vì nó render từ frontmatter qua `relURL`. Đây là lỗi ảnh hưởng **toàn bộ bài có ảnh inline**.
2. **Thiếu file.** Ảnh inline trỏ tới file `.webp` không tồn tại trên đĩa.
**Root-cause fix (loại 1 — đã áp dụng):** render hook `layouts/_default/_markup/render-image.html` — trim dấu `/` đầu rồi `relURL` (`$dest | strings.TrimPrefix "/" | relURL`) → ra `/reviewchanthat/images/...` trên production, `/images/...` khi dev local; URL remote/`data:` giữ nguyên. Hook này sửa **mọi bài** tại thời điểm build, KHÔNG cần đụng vào body của post.
**Auto-Fix:** `python3 scripts/qa_inline_images.py --fix` (tự tạo lại hook nếu bị mất; đồng thời quét và báo các ảnh inline trỏ tới file thiếu).
**Prevention:**
- Body vẫn viết ảnh inline bình thường: `![alt](/images/posts/<slug>-inline.webp)` — hook lo phần resolve.
- Khi verify bài đã lên live: kiểm tra `<img src>` THẬT trong HTML phải chứa `/reviewchanthat/`, đừng chỉ curl file ảnh thấy 200 (asset 200 không chứng minh HTML trỏ đúng).
- Deploy-doctor bắt lỗi này ở **Rule 10** (`broken_inline_image` — file thiếu, WARNING) và **Rule 11** (`missing_render_image_hook` — hook bị mất, CRITICAL).

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
- Missing images → Run `select_images.py --post content/posts/<slug>.md --fix`
- Date issues → Run `qa_dates.py --post content/posts/<slug>.md --fix-obvious`
- Commit hash missing → Run `add_commit_id.py --post content/posts/<slug>.md`

**Step 3:** Run auto-healer **chỉ post lỗi** (không full-tree)
```bash
python3 scripts/deploy-failure-healer.py --fix-all --post content/posts/<slug>.md
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

1. **Pre-Deploy Checklist SCOPE-ONLY** — chỉ file trong diff, không full blog
2. **TOML syntax only** - Never use `key: value` in `+++...+++`
3. **2000–3000+ words, human-first** - Chiều sâu thật, không mùi AI, tuân thủ bản quyền. Check before committing
4. **Real images only** - Use Pexels/Pixabay API, đổi source khi rate limit; never fake. Không ra ảnh → ship text-first, không placeholder giả
5. **Chỉ 5 category chuẩn** - Không tạo category mới; content lạ → nhét vào category gần nhất (mặc định Đời sống)
6. **Commit hash tracking (scope)** - `add_commit_id.py --post …` after every merge; **cấm** full-tree
7. **Vietnam timezone** - Always +07:00, never +05:00 or Z
8. **No placeholder links** - Only link to existing posts
9. **No IMAGE_API_QUERY** - Remove all markers before push
10. **Footer macro only** - `[[internal_links]]`, `[[external_links]]`, `[[faq]]`, `[attribution]` chỉ trong front matter, cấm hardcode body. Scope: `move_hardcoded_footer_sections.py --fix --post …`
11. **Internal links must be in body** - Scope: `strip_unused_internal_links.py --write --post …`
12. **Deploy one at a time** - 30s minimum between pushes
13. **WebP in git** - commit `static/images/posts/<slug>.webp` (scope slug only)
14. **CẤM full-tree py sau mỗi commit/merge** — chỉ `--post` / `--slug`; full-tree = `qa-debt-fix` hoặc CI explicit

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
| Meta description length (50–160) | Pre-deploy | ❌ Manual | N/A |
| WebP tracking | Pre-deploy | ✅ Yes | < 1 min |
| Broken inline image (missing file) | Pre-deploy | ❌ Manual | N/A |
| Missing render-image hook | Pre-deploy | ✅ Yes | < 1 min |
| Empty/0-byte .md file | Pre-deploy | ✅ Yes | < 1 min |
| Hardcoded footer sections (macro bypass) | Pre-deploy | ✅ Yes | < 1 min |
| Unused internal links (not in body) | Pre-deploy | ✅ Yes | < 1 min |

**Goal: 0 deploy failures** through automated pre-deploy validation.
