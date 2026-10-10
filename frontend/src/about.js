// About: the first page. Every number and every dot comes from the live API; nothing here is invented.
import { language, pair } from "./i18n.js";
import { escapeHTML as e, routeURL } from "./model.js";
import { icon } from "./components.js";

const BOT = "https://t.me/Srott_bot";
const FEATURED = "412558"; // Behta Lakhi, Harpalpur, Hardoi: the demo village

const c = {
  kicker: ["सरकारी लैब जांच पर आधारित पानी की सूचना", "Lab-confirmed drinking-water alerts"],
  title: ["साफ़ दिखने वाला पानी भी बच्चे को बीमार कर सकता है।", "Clear water can still make a child sick."],
  lead: [
    "जब सरकारी लैब किसी गांव के पीने के पानी को असुरक्षित पाती है, जलसाथी पानी पीने वालों को बताता है कि क्या करना है: हिंदी या English में, लिखकर और बोलकर। और मामला तब तक खुला रखता है, जब तक दोबारा जांच में पानी सुरक्षित साबित न हो।",
    "When a government lab finds a village's drinking water unsafe, JalSaathi tells the people who drink it what to do, in Hindi or English, by text and by voice, and keeps the case open until a re-test proves the water safe.",
  ],
  find: ["अपना गांव खोजें", "Find my village"],
  how: ["यह कैसे काम करता है", "How it works"],
  mapCaption: [
    "हर बिंदु एक गांव है जिसके पीने के पानी की इस साल (2026-27) सरकारी लैब जांच फेल हुई। खोखले बिंदु: अनुमानित जगह।",
    "Each dot is a village whose drinking water failed a government lab test this year (2026-27). Hollow dots: approximate location.",
  ],
  source: ["स्रोत: JJM-WQMIS, जल शक्ति मंत्रालय", "Source: JJM-WQMIS, Ministry of Jal Shakti"],
  whyTitle: ["जांच फेल होना, चेतावनी नहीं है।", "A failed test is not a warning."],
  whyLead: [
    "सरकार पानी की जांच करती है और नतीजा दर्ज करती है। पर वह नतीजा उस परिवार तक नहीं पहुंचता जो वह पानी पी रहा है।",
    "The government tests the water and records the result. The result does not reach the family drinking it.",
  ],
  daysLabel: ["दिन, फेल जांच की औसत उम्र", "days: the median age of the failed tests we found"],
  daysBody: [
    "नतीजा एक सरकारी पोर्टल में दर्ज है। उसमें ऐसा कुछ नहीं जो गांव को बताए या किसी को स्रोत ठीक करने के लिए कहे।",
    "The result sits in a public portal. Nothing in it tells the village, or makes anyone fix the source.",
  ],
  chemLabel: ["रसायन, जिन्हें उबालने से ठीक नहीं किया जा सकता", "are chemicals that boiling can't fix"],
  chemBody: [
    "नाइट्रेट, फ्लोराइड और आर्सेनिक। उबालने से नाइट्रेट और बढ़ जाता है, यानी सबसे आम सलाह नुकसान करती है। हर सूचना में उस दूषक की सही सलाह होती है।",
    "Nitrate, fluoride and arsenic. Boiling concentrates nitrate: the most common advice makes it worse. Every alert carries the right action for its contaminant.",
  ],
  repeatLabel: ["गांव अगले साल फिर उसी जांच में फेल हुए", "villages failed the same test again the next year"],
  repeatBody: [
    "2025-26 में फेल हुए {n} गांवों में से, जबकि इस साल का आधा समय अभी बाकी है। बिना पीछा किए, वही पानी फिर फेल होता है।",
    "Out of {n} that failed in 2025-26, with half of this year still to come. Without follow-up, the same water fails again.",
  ],
  stepsTitle: ["फेल जांच से सुरक्षित पानी तक", "From a failed test to safe water again"],
  steps: [
    [["लैब का नतीजा आता है", "The lab result arrives"],
     ["हम जल शक्ति मंत्रालय का पोर्टल JJM-WQMIS पढ़ते हैं: उत्तर प्रदेश और राजस्थान।", "We read JJM-WQMIS, the Ministry of Jal Shakti's water-quality portal, for Uttar Pradesh and Rajasthan."]],
    [["गांव को सूचना मिलती है", "The village is warned"],
     ["आवाज़ वाले संदेश के साथ हिंदी या English में सूचना, Telegram और इस ऐप पर, उसी दूषक की सलाह के साथ।", "A Hindi or English alert with a voice note reaches the village on Telegram and in this app, with advice for that contaminant."]],
    [["सवालों के जवाब", "Questions get answers"],
     ["लोग बोलकर पूछ सकते हैं, 'क्या मैं इसे उबालकर पी सकता हूं?', और जवाब सिर्फ़ उनके गांव की जांच से बनता है।", "People can ask by voice, 'Can I boil it?', and get a spoken answer drawn only from their village's results."]],
    [["इंजीनियर की ज़िम्मेदारी", "The engineer is accountable"],
     ["ब्लॉक इंजीनियर को समय सीमा के साथ मामला मिलता है। देर हुई तो मामला ज़िले तक जाता है।", "The block engineer gets the case with a deadline. Miss it, and it escalates to the district."]],
    [["सिर्फ़ दोबारा जांच से बंद", "Only a re-test closes it"],
     ["फील्ड किट से अस्थायी रूप से सुरक्षित। केस सिर्फ़ लैब की पास जांच से बंद होता है, इंजीनियर भी इसे नहीं बदल सकता।", "A field kit marks it provisionally safe. Only a passing lab re-test closes the case, a rule even the engineer cannot override."]],
  ],
  placesTitle: ["कहां पानी फेल हुआ", "Where the water failed"],
  placesLead: ["जिन ज़िलों में सबसे ज़्यादा खुले मामले हैं। किसी ज़िले पर टैप करके उसके गांव देखें।", "Districts with the most open cases. Tap one to see its villages."],
  cases: ["मामले", "cases"],
  villagesWord: ["गांव", "villages"],
  techTitle: ["लोगों तक पहुंचने के लिए बना", "Built to reach people, not just servers"],
  techLead: ["AWS पर चलता हुआ सिस्टम, मुंबई (ap-south-1) में। कोई नकली डेटा नहीं।", "A working system on AWS in Mumbai (ap-south-1), on real government data."],
  tech: [
    [["हर मामले का अपना वर्कफ़्लो", "One workflow per village case"], "AWS Step Functions", ["समय सीमा और escalation। एक Distributed Map ने 560 असली मामले दस मिनट में शुरू किए।", "Deadlines and escalation. One Distributed Map started 560 real cases in ten minutes."]],
    [["हिंदी और English में आवाज़", "Voice notes in Hindi and English"], "Amazon Polly", ["जो पढ़ नहीं सकते, वे सुन सकते हैं।", "So people who can't read can listen."]],
    [["बोलकर सवाल", "Questions by voice"], "Amazon Transcribe · Amazon Translate", ["हिंदी आवाज़ से सवाल, सेकंडों में।", "Hindi speech to a question in seconds."]],
    [["डेटा से जांचे गए जवाब", "Answers checked against the data"], "Strands Agents · Amazon Bedrock · Guardrails", ["जवाब सिर्फ़ गांव की जांच से; बाकी हर दावा रोका जाता है।", "Answers come only from the village's results; anything else is blocked."]],
    [["नियम जो कोई नहीं तोड़ सकता", "Rules no one can bend"], "Cedar · Amazon Verified Permissions", ["केस सिर्फ़ लैब पास से बंद; रसायन के लिए 'उबालें' कभी नहीं। हर फैसला AWS पर दर्ज।", "A case closes only on a lab pass; never 'boil' for chemicals. Every decision recorded on AWS."]],
    [["ज़िले तक खबर", "The district hears about it"], "Amazon SES · EventBridge Scheduler", ["देर वाले मामले ज़िला अधिकारी को ईमेल में, सिर्फ़ तब जब कुछ बदला हो।", "Overdue cases are emailed to the district official, only when something changed."]],
    [["फील्ड किट की फ़ोटो पढ़ना", "Reading the field-kit photo"], "Amazon Bedrock · Nova Pro", ["AI सुझाव देता है, फैसला व्यक्ति करता है।", "The AI suggests; the person decides."]],
    [["हर गांव नक्शे पर", "Every village on the map"], "Amazon Location Service", ["नाम और ज़िले से मिलान करके जगह; अंदाज़ा साफ़ बताया जाता है।", "Places checked against name and district; estimates are marked."]],
    [["तेज़, सुरक्षित, हमेशा चालू", "Fast, private, always on"], "Lambda · DynamoDB · S3 + CloudFront · API Gateway · X-Ray · CloudWatch · CDK", ["सर्वरलेस; हर कदम ट्रेस और मापा जाता है।", "Serverless; every step traced and measured."]],
  ],
  techMore: ["आंकड़े और आर्किटेक्चर देखें", "See the numbers and architecture"],
  tryTitle: ["हर स्क्रीन आज़माएं", "Try every screen"],
  tryLead: ["13 डेमो गांवों पर सब कुछ खुला है।", "Everything is open on the 13 demo villages."],
  tryVillage: ["गांव का पेज: बेहटा लखी", "Village page: Behta Lakhi"],
  tryEngineer: ["इंजीनियर स्क्रीन", "Engineer screen"],
  tryRelay: ["स्वास्थ्य कार्यकर्ता: फील्ड जांच", "Health worker: field test"],
  tryOfficials: ["अधिकारी: लाइव फ़ीड", "Officials: live feed"],
  tryBot: ["Telegram बॉट", "Telegram bot"],
  closeTitle: ["इस नक्शे पर कोई गांव है, जिसे यह जानना ज़रूरी है।", "Somewhere on this map is a village that needs to know."],
  telegram: ["Telegram पर जुड़ें", "Join on Telegram"],
  featured: ["आज ध्यान दें", "Act today"],
  labTest: ["लैब जांच", "Lab test"],
};

const T = (key) => pair(c[key]);
const CODES = { ecoli: ["ई. कोलाई", "E. coli"], coliform: ["कोलीफॉर्म", "coliform"], nitrate: ["नाइट्रेट", "nitrate"],
  fluoride: ["फ्लोराइड", "fluoride"], arsenic: ["आर्सेनिक", "arsenic"] };
const CHEMICAL = new Set(["nitrate", "fluoride", "arsenic"]);

export function chemicalShare(stats) {
  const byCode = stats?.open_by_code || {};
  const total = Object.values(byCode).reduce((a, b) => a + b, 0);
  const chem = Object.entries(byCode).reduce((a, [k, v]) => a + (CHEMICAL.has(k) ? v : 0), 0);
  return total ? Math.round((chem / total) * 100) : null;
}

// A small cartographic projection of the real village coordinates (no basemap download on the first page).
function project(villages, width, height, pad = 18) {
  const pts = villages.filter((v) => Number.isFinite(v.lat) && Number.isFinite(v.lon));
  if (!pts.length) return { pts: [], x: () => 0, y: () => 0, bounds: null };
  const lons = pts.map((v) => v.lon), lats = pts.map((v) => v.lat);
  const b = { w: Math.min(...lons) - 0.6, e: Math.max(...lons) + 0.6, s: Math.min(...lats) - 0.6, n: Math.max(...lats) + 0.6 };
  const k = Math.cos((((b.n + b.s) / 2) * Math.PI) / 180);
  const sx = (width - 2 * pad) / ((b.e - b.w) * k), sy = (height - 2 * pad) / (b.n - b.s);
  const s = Math.min(sx, sy);
  const ox = (width - (b.e - b.w) * k * s) / 2, oy = (height - (b.n - b.s) * s) / 2;
  return { pts, bounds: b, x: (lon) => ox + (lon - b.w) * k * s, y: (lat) => oy + (b.n - lat) * s };
}

function spread(key) {
  let h = 0;
  for (const ch of String(key)) h = (h * 31 + ch.charCodeAt(0)) | 0;
  const a = ((h % 360) * Math.PI) / 180, r = 0.05 + ((h >>> 9) % 100) / 1400;
  return [Math.cos(a) * r, Math.sin(a) * r];
}

export function villageMap(villages, featured) {
  const W = 600;
  const geo = villages.filter((v) => Number.isFinite(v.lat) && Number.isFinite(v.lon));
  if (!geo.length) return "";
  const lats = geo.map((v) => v.lat), lons = geo.map((v) => v.lon);
  const k = Math.cos((((Math.max(...lats) + Math.min(...lats)) / 2) * Math.PI) / 180);
  const H = Math.round(((Math.max(...lats) - Math.min(...lats) + 1.2) / ((Math.max(...lons) - Math.min(...lons) + 1.2) * k)) * (W - 36) + 36);
  const { pts, bounds, x, y } = project(villages, W, H);
  if (!pts.length) return "";
  const grid = [];
  for (let lon = Math.ceil(bounds.w); lon <= bounds.e; lon += 2)
    grid.push(`<line x1="${x(lon).toFixed(1)}" y1="0" x2="${x(lon).toFixed(1)}" y2="${H}"/><text x="${(x(lon) + 3).toFixed(1)}" y="${H - 6}">${lon}°E</text>`);
  for (let lat = Math.ceil(bounds.s); lat <= bounds.n; lat += 2)
    grid.push(`<line x1="0" y1="${y(lat).toFixed(1)}" x2="${W}" y2="${y(lat).toFixed(1)}"/><text x="4" y="${(y(lat) - 3).toFixed(1)}">${lat}°N</text>`);
  const states = {};
  for (const v of pts) (states[v.state] ||= []).push(v);
  const labels = Object.entries(states).map(([name, vs]) => {
    const lon = vs.reduce((a, v) => a + v.lon, 0) / vs.length, low = Math.min(...vs.map((v) => v.lat));
    return `<text class="state-label" x="${x(lon).toFixed(1)}" y="${Math.min(H - 20, y(low) + 20).toFixed(1)}" text-anchor="middle">${e(name)}</text>`;
  });
  const dots = pts.map((v, i) => {
    const approx = v.geo_precision !== "village";
    const [dx, dy] = approx ? spread(v.key) : [0, 0];
    const cx = x(v.lon + dx).toFixed(1), cy = y(v.lat + dy).toFixed(1);
    return `<circle class="dot ${e(v.status)}${approx ? " approx" : ""}" cx="${cx}" cy="${cy}" r="${approx ? 3.4 : 4}" style="--d:${(i % 60) * 18}ms"/>`;
  });
  const f = pts.find((v) => v.key === featured);
  const mark = f
    ? `<g class="featured"><circle class="pulse" cx="${x(f.lon).toFixed(1)}" cy="${y(f.lat).toFixed(1)}" r="9"/><circle class="core" cx="${x(f.lon).toFixed(1)}" cy="${y(f.lat).toFixed(1)}" r="6"/></g>`
    : "";
  return `<svg class="living-map" viewBox="0 0 ${W} ${H}" role="img" aria-label="${e(T("mapCaption"))}">
    <g class="graticule">${grid.join("")}</g>${labels.join("")}<g>${dots.join("")}</g>${mark}</svg>`;
}

function featuredCard(f) {
  if (!f) return "";
  const names = (f.parameters || []).map((p) => pair(CODES[p] || [p, p])).join(", ");
  return `<a class="map-card" data-nav href="${routeURL("village", f.key)}">
    <span class="map-card-tag">${icon("alert")} ${e(T("featured"))}</span>
    <strong>${e(f.name)}</strong><small>${e([f.block, f.district].filter(Boolean).join(", "))}</small>
    <span class="map-card-finding">${e(names)}</span>${icon("arrow")}</a>`;
}

export function aboutPage(stats, villages, overview) {
  const f = villages.find((v) => v.key === FEATURED);
  const days = stats?.days_since_test?.median_days;
  const chem = chemicalShare(stats);
  const repeat = stats?.repeat_failures?.totals;
  const districts = (overview?.districts || []).slice().sort((a, b) => b.open - a.open).slice(0, 10);
  const find = "/?find";
  return `
  <section class="about-hero">
    <div class="about-hero-copy">
      <p class="eyebrow">${e(T("kicker"))}</p>
      <h1 class="display">${e(T("title"))}</h1>
      <p class="lede">${e(T("lead"))}</p>
      <div class="hero-actions">
        <a class="button primary large" data-nav href="${find}">${icon("search")} ${e(T("find"))}</a>
        <a class="button quiet large" href="#how">${e(T("how"))}</a>
      </div>
    </div>
    <figure class="about-hero-map">
      ${villageMap(villages, FEATURED)}
      ${featuredCard(f)}
      <figcaption>${e(T("mapCaption"))} <span>${e(T("source"))}${stats?.days_since_test?.as_of ? ` · ${e(stats.days_since_test.as_of)}` : ""}</span></figcaption>
    </figure>
  </section>

  <section class="about-why" aria-labelledby="why-title">
    <header><h2 id="why-title" class="display">${e(T("whyTitle"))}</h2><p>${e(T("whyLead"))}</p></header>
    <div class="why-grid">
      ${days != null ? `<article><b class="figure">${e(days)}</b><h3>${e(T("daysLabel"))}</h3><p>${e(T("daysBody"))}</p></article>` : ""}
      ${chem != null ? `<article><b class="figure">${e(chem)}%</b><h3>${e(T("chemLabel"))}</h3><p>${e(T("chemBody"))}</p></article>` : ""}
      ${repeat ? `<article><b class="figure">${e(repeat.both)}</b><h3>${e(T("repeatLabel"))}</h3><p>${e(T("repeatBody").replace("{n}", repeat.last_year.toLocaleString(language === "hi" ? "hi-IN" : "en-IN")))}</p></article>` : ""}
    </div>
  </section>

  <section class="about-how" id="how" aria-labelledby="how-title">
    <h2 id="how-title" class="display">${e(T("stepsTitle"))}</h2>
    <ol class="route">
      ${c.steps.map(([title, body], i) => `<li><span class="milestone">${i + 1}</span><h3>${e(pair(title))}</h3><p>${e(pair(body))}</p></li>`).join("")}
    </ol>
  </section>

  ${districts.length ? `<section class="about-places" aria-labelledby="places-title">
    <header><h2 id="places-title" class="display">${e(T("placesTitle"))}</h2><p>${e(T("placesLead"))}</p></header>
    <ol class="gazetteer">
      ${districts.map((d, i) => `<li><a data-nav href="/?find&q=${encodeURIComponent(d.district)}"><span class="g-rank">${String(i + 1).padStart(2, "0")}</span><span class="g-name"><strong>${e(d.district)}</strong><small>${e(d.state)}</small></span><span class="g-count"><b>${e(d.open)}</b> ${e(T("cases"))}<small>${e(d.villages)} ${e(T("villagesWord"))}</small></span>${icon("arrow")}</a></li>`).join("")}
    </ol>
  </section>` : ""}

  <section class="about-tech" aria-labelledby="tech-title">
    <header><h2 id="tech-title" class="display">${e(T("techTitle"))}</h2><p>${e(T("techLead"))}</p></header>
    <ul class="tech-grid">
      ${c.tech.map(([title, service, body]) => `<li><h3>${e(pair(title))}</h3><p class="service">${e(service)}</p><p>${e(pair(body))}</p></li>`).join("")}
    </ul>
    <a class="text-link" href="/app/impact">${e(T("techMore"))} ${icon("arrow")}</a>
  </section>

  <section class="about-try" aria-labelledby="try-title">
    <div><h2 id="try-title">${e(T("tryTitle"))}</h2><p>${e(T("tryLead"))}</p></div>
    <ul>
      <li><a data-nav href="${routeURL("village", FEATURED)}">${e(T("tryVillage"))} ${icon("arrow")}</a></li>
      <li><a href="/app/engineer/5037?k=demo">${e(T("tryEngineer"))} ${icon("arrow")}</a></li>
      <li><a href="/app/relay/412558?k=demo">${e(T("tryRelay"))} ${icon("arrow")}</a></li>
      <li><a href="/app/officials">${e(T("tryOfficials"))} ${icon("arrow")}</a></li>
      <li><a href="${BOT}?start=v_${FEATURED}" target="_blank" rel="noopener noreferrer">${e(T("tryBot"))} ${icon("arrow")}</a></li>
    </ul>
  </section>

  <section class="about-close">
    <h2 class="display">${e(T("closeTitle"))}</h2>
    <div class="hero-actions">
      <a class="button primary large" data-nav href="${find}">${icon("search")} ${e(T("find"))}</a>
      <a class="button quiet large on-dark" href="${BOT}" target="_blank" rel="noopener noreferrer">${e(T("telegram"))}</a>
    </div>
  </section>`;
}
