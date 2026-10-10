"""Ask JalSaathi: a villager asks about their water by Hindi voice note or text, and gets a checked, spoken answer.

Pipeline (each step is a separate AWS service, and each check can only make the answer safer):
  Telegram voice note --Amazon Transcribe (streaming, hi-IN)--> question text
  --Amazon Translate--> English --Strands agent on Amazon Bedrock (Nova Pro), tools read this village's case--> answer
  --Bedrock Guardrails (grounded in the facts the agent read; no diagnosis; no false all-clear)-->
  --Cedar (never 'boil' when only chemical contamination is open)--> --Amazon Translate--> Hindi --Amazon Polly--> voice.
If any check fails, the person gets the official advice for their village instead of the model's words.
"""

from __future__ import annotations

import logging
import re
import time
import uuid

from . import advice, config, i18n, policy, store, views

log = logging.getLogger()

MODEL_ID = "apac.amazon.nova-pro-v1:0"
SSM_GUARDRAIL = "/jalsaathi/guardrail"
MAX_VOICE_SECONDS = 60
OPEN = store.OPEN_STATUSES

SYSTEM_PROMPT = (
    "You are JalSaathi, a helper for people in Indian villages whose drinking water failed a government lab test. "
    "Always call village_status first; call contaminant_facts when asked why something is harmful or what to do. "
    "Answer in at most three short, plain sentences, using only facts returned by the tools. "
    "Never diagnose illness or name medicines; for illness, say give ORS to children with diarrhoea and see the ASHA worker or a doctor. "
    "Never say the water is safe unless the tools say a lab re-test passed. "
    "The government test is for people's drinking water: for animals, crops or anything else the tools don't cover, "
    "say the test doesn't tell us that and suggest asking the ASHA worker or the block engineer. "
    "Reply with the answer only, no reasoning or tags."
)

THINKING = re.compile(r"<thinking>.*?</thinking>", re.S | re.I)


def clean(text: str) -> str:
    """Drop any reasoning the model emits in <thinking> tags; only the answer itself is checked and sent."""
    return re.sub(r"</?\w+>", "", THINKING.sub("", text)).strip()


# --- facts the agent may use (also the grounding source for the guardrail) ----------------------------------------

def _progress(timeline: list[dict]) -> str:
    kinds = [e.get("kind") for e in timeline or []]
    if "closed" in kinds:
        return "A lab re-test passed and the case is closed."
    if "kit_result" in kinds and "awaiting_lab" in kinds:
        return "The engineer logged a fix and a field-kit re-test was clean; waiting for the lab to confirm. Keep the precautions until then."
    if "fix_logged" in kinds:
        return "The engineer logged a fix; the village has been asked to re-test the water. Keep the precautions until a re-test passes."
    if "escalated" in kinds:
        return "The fix deadline passed and the case was escalated to the district. No fix is recorded yet."
    return "No fix is recorded yet; the block engineer has been asked to act."


def village_facts(key: str) -> tuple[str, list[dict]]:
    """Plain-English facts about one village's water, built from our records (not from the model)."""
    b = views.village_bundle(key)
    if not b:
        return "", []
    v = b["village"]
    cases = [c for c in b["cases"] if c["status"] in OPEN]
    lines = [f"Village: {v['name']} ({v.get('block')} block, {v.get('district')} district, {v.get('state')}).",
             f"Overall status: {b['status_text']['en']}."]
    if not cases:
        lines.append("There is no open water-quality case for this village.")
    for c in cases:
        lines.append(f"Open case: {c['parameter_name']['en']} measured {c['value']} {c.get('unit') or ''} against a safe limit of "
                     f"{c.get('acceptable_limit')} {c.get('unit') or ''} in a government lab test on {(c.get('lab_approval') or '')[:10]}.")
        lines.append("Official advice for it: " + " ".join(c["advice"]["en"]))
        lines.append("Progress: " + _progress(c.get("timeline")))
    lines.append("Rule: a case closes only when a lab re-test passes. Data: JJM-WQMIS (Ministry of Jal Shakti).")
    return "\n".join(lines), cases


def contaminant_code(name: str) -> str:
    """'E. coli' -> 'ecoli', 'total coliform' -> 'coliform', 'Nitrate' -> 'nitrate'."""
    s = re.sub(r"[^a-z]", "", name.lower())
    if "coliform" in s:
        return "coliform"
    if "coli" in s:
        return "ecoli"
    return s


def contaminant_text(code: str) -> str:
    e = advice.entry(code)
    if not e:
        return f"No information about '{code}'."
    kind = {"chemical": "a chemical; boiling does not remove it",
            "microbial": "a germ (bacteria); boiling for one minute kills it"}.get(e["class"], e["class"])
    return (f"{e['name']['en']} is {kind}. What to do: {' '.join(a['en'] for a in e['do_now'])} "
            f"What the engineer should do: {e['engineer_fix']['en']} Sources: {'; '.join(e.get('sources', []))}.")


# --- AWS steps ------------------------------------------------------------------------------------------------------

def translate(text: str, src: str, dst: str) -> str:
    if src == dst or not text.strip():
        return text
    return config.client("translate").translate_text(Text=text[:4500], SourceLanguageCode=src,
                                                      TargetLanguageCode=dst)["TranslatedText"]


def transcribe_ogg(audio: bytes, lang: str = "hi") -> str:
    """Amazon Transcribe streaming on a Telegram voice note (OGG/Opus, 48 kHz)."""
    import asyncio

    from amazon_transcribe.client import TranscribeStreamingClient
    from amazon_transcribe.handlers import TranscriptResultStreamHandler

    parts: list[str] = []

    class Handler(TranscriptResultStreamHandler):
        async def handle_transcript_event(self, event):
            for result in event.transcript.results:
                if not result.is_partial and result.alternatives:
                    parts.append(result.alternatives[0].transcript)

    async def run():
        client = TranscribeStreamingClient(region=config.REGION)
        stream = await client.start_stream_transcription(language_code="hi-IN" if lang == "hi" else "en-IN",
                                                         media_sample_rate_hz=48000, media_encoding="ogg-opus")

        async def send():
            for i in range(0, len(audio), 16000):
                await stream.input_stream.send_audio_event(audio_chunk=audio[i:i + 16000])
            await stream.input_stream.end_stream()

        await asyncio.gather(send(), Handler(stream.output_stream).handle_events())

    asyncio.run(run())
    return " ".join(parts).strip()


def run_agent(question_en: str, facts: str) -> tuple[str, list[str]]:
    """A Strands agent on Bedrock that may only read this village's facts and our advice library."""
    from strands import Agent, tool
    from strands.models import BedrockModel

    used: list[str] = []

    @tool
    def village_status() -> str:
        """Current government water-test results, case progress and official advice for the person's village."""
        used.append(facts)
        return facts

    @tool
    def contaminant_facts(contaminant: str) -> str:
        """Why a contaminant is harmful and what to do about it. contaminant: e.g. 'ecoli', 'nitrate', 'fluoride', 'arsenic'."""
        text = contaminant_text(contaminant_code(contaminant))
        used.append(text)
        return text

    agent = Agent(model=BedrockModel(model_id=MODEL_ID, region_name=config.REGION, temperature=0.2, max_tokens=300,
                                     streaming=False),
                  tools=[village_status, contaminant_facts], system_prompt=SYSTEM_PROMPT, callback_handler=None)
    answer = clean(str(agent(question_en)))
    return answer, used or [facts]


def guardrail_check(question_en: str, grounding: str, answer_en: str) -> dict:
    """Bedrock Guardrails: is the answer grounded in our facts, relevant, and free of diagnosis or false all-clear?"""
    gid, _, version = config.secret(SSM_GUARDRAIL).partition(":")
    resp = config.client("bedrock-runtime").apply_guardrail(
        guardrailIdentifier=gid, guardrailVersion=version or "1", source="OUTPUT", content=[
            {"text": {"text": grounding[:9000], "qualifiers": ["grounding_source"]}},
            {"text": {"text": question_en[:1000], "qualifiers": ["query"]}},
            {"text": {"text": answer_en, "qualifiers": ["guard_content"]}}])
    scores = {f["type"].lower(): round(f["score"], 2) for a in resp.get("assessments", [])
              for f in a.get("contextualGroundingPolicy", {}).get("filters", [])}
    topics = [t["name"] for a in resp.get("assessments", []) for t in a.get("topicPolicy", {}).get("topics", [])
              if t.get("action") == "BLOCKED"]
    return {"passed": resp["action"] == "NONE", **scores, "blocked_topics": topics}


BOIL_ADVICE = re.compile(r"\b(boil (it|the water|this water|your water|drinking water|water)|rolling boil|boil for)\b", re.I)
NEGATION = re.compile(r"\b(not|never|don't|do not|no)\b", re.I)


def advises_boiling(answer_en: str) -> bool:
    """True if any sentence tells the person to boil (not 'do not boil')."""
    return any(BOIL_ADVICE.search(s) and not NEGATION.search(s) for s in re.split(r"(?<=[.!?])\s+", answer_en))


def cedar_check(cases: list[dict], answer_en: str) -> dict:
    """The same Cedar rule as the alerts: no 'boil' advice when every open case is chemical."""
    classes = {c.get("class") for c in cases}
    context = {"contaminant_class": "chemical" if classes and classes <= {"chemical"} else "microbial",
               "actions": ["boil"] if advises_boiling(answer_en) else []}
    d = policy.decide("system", "send_message", (cases[0]["case_id"] if cases else "none"), context)
    return {"allowed": d["allowed"], "reason": d["reason"], "policies": d["policies"]}


def fallback(cases: list[dict], lang: str) -> str:
    """The official advice for the village, once per distinct piece of advice (E. coli and coliform share one)."""
    groups: dict[tuple, list[str]] = {}
    for c in cases:
        groups.setdefault(tuple(c["advice"][lang]), []).append(c["parameter_name"][lang])
    lines = [i18n.t("ask_official", lang)]
    lines += [f"{', '.join(names)}: {' '.join(advice_lines)}" for advice_lines, names in list(groups.items())[:3]]
    lines.append(i18n.t("ask_fallback", lang))
    return "\n".join(lines)


def answer(village_key: str, question: str, lang: str, actor: str = "villager") -> dict:
    """Run the whole pipeline on a text question. Never raises; on any failure the official advice is returned."""
    t0, steps = time.time(), {}
    out = {"village_key": village_key, "question": question, "lang": lang, "fallback": False, "actor": actor}
    facts, cases = village_facts(village_key)
    if not facts:
        return {**out, "answer": i18n.t("village_not_found", lang), "fallback": True}
    try:
        t = time.time(); q_en = translate(question, lang, "en"); steps["translate_in_ms"] = int((time.time() - t) * 1000)
        t = time.time(); a_en, used = run_agent(q_en, facts); steps["agent_ms"] = int((time.time() - t) * 1000)
        t = time.time(); guard = guardrail_check(q_en, "\n".join(used), a_en); steps["guardrail_ms"] = int((time.time() - t) * 1000)
        cedar = cedar_check(cases, a_en)
        out.update(question_en=q_en, answer_en=a_en, guardrail=guard, cedar=cedar)
        if guard["passed"] and cedar["allowed"]:
            t = time.time(); out["answer"] = translate(a_en, "en", lang); steps["translate_out_ms"] = int((time.time() - t) * 1000)
        else:
            out.update(answer=fallback(cases, lang), fallback=True)
    except Exception as exc:  # noqa: BLE001 - the person always gets an answer
        log.exception("assistant failed")
        out.update(answer=fallback(cases, lang), fallback=True, error=str(exc)[:200])
    out["ms"] = {**steps, "total": int((time.time() - t0) * 1000)}
    _record(cases, out)
    return out


def _record(cases: list[dict], out: dict) -> None:
    """The question appears on the case timeline and in the officials' activity feed."""
    if not cases:
        return
    checks = "answered" if not out["fallback"] else "official advice sent (a check failed)"
    try:
        store.add_event(cases[0]["case_id"], "question", actor=out.get("actor", "villager"),
                        note=f"Asked: \"{(out.get('question_en') or out['question'])[:140]}\" · {checks}",
                        result="grounded" if not out["fallback"] else "fallback")
    except Exception:  # noqa: BLE001
        log.exception("could not record question")


def speak(text: str, lang: str) -> str | None:
    from . import voice

    try:
        return voice.public_url(voice.synthesize(re.sub(r"<[^>]+>", "", text), f"answers/{uuid.uuid4().hex}.mp3", lang))
    except Exception:  # noqa: BLE001
        log.exception("polly failed")
        return None


def handle_telegram(event: dict) -> dict:
    """Async worker for the webhook: a voice note or text question from a village relay on Telegram."""
    from . import telegram

    chat, lang, key = event["chat_id"], i18n.norm(event.get("lang")), event["village_key"]
    question = event.get("text") or ""
    if event.get("file_id"):
        try:
            question = transcribe_ogg(telegram.download_file(event["file_id"]), lang)
        except Exception:  # noqa: BLE001
            log.exception("transcribe failed")
        if not question:
            telegram.send_message(chat, i18n.t("ask_not_heard", lang))
            return {"ok": False}
        telegram.send_message(chat, i18n.t("ask_heard", lang, question=question))
    result = answer(key, question, lang, actor=f"tg:{chat}")
    telegram.send_message(chat, ("🤖 " if not result["fallback"] else "📋 ") + result["answer"])
    if url := speak(result["answer"], lang):
        telegram.send_audio(chat, url, title=i18n.t("audio_title", lang))
    return {"ok": True, "fallback": result["fallback"], "ms": result.get("ms")}
