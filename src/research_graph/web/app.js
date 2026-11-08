const STATUSES = ["draft", "published", "boosted", "archived"];

const DATALISTS = {
  creator_tier: ["Nano", "Micro", "Mid-Tier", "Macro", "Mega"],
  creator_category: [
    "Automotive", "Beauty", "DIY", "Education", "Entertainment", "Fashion", "Finance",
    "Fitness", "Food", "Gaming", "Home", "Lifestyle", "Parenting", "Pets", "Sports",
    "Technology", "Travel",
  ],
  creator_country: ["AU", "BR", "CA", "DE", "FR", "JP", "UK", "US"],
  product_category: [
    "Accessories", "Baby Products", "Beauty", "Electronics", "Fashion", "Fitness", "Food",
    "Gaming", "Home", "Kitchen", "Lifestyle", "Makeup", "Other", "Pet Products", "Shoes",
    "Skincare", "Smartphones", "Sports", "Toys",
  ],
  video_format: [
    "Before & After", "Comedy", "Comparison", "Lifestyle", "Other", "Problem-Solution",
    "Product Demo", "Reaction", "Review", "Storytelling", "Testimonial", "Trend", "Tutorial",
    "Unboxing",
  ],
  video_title_type: ["Demo", "How To", "Review", "Tutorial", "Unboxing"],
  hook_type: [
    "Before & After", "Challenge", "Comparison", "Curiosity", "Demonstration", "Discount",
    "Problem", "Product Reveal", "Question", "Shock", "Social Proof", "Story", "Trend",
    "Urgency",
  ],
  season: ["Fall", "Holiday", "Spring", "Summer", "Winter"],
};

// [имя признака, подпись, значение по умолчанию, шаг]
const NUMBER_FIELDS = [
  ["creator_followers", "Подписчики креатора", 10000, "1"],
  ["creator_engagement_rate", "Вовлечённость креатора, %", 9.8, "0.1"],
  ["creator_post_frequency", "Постов в день", 0.8, "0.1"],
  ["product_price", "Цена товара", 47, "0.01"],
  ["product_rating", "Рейтинг товара (0–5)", 4, "0.1"],
  ["video_length_seconds", "Длительность видео, сек.", 60, "1"],
  ["video_upload_hour", "Час публикации (0–23)", 17, "1"],
  ["hook_strength_score", "Сила хука (0–100)", 60, "1"],
];

const TEXT_FIELDS = [
  ["creator_tier", "Уровень креатора", "Micro"],
  ["creator_category", "Тематика креатора", "Beauty"],
  ["creator_country", "Страна креатора", "US"],
  ["product_category", "Категория товара", "Beauty"],
  ["video_format", "Формат видео", "Tutorial"],
  ["video_title_type", "Тип заголовка", "Tutorial"],
  ["hook_type", "Тип хука", "Curiosity"],
  ["season", "Сезон", "Fall"],
];

const FLAG_FIELDS = [
  ["hook_problem_statement_flag", "Постановка проблемы"],
  ["hook_discount_hook_flag", "Скидка"],
  ["hook_shock_hook_flag", "Шок"],
  ["hook_question_hook_flag", "Вопрос"],
  ["hook_demo_hook_flag", "Демонстрация"],
  ["hook_before_after_hook_flag", "До и после"],
  ["hook_social_proof_hook_flag", "Социальное доказательство"],
  ["hook_story_hook_flag", "История"],
  ["hook_trend_hook_flag", "Тренд"],
  ["hook_product_reveal_flag", "Показ товара"],
  ["discount_code_flag", "Промокод"],
  ["free_shipping_flag", "Бесплатная доставка"],
];

const ADVICE = {
  boost: "Усилить бюджет: вероятность заметно выше средней.",
  watch: "Понаблюдать: вероятность немного выше средней.",
  skip: "Не вкладываться: вероятность на уровне средней или ниже.",
};

class ApiError extends Error {
  constructor(message, status, details) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

/* ---------- вспомогательные функции ---------- */

function h(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "class") {
      node.className = value;
    } else if (key.startsWith("on") && typeof value === "function") {
      node.addEventListener(key.slice(2), value);
    } else if (value === true) {
      node.setAttribute(key, "");
    } else if (value !== false && value !== null && value !== undefined) {
      node.setAttribute(key, value);
    }
  }
  for (const child of children.flat()) {
    node.append(child instanceof Node ? child : document.createTextNode(String(child ?? "")));
  }
  return node;
}

const $ = (selector) => document.querySelector(selector);

async function api(method, path, { body, form, query } = {}) {
  const url = new URL(path, window.location.origin);
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== "" && value !== null && value !== undefined) {
      url.searchParams.set(key, value);
    }
  }
  const init = { method, headers: {} };
  if (form) {
    init.body = form;
  } else if (body !== undefined) {
    init.headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(url, init);
  } catch {
    throw new ApiError("Сервер недоступен. Проверьте, что приложение запущено.", 0);
  }
  if (response.status === 204) {
    return null;
  }
  const text = await response.text();
  let data = null;
  try {
    data = JSON.parse(text);
  } catch {
    data = null;
  }
  if (!response.ok) {
    const error = data?.error;
    throw new ApiError(error?.message ?? `Ошибка ${response.status}`, response.status, error?.details);
  }
  return data;
}

function errorText(error) {
  if (!(error instanceof ApiError)) {
    return `Неожиданная ошибка: ${error.message}`;
  }
  let text = error.message;
  if (Array.isArray(error.details)) {
    const parts = error.details.map((d) => (typeof d === "object" ? `${d.field}: ${d.message}` : d));
    if (parts.length > 0) {
      text += ` (${parts.join("; ")})`;
    }
  }
  return text;
}

function notify(message, kind = "ok") {
  const box = $("#notice");
  box.textContent = message;
  box.className = kind;
  box.hidden = false;
}

function clearNotice() {
  $("#notice").hidden = true;
}

async function run(action) {
  try {
    await action();
  } catch (error) {
    notify(errorText(error), "error");
  }
}

const percent = (value) => `${(value * 100).toFixed(1)}%`;

function numberOrUndefined(value) {
  return value === "" || value === null ? undefined : Number(value);
}

function textOrUndefined(value) {
  const trimmed = String(value ?? "").trim();
  return trimmed === "" ? undefined : trimmed;
}

function table(headers, rows) {
  return h(
    "table",
    {},
    h("thead", {}, h("tr", {}, headers.map((title) => h("th", {}, title)))),
    h("tbody", {}, rows.map((cells) => h("tr", {}, cells.map((cell) => h("td", {}, cell))))),
  );
}

function bar(rate) {
  const fill = h("div");
  fill.style.width = `${Math.min(100, Math.round(rate * 100))}%`;
  return h("div", { class: "bar", role: "img", "aria-label": percent(rate) }, fill);
}

function renderPager(container, state, total, reload) {
  const pages = Math.max(1, Math.ceil(total / state.size));
  container.replaceChildren(
    h(
      "button",
      {
        type: "button",
        disabled: state.page <= 1,
        onclick: () => {
          state.page -= 1;
          run(reload);
        },
      },
      "Назад",
    ),
    h("span", {}, `Страница ${state.page} из ${pages}, всего ${total}`),
    h(
      "button",
      {
        type: "button",
        disabled: state.page >= pages,
        onclick: () => {
          state.page += 1;
          run(reload);
        },
      },
      "Вперёд",
    ),
  );
}

/* ---------- прогноз ---------- */

function buildPredictForm() {
  const fields = $("#predict-fields");
  for (const [name, label, value, step] of NUMBER_FIELDS) {
    fields.append(
      h("label", {}, label, h("input", { name, type: "number", step, value, inputmode: "decimal" })),
    );
  }
  for (const [name, label, value] of TEXT_FIELDS) {
    fields.append(h("label", {}, label, h("input", { name, value, list: `dl-${name}` })));
  }
  const flags = $("#predict-flags");
  for (const [name, label] of FLAG_FIELDS) {
    flags.append(h("label", {}, h("input", { type: "checkbox", name }), label));
  }
}

function collectPredictRecord(form) {
  const record = {};
  for (const [name] of NUMBER_FIELDS) {
    const value = numberOrUndefined(form.elements[name].value);
    if (value !== undefined) {
      record[name] = value;
    }
  }
  for (const [name] of TEXT_FIELDS) {
    const value = textOrUndefined(form.elements[name].value);
    if (value !== undefined) {
      record[name] = value;
    }
  }
  for (const [name] of FLAG_FIELDS) {
    record[name] = form.elements[name].checked ? 1 : 0;
  }
  return record;
}

function showPrediction(item) {
  const box = $("#predict-result");
  box.replaceChildren(
    h("p", { class: "muted" }, "Вероятность стать виральным"),
    h("p", { class: "big" }, percent(item.probability)),
    bar(item.probability),
    h("p", {}, h("span", { class: `badge ${item.recommendation}` }, item.recommendation)),
    h("p", {}, ADVICE[item.recommendation] ?? ""),
    h("p", { class: "muted" }, `Прогноз viral_flag: ${item.viral_flag}. Средняя доля в данных: 12,7%.`),
  );
  box.hidden = false;
}

function showCsvResult(data) {
  const box = $("#csv-result");
  const columns = [
    "video_id",
    "viral_flag",
    "predicted_probability",
    "predicted_viral_flag",
    "recommendation",
  ].filter((name) => data.rows.length > 0 && name in data.rows[0]);
  const preview = data.rows.slice(0, 10);
  box.replaceChildren(
    h("p", {}, `Строк: ${data.rows_total}. ROC-AUC: ${data.roc_auc ?? "нет (в файле нет viral_flag)"}.`),
    h("p", { class: "muted" }, `Показаны первые ${preview.length} строк.`),
    h(
      "div",
      { class: "scroll" },
      table(columns, preview.map((row) => columns.map((name) => row[name] ?? ""))),
    ),
  );
  box.hidden = false;
}

function initPredict() {
  buildPredictForm();
  $("#predict-form").addEventListener("submit", (event) => {
    event.preventDefault();
    run(async () => {
      clearNotice();
      const record = collectPredictRecord(event.currentTarget);
      const data = await api("POST", "/predict", { body: { records: [record] } });
      showPrediction(data.predictions[0]);
    });
  });
  $("#csv-form").addEventListener("submit", (event) => {
    event.preventDefault();
    run(async () => {
      clearNotice();
      const form = new FormData(event.currentTarget);
      const data = await api("POST", "/predict-from-csv", { form, query: { limit: 10 } });
      showCsvResult(data);
    });
  });
}

/* ---------- видео ---------- */

const videoState = { page: 1, size: 10, editing: null };

async function loadHooks() {
  const hooks = await api("GET", "/hooks");
  const box = $("#video-hooks");
  if (hooks.length === 0) {
    box.replaceChildren(h("span", { class: "muted" }, "Справочник хуков пуст (запустите ETL)."));
    return;
  }
  box.replaceChildren(
    ...hooks.map((hook) =>
      h("label", {}, h("input", { type: "checkbox", name: "hook", value: hook.code }), hook.title),
    ),
  );
}

async function loadVideos() {
  const filters = $("#video-filters").elements;
  const data = await api("GET", "/videos", {
    query: {
      page: videoState.page,
      size: videoState.size,
      status: filters.status.value,
      video_format: filters.video_format.value.trim(),
      sort_by: filters.sort_by.value,
      order: filters.order.value,
    },
  });
  renderVideos(data.items);
  renderPager($("#videos-pager"), videoState, data.total, loadVideos);
}

function renderVideos(items) {
  const body = $("#videos-body");
  body.replaceChildren();
  for (const video of items) {
    const statusSelect = h(
      "select",
      { "aria-label": `Новый статус видео ${video.id}` },
      STATUSES.map((s) => h("option", { value: s, selected: s === video.status }, s)),
    );
    const actions = h(
      "div",
      { class: "actions" },
      statusSelect,
      h(
        "button",
        {
          type: "button",
          onclick: () =>
            run(async () => {
              await api("PATCH", `/videos/${video.id}/status`, {
                body: { status: statusSelect.value },
              });
              notify(`Статус видео ${video.id} изменён на «${statusSelect.value}»`);
              await loadVideos();
            }),
        },
        "Сменить статус",
      ),
      h(
        "button",
        {
          type: "button",
          onclick: () =>
            run(async () => {
              const result = await api("POST", `/videos/${video.id}/predict`);
              notify(
                `Видео ${video.id}: вероятность ${percent(result.probability)}, рекомендация «${result.recommendation}»`,
              );
            }),
        },
        "Предсказать",
      ),
      h("button", { type: "button", onclick: () => startVideoEdit(video) }, "Изменить"),
      h(
        "button",
        {
          type: "button",
          onclick: () =>
            run(async () => {
              if (!window.confirm(`Удалить видео ${video.id}?`)) {
                return;
              }
              await api("DELETE", `/videos/${video.id}`);
              notify(`Видео ${video.id} удалено`);
              await loadVideos();
            }),
        },
        "Удалить",
      ),
    );
    const row = [
      video.id,
      video.external_id,
      video.creator_id,
      video.product_id,
      video.video_format ?? "",
      video.length_seconds,
      video.published_at ?? "",
      video.status,
      video.viral_flag === null ? "" : video.viral_flag === 1 ? "да" : "нет",
      video.hooks.map((hook) => hook.code).join(", "),
      actions,
    ];
    body.append(h("tr", {}, row.map((cell) => h("td", {}, cell))));
  }
}

function resetVideoForm() {
  const form = $("#video-form");
  form.reset();
  form.elements.external_id.disabled = false;
  form.elements.creator_id.disabled = false;
  form.elements.product_id.disabled = false;
  videoState.editing = null;
  $("#video-form-title").textContent = "Новое видео";
  $("#video-submit").textContent = "Создать";
  $("#video-cancel").hidden = true;
}

function startVideoEdit(video) {
  const form = $("#video-form");
  videoState.editing = video.id;
  form.elements.external_id.value = video.external_id;
  form.elements.creator_id.value = video.creator_id;
  form.elements.product_id.value = video.product_id;
  form.elements.video_format.value = video.video_format ?? "";
  form.elements.title_type.value = video.title_type ?? "";
  form.elements.length_seconds.value = video.length_seconds;
  form.elements.published_at.value = video.published_at ?? "";
  for (const box of form.querySelectorAll('input[name="hook"]')) {
    box.checked = video.hooks.some((hook) => hook.code === box.value);
  }
  form.elements.external_id.disabled = true;
  form.elements.creator_id.disabled = true;
  form.elements.product_id.disabled = true;
  $("#video-form-title").textContent = `Изменение видео ${video.id}`;
  $("#video-submit").textContent = "Сохранить";
  $("#video-cancel").hidden = false;
  form.elements.video_format.focus();
}

function initVideos() {
  $("#video-filters").addEventListener("submit", (event) => {
    event.preventDefault();
    videoState.page = 1;
    run(loadVideos);
  });
  $("#video-cancel").addEventListener("click", resetVideoForm);
  $("#video-form").addEventListener("submit", (event) => {
    event.preventDefault();
    run(async () => {
      const form = event.currentTarget;
      const hookCodes = [...form.querySelectorAll('input[name="hook"]:checked')].map((b) => b.value);
      const common = {
        video_format: textOrUndefined(form.elements.video_format.value),
        title_type: textOrUndefined(form.elements.title_type.value),
        length_seconds: numberOrUndefined(form.elements.length_seconds.value),
        published_at: textOrUndefined(form.elements.published_at.value),
        hook_codes: hookCodes,
      };
      if (videoState.editing === null) {
        const created = await api("POST", "/videos", {
          body: {
            ...common,
            external_id: form.elements.external_id.value.trim(),
            creator_id: numberOrUndefined(form.elements.creator_id.value),
            product_id: numberOrUndefined(form.elements.product_id.value),
          },
        });
        notify(`Видео ${created.id} создано со статусом «${created.status}»`);
      } else {
        await api("PATCH", `/videos/${videoState.editing}`, { body: common });
        notify(`Видео ${videoState.editing} обновлено`);
      }
      resetVideoForm();
      await loadVideos();
    });
  });
}

/* ---------- креаторы ---------- */

const creatorState = { page: 1, size: 10, editing: null };

async function loadCreators() {
  const data = await api("GET", "/creators", {
    query: { page: creatorState.page, size: creatorState.size, sort_by: "id", order: "desc" },
  });
  const body = $("#creators-body");
  body.replaceChildren();
  for (const creator of data.items) {
    const actions = h(
      "div",
      { class: "actions" },
      h("button", { type: "button", onclick: () => startCreatorEdit(creator) }, "Изменить"),
      h(
        "button",
        {
          type: "button",
          onclick: () =>
            run(async () => {
              if (!window.confirm(`Удалить креатора ${creator.id}?`)) {
                return;
              }
              await api("DELETE", `/creators/${creator.id}`);
              notify(`Креатор ${creator.id} удалён`);
              await loadCreators();
            }),
        },
        "Удалить",
      ),
    );
    const row = [
      creator.id,
      creator.external_id,
      creator.tier,
      creator.category,
      creator.country,
      creator.followers,
      creator.engagement_rate,
      actions,
    ];
    body.append(h("tr", {}, row.map((cell) => h("td", {}, cell))));
  }
  renderPager($("#creators-pager"), creatorState, data.total, loadCreators);
}

function resetCreatorForm() {
  const form = $("#creator-form");
  form.reset();
  form.elements.external_id.disabled = false;
  creatorState.editing = null;
  $("#creator-form-title").textContent = "Новый креатор";
  $("#creator-submit").textContent = "Создать";
  $("#creator-cancel").hidden = true;
}

function startCreatorEdit(creator) {
  const form = $("#creator-form");
  creatorState.editing = creator.id;
  form.elements.external_id.value = creator.external_id;
  form.elements.external_id.disabled = true;
  form.elements.tier.value = creator.tier;
  form.elements.category.value = creator.category;
  form.elements.country.value = creator.country;
  form.elements.followers.value = creator.followers;
  form.elements.engagement_rate.value = creator.engagement_rate;
  $("#creator-form-title").textContent = `Изменение креатора ${creator.id}`;
  $("#creator-submit").textContent = "Сохранить";
  $("#creator-cancel").hidden = false;
  form.elements.tier.focus();
}

function initCreators() {
  $("#creator-cancel").addEventListener("click", resetCreatorForm);
  $("#creator-form").addEventListener("submit", (event) => {
    event.preventDefault();
    run(async () => {
      const form = event.currentTarget;
      const common = {
        tier: form.elements.tier.value.trim(),
        category: form.elements.category.value.trim(),
        country: form.elements.country.value.trim(),
        followers: numberOrUndefined(form.elements.followers.value),
        engagement_rate: numberOrUndefined(form.elements.engagement_rate.value),
      };
      if (creatorState.editing === null) {
        const created = await api("POST", "/creators", {
          body: { ...common, external_id: form.elements.external_id.value.trim() },
        });
        notify(`Креатор ${created.id} создан`);
      } else {
        await api("PATCH", `/creators/${creatorState.editing}`, { body: common });
        notify(`Креатор ${creatorState.editing} обновлён`);
      }
      resetCreatorForm();
      creatorState.page = 1;
      await loadCreators();
    });
  });
}

/* ---------- модели ---------- */

async function loadModels() {
  const models = await api("GET", "/models");
  const body = $("#models-body");
  body.replaceChildren();
  for (const model of models) {
    const action = model.is_active
      ? ""
      : h(
          "button",
          {
            type: "button",
            onclick: () =>
              run(async () => {
                await api("POST", `/models/${model.id}/activate`);
                notify(`Модель ${model.id} стала активной`);
                await loadModels();
              }),
          },
          "Сделать активной",
        );
    const row = [
      model.id,
      model.name,
      model.algorithm ?? "",
      model.roc_auc ?? "",
      model.is_active ? "да" : "нет",
      new Date(model.created_at).toLocaleString("ru-RU"),
      action,
    ];
    body.append(h("tr", {}, row.map((cell) => h("td", {}, cell))));
  }
}

function initModels() {
  $("#model-form").addEventListener("submit", (event) => {
    event.preventDefault();
    run(async () => {
      const form = event.currentTarget;
      const result = await api("POST", "/upload-model", { form: new FormData(form) });
      notify(`Модель «${result.model.name}» загружена и активна (${result.model.algorithm})`);
      form.reset();
      await loadModels();
    });
  });
}

/* ---------- аналитика ---------- */

async function loadAnalytics() {
  const [hooks, creators, trend] = await Promise.all([
    api("GET", "/analytics/virality-by-hook"),
    api("GET", "/analytics/top-creators"),
    api("GET", "/analytics/viral-trend"),
  ]);
  $("#an-hooks").replaceChildren(
    table(
      ["Хук", "Видео", "Виральных", "Доля", ""],
      hooks.map((s) => [s.hook_title, s.videos, s.viral_videos, percent(s.viral_rate), bar(s.viral_rate)]),
    ),
  );
  $("#an-creators").replaceChildren(
    table(
      ["Креатор", "Уровень", "Подписчики", "Видео", "Виральных", "Доля", ""],
      creators.map((c) => [
        c.external_id,
        c.tier,
        c.followers,
        c.videos,
        c.viral_videos,
        percent(c.viral_rate),
        bar(c.viral_rate),
      ]),
    ),
  );
  $("#an-trend").replaceChildren(
    table(
      ["Месяц", "Видео", "Виральных", "Доля", ""],
      trend.map((p) => [p.period, p.videos, p.viral_videos, percent(p.viral_rate), bar(p.viral_rate)]),
    ),
  );
}

/* ---------- вкладки и запуск ---------- */

const LOADERS = {
  videos: async () => {
    await loadHooks();
    await loadVideos();
  },
  creators: loadCreators,
  models: loadModels,
  analytics: loadAnalytics,
};

function showTab(name) {
  for (const panel of document.querySelectorAll("[data-panel]")) {
    panel.hidden = panel.dataset.panel !== name;
  }
  for (const button of document.querySelectorAll("nav button")) {
    if (button.dataset.tab === name) {
      button.setAttribute("aria-current", "page");
    } else {
      button.removeAttribute("aria-current");
    }
  }
  clearNotice();
  const loader = LOADERS[name];
  if (loader) {
    run(loader);
  }
}

function buildDatalists() {
  const box = $("#datalists");
  for (const [name, values] of Object.entries(DATALISTS)) {
    box.append(h("datalist", { id: `dl-${name}` }, values.map((value) => h("option", { value }))));
  }
}

function init() {
  buildDatalists();
  initPredict();
  initVideos();
  initCreators();
  initModels();
  for (const button of document.querySelectorAll("nav button")) {
    button.addEventListener("click", () => showTab(button.dataset.tab));
  }
}

init();
