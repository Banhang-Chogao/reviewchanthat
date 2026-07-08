const GITHUB_API_BASE = 'https://api.github.com';
const GITHUB_API_VERSION = '2022-11-28';
const DEFAULT_BRANCH = 'main';
const DEFAULT_CONTENT_DIR = 'content/posts';
const DEFAULT_IMAGE_SOURCE_DIR = 'static/images/posts-src';
const DEFAULT_PUBLIC_SITE_BASE = 'https://banhang-chogao.github.io/reviewchanthat/';
const DEFAULT_CATEGORIES_PATH = 'data/categories.json';
const DEFAULT_MAX_IMAGE_BYTES = 5 * 1024 * 1024;
const CATEGORY_SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const ALLOWED_IMAGE_EXTENSIONS = new Set(['jpg', 'jpeg', 'png', 'webp']);
const ALLOWED_IMAGE_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp']);

class HttpError extends Error {
  constructor(status, message, details) {
    super(message);
    this.name = 'HttpError';
    this.status = status;
    this.details = details || null;
  }
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin') || '';
    const corsHeaders = getCorsHeaders(env, origin);

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders });
    }

    try {
      const url = new URL(request.url);
      const pathname = url.pathname.replace(/\/+$/, '') || '/';

      if (pathname === '/' && request.method === 'GET') {
        return jsonResponse(
          {
            status: 'ok',
            service: 'veritable-content-cms-publish',
            endpoints: {
              publish: 'POST /api/cms/publish',
              categories: 'GET/PUT /api/cms/categories',
              deployStatus: 'GET /api/cms/deploy-status?run_id=<id>'
            }
          },
          200,
          corsHeaders
        );
      }

      if (pathname === '/api/cms/publish' && request.method === 'POST') {
        await requireAdmin(request, env);
        const result = await publishArticle(request, env);
        return jsonResponse(result, 200, corsHeaders);
      }

      if (pathname === '/api/cms/categories' && request.method === 'GET') {
        await requireAdmin(request, env);
        const result = await getCategoriesCatalog(env);
        return jsonResponse(result, 200, corsHeaders);
      }

      if (pathname === '/api/cms/categories' && request.method === 'PUT') {
        await requireAdmin(request, env);
        const result = await saveCategoriesCatalogRequest(request, env);
        return jsonResponse(result, 200, corsHeaders);
      }

      if (pathname === '/api/cms/deploy-status' && request.method === 'GET') {
        await requireAdmin(request, env);
        const result = await getDeployStatus(url, env);
        return jsonResponse(result, 200, corsHeaders);
      }

      return jsonResponse(
        {
          status: 'error',
          message: 'Not found',
          hint: 'Use POST /api/cms/publish with Authorization: Bearer <admin-token>'
        },
        404,
        corsHeaders
      );
    } catch (error) {
      const status = error instanceof HttpError ? error.status : 500;
      const message = error instanceof Error ? error.message : 'Internal server error';
      console.error(JSON.stringify({ message: 'cms request failed', status, error: message }));
      return jsonResponse(
        {
          status: 'error',
          message,
          details: error instanceof HttpError ? error.details : null
        },
        status,
        corsHeaders
      );
    }
  }
};

async function publishArticle(request, env) {
  const form = await request.formData();
  const payload = parsePayload(form.get('payload'));
  const normalized = normalizePayload(payload);
  validatePublishPayload(normalized);

  const branch = env.GITHUB_BRANCH || DEFAULT_BRANCH;
  const contentDir = cleanRepoDir(env.CMS_CONTENT_DIR || DEFAULT_CONTENT_DIR);
  const imageSourceDir = cleanRepoDir(env.CMS_IMAGE_SOURCE_DIR || DEFAULT_IMAGE_SOURCE_DIR);
  const articlePath = `${contentDir}/${normalized.slug}.md`;
  ensureSafeRepoPath(articlePath);

  const message = normalized.draft
    ? `cms: save draft ${normalized.slug}`
    : `cms: publish ${normalized.slug}`;

  const uploadedImages = [];
  const commits = [];

  for (let index = 0; index < normalized.images.length; index += 1) {
    const image = normalized.images[index];
    if (!image.fileField) {
      continue;
    }

    const fileValue = form.get(image.fileField);
    if (!(fileValue instanceof File)) {
      throw new HttpError(400, `Image ${index + 1} file is missing`);
    }

    const upload = await uploadImageFile(fileValue, image, index, imageSourceDir, branch, message, env);
    uploadedImages.push(upload.image);
    commits.push(...upload.commits);
  }

  if (normalized.categoriesCatalog) {
    const categoriesCommit = await saveCategoriesCatalog(normalized.categoriesCatalog, message, branch, env);
    if (categoriesCommit) {
      commits.push(categoriesCommit);
    }
  }

  const articleCommit = await putGithubContent(articlePath, normalized.markdown, message, branch, env);
  commits.push(articleCommit);

  const deploy = await triggerDeployIfNeeded(branch, env, articleCommit.sha);
  const articleUrl = buildArticleUrl(normalized.slug, env);

  return {
    status: deploy.status === 'failed' ? 'published_with_deploy_error' : 'published',
    commit_sha: articleCommit.sha,
    article_path: articlePath,
    article_url: articleUrl,
    uploaded_images: uploadedImages,
    categories_updated: Boolean(normalized.categoriesCatalog),
    commits,
    deploy
  };
}

async function getCategoriesCatalog(env) {
  const branch = env.GITHUB_BRANCH || DEFAULT_BRANCH;
  const catalog = await loadCategoriesCatalog(branch, env);
  return {
    status: 'ok',
    path: categoriesPath(env),
    catalog
  };
}

async function saveCategoriesCatalogRequest(request, env) {
  const body = await request.json().catch(() => null);
  if (!body || typeof body !== 'object') {
    throw new HttpError(400, 'Category catalog JSON body is required');
  }

  const branch = env.GITHUB_BRANCH || DEFAULT_BRANCH;
  const catalog = normalizeCategoriesCatalog(body.catalog || body);
  const message = String(body.message || 'cms: update categories').trim() || 'cms: update categories';
  const commit = await saveCategoriesCatalog(catalog, message, branch, env);

  return {
    status: 'ok',
    path: categoriesPath(env),
    commit_sha: commit ? commit.sha : '',
    catalog
  };
}

async function loadCategoriesCatalog(branch, env) {
  const path = categoriesPath(env);
  try {
    const text = await readTextFile(path, branch, env);
    return normalizeCategoriesCatalog(safeJsonParse(text));
  } catch (error) {
    if (error instanceof HttpError && error.status === 404) {
      return normalizeCategoriesCatalog({});
    }
    throw error;
  }
}

async function saveCategoriesCatalog(catalogInput, message, branch, env) {
  const catalog = normalizeCategoriesCatalog(catalogInput);
  const remote = await loadCategoriesCatalog(branch, env);
  const nextText = `${JSON.stringify(catalog, null, 2)}\n`;
  const remoteText = `${JSON.stringify(remote, null, 2)}\n`;

  if (nextText === remoteText) {
    return null;
  }

  return putGithubContent(categoriesPath(env), nextText, message, branch, env);
}

function categoriesPath(env) {
  const path = String(env.CMS_CATEGORIES_PATH || DEFAULT_CATEGORIES_PATH).trim();
  ensureSafeRepoPath(path);
  return path;
}

function normalizeCategoriesCatalog(raw) {
  const source = raw && typeof raw === 'object' ? raw : {};
  let items = [];

  if (Array.isArray(source.items)) {
    items = source.items.map(normalizeCategoryItem);
  } else if (source.labels && typeof source.labels === 'object') {
    items = Object.entries(source.labels).map(([slug, label], index) => normalizeCategoryItem({
      slug,
      label,
      description: '',
      nav: true,
      order: (index + 1) * 10
    }));
  }

  items.sort((left, right) => left.order - right.order || left.slug.localeCompare(right.slug));

  const aliases = { ...(source.aliases && typeof source.aliases === 'object' ? source.aliases : {}) };
  for (const item of items) {
    aliases[item.slug] = item.slug;
    aliases[item.label.toLowerCase()] = item.slug;
    aliases[slugify(item.label)] = item.slug;
  }

  return {
    items,
    aliases
  };
}

function normalizeCategoryItem(item) {
  const slug = slugify(String(item && item.slug ? item.slug : ''));
  const label = String(item && item.label ? item.label : slug).trim() || slug;

  if (!slug || !CATEGORY_SLUG_RE.test(slug)) {
    throw new HttpError(400, `Invalid category slug: ${slug || '(empty)'}`);
  }

  return {
    slug,
    label,
    description: String(item && item.description ? item.description : '').trim(),
    nav: item && item.nav === false ? false : true,
    order: Number.isFinite(Number(item && item.order)) ? Number(item.order) : 100
  };
}

function validateCategoriesCatalog(catalogInput) {
  normalizeCategoriesCatalog(catalogInput);
}

async function uploadImageFile(file, image, index, imageSourceDir, branch, message, env) {
  const maxBytes = parseInteger(env.CMS_MAX_IMAGE_BYTES, DEFAULT_MAX_IMAGE_BYTES);

  if (!image.alt) {
    throw new HttpError(400, `Image ${index + 1} alt text is required`);
  }

  if (file.size > maxBytes) {
    throw new HttpError(400, `Image ${file.name} exceeds max size ${maxBytes} bytes`);
  }

  const safeName = safeImageFileName(file.name);
  const extension = safeName.split('.').pop() || '';
  const contentType = file.type || guessImageContentType(extension);

  if (!ALLOWED_IMAGE_EXTENSIONS.has(extension)) {
    throw new HttpError(400, `Image ${file.name} has an unsupported extension`);
  }

  if (contentType && !ALLOWED_IMAGE_TYPES.has(contentType)) {
    throw new HttpError(400, `Image ${file.name} has unsupported type ${contentType}`);
  }

  const sourcePath = `${imageSourceDir}/${safeName}`;
  const metadataPath = `${sourcePath}.meta.json`;
  ensureSafeRepoPath(sourcePath);
  ensureSafeRepoPath(metadataPath);

  const imageBytes = await file.arrayBuffer();
  const imageCommit = await putGithubContentBase64(
    sourcePath,
    arrayBufferToBase64(imageBytes),
    message,
    branch,
    env
  );

  const metadata = {
    source: 'self-owned',
    pipeline_source: 'self',
    source_url: '',
    license: 'Owned by Veritable Content',
    commercial_use: true,
    watermark: true,
    alt: image.alt,
    caption: image.caption || '',
    markdown_path: image.path || processedImagePath(safeName)
  };

  const metadataCommit = await putGithubContent(
    metadataPath,
    `${JSON.stringify(metadata, null, 2)}\n`,
    message,
    branch,
    env
  );

  return {
    image: {
      original_name: file.name,
      safe_name: safeName,
      source_path: sourcePath,
      metadata_path: metadataPath,
      markdown_path: metadata.markdown_path,
      alt: image.alt,
      caption: image.caption || ''
    },
    commits: [imageCommit, metadataCommit]
  };
}

async function getDeployStatus(url, env) {
  const runId = url.searchParams.get('run_id');
  if (!runId || !/^\d+$/.test(runId)) {
    throw new HttpError(400, 'run_id is required');
  }

  const response = await githubJson(`/repos/${repoPath(env)}/actions/runs/${runId}`, {
    method: 'GET'
  }, env);

  return {
    status: 'ok',
    run_id: response.id,
    run_status: response.status,
    conclusion: response.conclusion,
    html_url: response.html_url
  };
}

async function triggerDeployIfNeeded(branch, env, commitSha) {
  const workflow = env.GITHUB_DEPLOY_WORKFLOW || '';
  if (!workflow) {
    return { status: 'auto_on_push', commit_sha: commitSha };
  }

  try {
    const workflowText = await readTextFile(`.github/workflows/${workflow}`, branch, env);
    if (workflowText && workflowHasPushForBranch(workflowText, branch) && env.CMS_FORCE_WORKFLOW_DISPATCH !== 'true') {
      return {
        status: 'auto_on_push',
        workflow,
        ref: branch,
        commit_sha: commitSha
      };
    }
  } catch (error) {
    if (!(error instanceof HttpError && error.status === 404)) {
      throw error;
    }
  }

  try {
    await githubJson(`/repos/${repoPath(env)}/actions/workflows/${encodeURIComponent(workflow)}/dispatches`, {
      method: 'POST',
      body: JSON.stringify({ ref: branch })
    }, env);

    return {
      status: 'triggered',
      workflow,
      ref: branch,
      commit_sha: commitSha
    };
  } catch (error) {
    return {
      status: 'failed',
      workflow,
      ref: branch,
      commit_sha: commitSha,
      error: error instanceof Error ? error.message : 'Deploy trigger failed'
    };
  }
}

async function putGithubContent(path, text, message, branch, env) {
  return putGithubContentBase64(path, utf8ToBase64(text), message, branch, env);
}

async function putGithubContentBase64(path, base64Content, message, branch, env) {
  const existingSha = await getGithubContentSha(path, branch, env);
  const body = {
    message,
    content: base64Content,
    branch
  };

  if (existingSha) {
    body.sha = existingSha;
  }

  const name = env.CMS_COMMITTER_NAME || '';
  const email = env.CMS_COMMITTER_EMAIL || '';
  if (name && email) {
    body.committer = { name, email };
  }

  const result = await githubJson(`/repos/${repoPath(env)}/contents/${encodePath(path)}`, {
    method: 'PUT',
    body: JSON.stringify(body)
  }, env);

  return {
    path,
    sha: result.commit && result.commit.sha ? result.commit.sha : '',
    html_url: result.content && result.content.html_url ? result.content.html_url : ''
  };
}

async function getGithubContentSha(path, branch, env) {
  try {
    const result = await githubJson(`/repos/${repoPath(env)}/contents/${encodePath(path)}?ref=${encodeURIComponent(branch)}`, {
      method: 'GET'
    }, env);
    return typeof result.sha === 'string' ? result.sha : '';
  } catch (error) {
    if (error instanceof HttpError && error.status === 404) {
      return '';
    }
    throw error;
  }
}

async function readTextFile(path, branch, env) {
  const result = await githubJson(`/repos/${repoPath(env)}/contents/${encodePath(path)}?ref=${encodeURIComponent(branch)}`, {
    method: 'GET'
  }, env);

  if (typeof result.content !== 'string') {
    return '';
  }

  return base64ToUtf8(result.content);
}

async function githubJson(path, init, env) {
  if (!env.GITHUB_TOKEN) {
    throw new HttpError(500, 'GitHub token invalid or missing permissions');
  }

  const response = await fetch(`${GITHUB_API_BASE}${path}`, {
    ...init,
    headers: {
      Accept: 'application/vnd.github+json',
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      'Content-Type': 'application/json',
      'User-Agent': 'veritable-content-cms-worker',
      'X-GitHub-Api-Version': GITHUB_API_VERSION,
      ...(init && init.headers ? init.headers : {})
    }
  });

  if (response.status === 204) {
    return {};
  }

  const text = await response.text();
  const data = text ? safeJsonParse(text) : {};

  if (!response.ok) {
    throw mapGithubError(response.status, data);
  }

  return data;
}

function mapGithubError(status, data) {
  const githubMessage = data && typeof data.message === 'string' ? data.message : '';

  if (status === 401 || status === 403) {
    return new HttpError(status, 'GitHub token invalid or missing permissions', githubMessage);
  }
  if (status === 404) {
    return new HttpError(status, 'Repo/path/workflow not found', githubMessage);
  }
  if (status === 409) {
    return new HttpError(status, 'File conflict, refresh and retry', githubMessage);
  }
  if (status === 422) {
    return new HttpError(status, 'Invalid GitHub request, check payload', githubMessage);
  }

  return new HttpError(status, githubMessage || 'GitHub API request failed');
}

async function requireAdmin(request, env) {
  if (!env.CMS_ADMIN_SECRET) {
    throw new HttpError(500, 'CMS admin secret is not configured');
  }

  const auth = request.headers.get('Authorization') || '';
  const prefix = 'Bearer ';
  if (!auth.startsWith(prefix)) {
    throw new HttpError(401, 'Admin authorization is required');
  }

  const provided = auth.slice(prefix.length).trim();
  const providedHash = await sha256(provided);
  const expectedHash = await sha256(env.CMS_ADMIN_SECRET);
  if (!crypto.subtle.timingSafeEqual(providedHash, expectedHash)) {
    throw new HttpError(403, 'Admin authorization failed');
  }
}

function parsePayload(value) {
  if (typeof value !== 'string' || !value.trim()) {
    throw new HttpError(400, 'Publish payload is required');
  }
  try {
    return JSON.parse(value);
  } catch (error) {
    throw new HttpError(400, 'Publish payload must be valid JSON');
  }
}

function normalizePayload(payload) {
  const images = Array.isArray(payload.images) ? payload.images.map(normalizeImage) : [];
  const tags = Array.isArray(payload.tags)
    ? payload.tags.map((item) => String(item).trim()).filter(Boolean)
    : splitCommaList(payload.tags);
  const title = String(payload.title || '').trim();

  return {
    title,
    slug: slugify(title),
    description: String(payload.description || '').trim(),
    category: String(payload.category || '').trim(),
    tags,
    date: String(payload.date || '').trim(),
    lastmod: String(payload.lastmod || payload.date || '').trim(),
    draft: payload.draft !== false,
    cover: String(payload.cover || '').trim(),
    body: String(payload.body || payload.content || '').trim(),
    markdown: String(payload.markdown || payload.generatedMarkdownFullContent || '').trim(),
    images,
    categoriesCatalog: payload.categoriesCatalog || null
  };
}

function normalizeImage(image) {
  return {
    path: String(image && image.path ? image.path : '').trim(),
    alt: String(image && image.alt ? image.alt : '').trim(),
    caption: String(image && image.caption ? image.caption : '').trim(),
    fileField: String(image && image.fileField ? image.fileField : '').trim()
  };
}

function validatePublishPayload(payload) {
  if (!payload.title) {
    throw new HttpError(400, 'title required');
  }
  const expectedSlug = slugify(payload.title);
  if (payload.slug !== expectedSlug) {
    throw new HttpError(400, `slug must match title. Expected: "${expectedSlug}"`);
  }
  if (!payload.body) {
    throw new HttpError(400, 'body required');
  }
  if (!payload.category) {
    throw new HttpError(400, 'category required');
  }
  if (!isRealDate(payload.date)) {
    throw new HttpError(400, 'date must be real YYYY-MM-DD');
  }
  if (payload.lastmod && !isRealDate(payload.lastmod)) {
    throw new HttpError(400, 'lastmod must be real YYYY-MM-DD');
  }
  if (!payload.markdown || !payload.markdown.startsWith('---')) {
    throw new HttpError(400, 'generated markdown full content is required');
  }

  const contentForChecks = [
    payload.title,
    payload.description,
    payload.category,
    payload.tags.join(','),
    payload.body,
    payload.markdown
  ].join('\n');

  if (/\bTODO\b|fake date/i.test(contentForChecks)) {
    throw new HttpError(400, 'TODO or fake date text is not allowed');
  }
  if (/tamsudev\.com@gmail\.com|users\.noreply\.github\.com/i.test(contentForChecks)) {
    throw new HttpError(400, 'Blocked contact email is not allowed');
  }
  if (/https?:\/\/(?:www\.)?(?:facebook\.com|fb\.com|youtube\.com|youtu\.be)\//i.test(contentForChecks)) {
    throw new HttpError(400, 'Raw Facebook/YouTube contact links are not allowed');
  }

  for (let index = 0; index < payload.images.length; index += 1) {
    const image = payload.images[index];
    if (image.fileField && !image.alt) {
      throw new HttpError(400, `Image ${index + 1} alt text is required`);
    }
    if (image.path) {
      ensureSafePublicPath(image.path);
    }
  }

  if (payload.categoriesCatalog) {
    validateCategoriesCatalog(payload.categoriesCatalog);
  }
}

function isRealDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return false;
  }
  const [year, month, day] = value.split('-').map((item) => Number(item));
  const date = new Date(Date.UTC(year, month - 1, day));
  return date.getUTCFullYear() === year && date.getUTCMonth() + 1 === month && date.getUTCDate() === day;
}

function splitCommaList(value) {
  return String(value || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

function safeImageFileName(filename) {
  const clean = String(filename || '').replace(/\\/g, '/').split('/').pop() || '';
  const match = clean.match(/\.([a-zA-Z0-9]+)$/);
  const extension = match ? match[1].toLowerCase() : '';
  if (!extension || !ALLOWED_IMAGE_EXTENSIONS.has(extension)) {
    throw new HttpError(400, `Image validation fail: ${filename} has unsupported extension`);
  }

  const stem = clean.slice(0, clean.length - extension.length - 1);
  const safeStem = slugify(stem);
  if (!safeStem) {
    throw new HttpError(400, `Image validation fail: ${filename} has unsafe filename`);
  }

  return `${safeStem}.${extension === 'jpeg' ? 'jpg' : extension}`;
}

function processedImagePath(safeName) {
  const stem = safeName.replace(/\.[^.]+$/, '');
  return `images/posts/${stem}-hero.webp`;
}

function slugify(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/đ/g, 'd')
    .replace(/Đ/g, 'd')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .replace(/-{2,}/g, '-');
}

function cleanRepoDir(value) {
  const dir = String(value || '').trim().replace(/^\/+|\/+$/g, '');
  ensureSafeRepoPath(dir);
  return dir;
}

function ensureSafeRepoPath(path) {
  if (!path || path.startsWith('/') || path.includes('../') || path.includes('..\\') || /[\x00-\x1F]/.test(path)) {
    throw new HttpError(400, `Unsafe repository path: ${path}`);
  }
}

function ensureSafePublicPath(path) {
  if (path.includes('../') || path.includes('..\\') || /[\x00-\x1F]/.test(path)) {
    throw new HttpError(400, `Unsafe image path: ${path}`);
  }
}

function workflowHasPushForBranch(workflowText, branch) {
  if (!/^\s*push\s*:/m.test(workflowText)) {
    return false;
  }
  const escapedBranch = branch.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const inlineBranches = new RegExp(`branches\\s*:\\s*\\[[^\\]]*\\b${escapedBranch}\\b[^\\]]*\\]`);
  const listBranches = new RegExp(`branches\\s*:\\s*\\n(?:\\s*-\\s*["']?${escapedBranch}["']?\\s*\\n?)`);
  return inlineBranches.test(workflowText) || listBranches.test(workflowText);
}

function buildArticleUrl(slug, env) {
  const base = env.CMS_PUBLIC_SITE_BASE || DEFAULT_PUBLIC_SITE_BASE;
  return `${base.replace(/\/+$/, '')}/posts/${slug}/`;
}

function repoPath(env) {
  const owner = env.GITHUB_OWNER || '';
  const repo = env.GITHUB_REPO || '';
  if (!owner || !repo) {
    throw new HttpError(500, 'GitHub owner/repo is not configured');
  }
  return `${owner}/${repo}`;
}

function encodePath(path) {
  return path.split('/').map((part) => encodeURIComponent(part)).join('/');
}

function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let index = 0; index < bytes.length; index += 0x8000) {
    const chunk = bytes.subarray(index, index + 0x8000);
    binary += String.fromCharCode(...chunk);
  }
  return btoa(binary);
}

function utf8ToBase64(value) {
  return arrayBufferToBase64(new TextEncoder().encode(value).buffer);
}

function base64ToUtf8(base64) {
  const binary = atob(String(base64 || '').replace(/\s/g, ''));
  const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}

function guessImageContentType(extension) {
  if (extension === 'jpg' || extension === 'jpeg') {
    return 'image/jpeg';
  }
  if (extension === 'png') {
    return 'image/png';
  }
  if (extension === 'webp') {
    return 'image/webp';
  }
  return '';
}

function parseInteger(value, fallback) {
  const parsed = Number.parseInt(String(value || ''), 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

async function sha256(value) {
  return crypto.subtle.digest('SHA-256', new TextEncoder().encode(value));
}

function safeJsonParse(text) {
  try {
    return JSON.parse(text);
  } catch (error) {
    return {};
  }
}

function jsonResponse(body, status, corsHeaders) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      ...corsHeaders
    }
  });
}

function getCorsHeaders(env, origin) {
  const allowed = String(env.CMS_ALLOWED_ORIGIN || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
  const allowOrigin = origin && allowed.includes(origin) ? origin : allowed[0] || '*';

  return {
    'Access-Control-Allow-Origin': allowOrigin,
    'Access-Control-Allow-Methods': 'POST, GET, PUT, OPTIONS',
    'Access-Control-Allow-Headers': 'Authorization, Content-Type',
    'Access-Control-Max-Age': '86400',
    Vary: 'Origin'
  };
}
