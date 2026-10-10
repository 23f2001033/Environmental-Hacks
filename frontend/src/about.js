// About: the first page. Every number and every dot comes from the live API; nothing here is invented.
import { language, pair } from "./i18n.js";
import { escapeHTML as e, routeURL } from "./model.js";
import { icon } from "./components.js";
import shapes from "./map-shapes.json";

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
  legendUnsafe: ["पानी असुरक्षित", "Unsafe water"],
  legendProvisional: ["फील्ड जांच साफ़, लैब बाकी", "Field test clean, lab pending"],
  legendApprox: ["अनुमानित जगह (ब्लॉक या ज़िला)", "Approximate (block or district)"],
  legendCount: ["गांव नक्शे पर", "villages on the map"],
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

// The map: real state outlines and rivers (Natural Earth, public domain; scripts/build_map_shapes.py), reference
// cities, and one dot per village with a failed test, from the live API. No basemap download on the first page.
const MAP_W = 640;
const fmt = (n) => n.toFixed(1);

function frame() {
  // Fit the two states we cover, with a margin; equirectangular, scaled by cos(latitude).
  const pts = shapes.states.filter((st) => st.focus).flatMap((st) => st.rings.flat());
  const b = { w: Math.min(...pts.map((q) => q[0])) - 0.5, e: Math.max(...pts.map((q) => q[0])) + 0.9,
              s: Math.min(...pts.map((q) => q[1])) - 0.4, n: Math.max(...pts.map((q) => q[1])) + 0.5 };
  const k = Math.cos((((b.n + b.s) / 2) * Math.PI) / 180);
  const sc = MAP_W / ((b.e - b.w) * k);
  const H = Math.round((b.n - b.s) * sc);
  return { H, b, sc, k, x: (lon) => (lon - b.w) * k * sc, y: (lat) => (b.n - lat) * sc };
}

function path(points, f, close) {
  return points.map((q, i) => (i ? "L" : "M") + fmt(f.x(q[0])) + " " + fmt(f.y(q[1]))).join("") + (close ? "Z" : "");
}

function spread(key) {
  let h = 0;
  for (const ch of String(key)) h = (h * 31 + ch.charCodeAt(0)) | 0;
  const a = ((h % 360) * Math.PI) / 180, r = 0.05 + ((h >>> 9) % 100) / 1400;
  return [Math.cos(a) * r, Math.sin(a) * r];
}

const STATE_NAMES = { Rajasthan: ["राजस्थान", "Rajasthan"], "Uttar Pradesh": ["उत्तर प्रदेश", "Uttar Pradesh"] };
const RIVER_NAMES = { Ganges: ["गंगा", "Ganga"], Yamuna: ["यमुना", "Yamuna"], Chambal: ["चंबल", "Chambal"] };

export function villageMap(villages, featured) {
  const f = frame();
  const W = MAP_W, H = f.H;
  const geo = villages.filter((v) => Number.isFinite(v.lat) && Number.isFinite(v.lon));
  const neighbours = shapes.states.filter((st) => !st.focus)
    .map((st) => '<path class="land-other" d="' + st.rings.map((r) => path(r, f, true)).join("") + '"/>').join("");
  const focus = shapes.states.filter((st) => st.focus)
    .map((st) => '<path class="land" d="' + st.rings.map((r) => path(r, f, true)).join("") + '"/>').join("");
  const rivers = shapes.rivers.map((rv) => {
    const major = rv.name === "Ganges" || rv.name === "Yamuna";
    return rv.lines.map((ln) => '<path class="river' + (major ? " major" : "") + '" d="' + path(ln, f, false) + '"/>').join("");
  }).join("");
  // Each river is named at the point nearest an open stretch, clear of the cities and clusters
  const RIVER_AT = { Ganges: [78.7, 28.1], Yamuna: [77.5, 28.15], Chambal: [76.4, 25.9] };
  const riverLabels = shapes.rivers.filter((rv) => RIVER_NAMES[rv.name] && RIVER_AT[rv.name]).map((rv) => {
    const [tx, ty] = RIVER_AT[rv.name];
    const q = rv.lines.flat().reduce((a, p) => (!a || Math.hypot(p[0] - tx, p[1] - ty) < Math.hypot(a[0] - tx, a[1] - ty) ? p : a), null);
    return q ?'<text class="river-label" x="' + fmt(f.x(q[0]) + 6) + '" y="' + fmt(f.y(q[1]) - 6) + '">' + e(pair(RIVER_NAMES[rv.name])) + "</text>" : "";
  }).join("");
  const LABEL_AT = { Rajasthan: [71.9, 27.15], "Uttar Pradesh": [80.7, 24.7] }; // open ground, clear of the clusters
  const stateLabels = shapes.states.filter((st) => st.focus && LABEL_AT[st.name]).map((st) => {
    const [lon, lat] = LABEL_AT[st.name];
    return '<text class="state-label" x="' + fmt(f.x(lon)) + '" y="' + fmt(f.y(lat)) + '" text-anchor="middle">' + e(pair(STATE_NAMES[st.name] || [st.name, st.name])) + "</text>";
  }).join("");
  const shown = shapes.cities.filter((c) => !["Kanpur", "Kota"].includes(c.name)); // too close to Lucknow / a cluster
  const cities = shown.map((c) => {
    const cx = f.x(c.lon), cy = f.y(c.lat);
    return '<rect class="city-mark" x="' + fmt(cx - 3) + '" y="' + fmt(cy - 3) + '" width="6" height="6" transform="rotate(45 ' + fmt(cx) + " " + fmt(cy) + ')"/>';
  }).join("");
  const cityNames = shown.map((c) => '<text class="city-name" x="' + fmt(f.x(c.lon) + 8) + '" y="' + fmt(f.y(c.lat) - 6) + '">' + e(c.name) + "</text>").join("");
  const dots = geo.map((v, i) => {
    const approx = v.geo_precision !== "village";
    const [dx, dy] = approx ? spread(v.key) : [0, 0];
    return '<circle class="dot ' + e(v.status) + (approx ? " approx" : "") + '" cx="' + fmt(f.x(v.lon + dx)) + '" cy="' + fmt(f.y(v.lat + dy)) + '" r="' + (approx ? 3 : 3.6) + '" style="--d:' + (i % 60) * 16 + 'ms"/>';
  }).join("");
  const glow = geo.filter((v) => v.status === "unsafe" && v.geo_precision === "village")
    .map((v) => '<circle cx="' + fmt(f.x(v.lon)) + '" cy="' + fmt(f.y(v.lat)) + '" r="9"/>').join("");
  // Featured village: pulse, a leader line, and a card in the empty north-east corner
  const fv = geo.find((v) => v.key === featured);
  let card = "";
  if (fv) {
    const px = f.x(fv.lon), py = f.y(fv.lat), cw = 196, ch = 92, cx0 = W - cw - 14, cy0 = 16;
    const names = (fv.parameters || []).map((c) => pair(CODES[c] || [c, c])).join(", ");
    card = '<g class="featured"><circle class="pulse" cx="' + fmt(px) + '" cy="' + fmt(py) + '" r="9"/><circle class="core" cx="' + fmt(px) + '" cy="' + fmt(py) + '" r="5.5"/></g>'
      + '<path class="leader" d="M' + fmt(px + 6) + " " + fmt(py - 6) + " C " + fmt(px + 40) + " " + fmt(py - 60) + ", " + fmt(cx0 - 30) + " " + fmt(cy0 + ch + 30) + ", " + fmt(cx0 + 18) + " " + fmt(cy0 + ch) + '"/>'
      + '<a class="svg-card" href="' + routeURL("village", fv.key) + '" data-nav>'
      + '<rect x="' + cx0 + '" y="' + cy0 + '" width="' + cw + '" height="' + ch + '" rx="12"/>'
      + '<text class="tag" x="' + (cx0 + 14) + '" y="' + (cy0 + 22) + '">⚠ ' + e(T("featured")) + "</text>"
      + '<text class="name" x="' + (cx0 + 14) + '" y="' + (cy0 + 44) + '">' + e(fv.name) + "</text>"
      + '<text class="where" x="' + (cx0 + 14) + '" y="' + (cy0 + 62) + '">' + e([fv.block, fv.district].filter(Boolean).join(", ")) + "</text>"
      + '<text class="finding" x="' + (cx0 + 14) + '" y="' + (cy0 + 80) + '">' + e(names) + " ›</text></a>";
  }
  // North arrow and a 100 km scale bar (100 km of longitude at this latitude)
  const kmPx = (100 / (111.32 * f.k)) * f.k * f.sc;
  const furniture = '<g class="north" transform="translate(' + (W - 26) + " " + (H - 64) + ')"><path d="M0 -14 L6 6 L0 2 L-6 6 Z"/><text x="0" y="20" text-anchor="middle">N</text></g>'
    + '<g class="scale" transform="translate(' + fmt(W - 24 - kmPx) + " " + (H - 18) + ')"><path d="M0 0 H' + fmt(kmPx) + " M0 -4 V0 M" + fmt(kmPx) + ' -4 V0"/><text x="' + fmt(kmPx / 2) + '" y="-7" text-anchor="middle">100 km</text></g>';
  return '<svg class="living-map" viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="' + e(T("mapCaption")) + '">'
    + '<defs><filter id="soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4"/></filter></defs>'
    + '<rect class="sea" width="' + W + '" height="' + H + '"/>'
    + "<g>" + neighbours + "</g><g>" + focus + "</g><g>" + rivers + "</g>" + riverLabels + stateLabels
    + '<g class="glow" filter="url(#soft)">' + glow + "</g><g>" + cities + "</g><g>" + dots + "</g><g>" + cityNames + "</g>" + card + furniture + "</svg>";
}

function mapLegend(count) {
  return '<ul class="map-legend">'
    + '<li><i class="key unsafe"></i>' + e(T("legendUnsafe")) + "</li>"
    + '<li><i class="key provisional"></i>' + e(T("legendProvisional")) + "</li>"
    + '<li><i class="key approx"></i>' + e(T("legendApprox")) + "</li>"
    + '<li class="count">' + e(String(count)) + " " + e(T("legendCount")) + "</li></ul>";
}

function featuredCard(f) {
  if (!f) return "";
  const names = (f.parameters || []).map((c) => pair(CODES[c] || [c, c])).join(", ");
  return '<a class="map-card" data-nav href="' + routeURL("village", f.key) + '">'
    + '<span class="map-card-tag">' + icon("alert") + " " + e(T("featured")) + "</span>"
    + "<strong>" + e(f.name) + "</strong><small>" + e([f.block, f.district].filter(Boolean).join(", ")) + "</small>"
    + '<span class="map-card-finding">' + e(names) + "</span>" + icon("arrow") + "</a>";
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
      ${mapLegend(villages.filter((v) => Number.isFinite(v.lat)).length)}
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
