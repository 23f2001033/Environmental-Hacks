import QRCode from "qrcode";
import { escapeHTML as e, safeURL, formatDate } from "./model.js";
import { t, language, local } from "./i18n.js";
import { icon } from "./components.js";

export async function showPoster(bundle, demo) {
  const dialog = document.querySelector("#poster-dialog");
  const status = ["unsafe", "provisional", "safe_again", "unknown"].includes(
    bundle.status,
  )
    ? bundle.status
    : "unknown";
  const active = (bundle.cases || []).filter((c) => c.status !== "CLOSED");
  dialog.innerHTML = `<div class="dialog-toolbar"><h2 id="poster-heading">${e(t("poster"))}</h2><button class="icon-button" data-close aria-label="${e(t("close"))}">${icon("x")}</button></div>
    <article class="print-sheet ${status}"><div class="poster-brand">${icon("drop")}${e(t("brand"))}</div>${demo ? `<p class="poster-preview">${e(t("preview"))}</p>` : ""}<h1>${e(bundle.village.name)}</h1><p>${e([bundle.village.block, bundle.village.district].filter(Boolean).join(", "))}</p><h2>${e(t(status))}</h2><p>${e(t(status + "Note"))}</p>
    ${active.map((c) => `<section><h3>${e(local(c.parameter_name) || c.parameter)}</h3><p>${e(t("measured"))}: ${e(c.value ?? "—")} ${e(c.unit)} | ${e(t("limit"))}: ${e(c.acceptable_limit ?? "—")} ${e(c.unit)}<br>${e(t("labDate"))}: ${e(formatDate(c.lab_approval, language))}</p><ul>${(c.advice?.[language] || []).map((a) => `<li>${e(a)}</li>`).join("")}</ul></section>`).join("")}
    <div class="poster-join"><div id="poster-qr"></div><div><strong>${e(t("qrNote"))}</strong><p class="poster-url">${e(safeURL(bundle.links?.telegram_join))}</p></div></div><p class="poster-provenance">${e(t("record"))}<br>${e(t("asOf"))}: ${e(formatDate(bundle.data_as_of, language))}<br>${e(t("disclaimer"))}</p></article>
    <div class="dialog-actions"><button class="button secondary" data-close>${e(t("close"))}</button><button class="button primary" id="confirm-print" disabled>${icon("print")}${e(t("print"))}</button></div>`;
  dialog
    .querySelectorAll("[data-close]")
    .forEach((button) => (button.onclick = () => dialog.close()));
  dialog.showModal();
  document.body.classList.add("poster-open");
  dialog.onclose = () => document.body.classList.remove("poster-open");
  const container = dialog.querySelector("#poster-qr");
  try {
    const url = safeURL(bundle.links?.telegram_join);
    if (!url) throw new Error("No link");
    const image = document.createElement("img");
    image.alt = t("qrNote");
    image.width = 144;
    image.height = 144;
    image.src = await QRCode.toDataURL(url, {
      errorCorrectionLevel: "M",
      width: 288,
      margin: 4,
    });
    await image.decode();
    container.append(image);
  } catch {
    container.textContent = t("qrMissing");
  }
  const print = dialog.querySelector("#confirm-print");
  print.disabled = false;
  print.onclick = () => window.print();
}
