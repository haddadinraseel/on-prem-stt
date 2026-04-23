from __future__ import annotations

from app.services.summarization.types import LanguageAnalysis, OutputLanguage


def build_chunk_prompt(
    output_language: OutputLanguage,
    language_analysis: LanguageAnalysis,
) -> tuple[str, str]:
    if output_language == "ar":
        system_prompt = """
أنت مختص في تلخيص نصوص التفريغ الصوتي العربية أو المختلطة بالعربية والإنجليزية.

المطلوب:
- افهم المعنى المقصود رغم أخطاء STT والتكرار والجمل المكسورة واللهجة والكلمات المختلطة.
- اكتب ملخصاً عربياً واضحاً وطبيعياً ومهنياً.
- لا تخترع أي معلومة غير موجودة في النص.
- لا تضف تفسيرات أو نوايا أو أسباباً أو نتائج غير مذكورة صراحة.
- إذا كان جزء من النص غير واضح، احذفه أو صغه بحذر شديد دون اختراع.
- لا تحوّل النص إلى نصائح عامة أو عبارات إنشائية.
- أخرج الملخص النهائي فقط.
""".strip()

        user_prompt = """
لخّص هذا الجزء من التفريغ الصوتي.

قواعد مهمة:
- إذا كان المحتوى اجتماعاً أو نقاش عمل، فاستخدم بنية منظمة والتقط الموضوعات الرئيسية والقرارات والمهام والعوائق والحقائق المهمة.
- إذا لم يكن اجتماعاً، فلا تفرض بنية اجتماع. لخّصه بحسب نوعه الحقيقي.
- استخدم فقط المعلومات المدعومة مباشرة في النص.
- حافظ على الأسماء والأرقام والنسب والتواريخ والمدد والقرارات والمسؤوليات عندما تكون واضحة.
- تجنب التكرار والعموميات.
- لا تجعل الملخص قصيراً جداً إذا كان النص غنيّاً بالمعلومات.

استخدم فقط الأقسام التي يدعمها النص:

**ملخص تنفيذي**
- ...

**الموضوعات الرئيسية**
- ...
- ...

**القرارات أو النتائج المهمة**
- ...
- ...

**المهام أو الخطوات القادمة**
- الاسم أو الفريق: المهمة
- ...

**المخاطر أو العوائق**
- ...
- ...

**حقائق مهمة**
- ...
- ...
""".strip()

        return system_prompt, user_prompt

    system_prompt = """
You are an expert summarizer of noisy speech-to-text transcripts.

Your job:
- Understand the intended meaning despite STT errors, repetition, broken phrasing, dialect, and mixed Arabic-English wording.
- Write a clear, natural, professional summary.
- Do not invent facts.
- Do not add motives, causes, interpretations, or conclusions not explicitly supported by the transcript.
- If a detail is unclear, omit it or state it cautiously without inventing meaning.
- Do not turn the transcript into generic advice.
- Output only the final summary.
""".strip()

    user_prompt = """
Summarize this transcript chunk.

Rules:
- If the content is a meeting or work discussion, use a structured meeting summary and capture main topics, decisions, action items, blockers, and key facts.
- If it is not a meeting, do not force a meeting structure. Summarize according to the real content type.
- Use only claims directly supported by the transcript.
- Preserve names, numbers, percentages, dates, durations, responsibilities, and decisions when they are clear.
- Avoid repetition and vague bullets.
- Do not make the summary too short if the content is information-rich.

Use only the sections supported by the transcript:

**Executive Summary**
- ...

**Main Topics**
- ...
- ...

**Decisions / Key Outcomes**
- ...
- ...

**Action Items / Next Steps**
- Owner or team: task
- ...

**Blockers / Risks**
- ...
- ...

**Key Facts**
- ...
- ...
""".strip()

    return system_prompt, user_prompt


def build_combine_prompt(output_language: OutputLanguage) -> tuple[str, str]:
    if output_language == "ar":
        system_prompt = """
أنت تجمع ملخصات جزئية لنص تفريغ صوتي طويل.

- ادمجها في ملخص عربي نهائي واحد واضح ومتماسك.
- أزل التكرار.
- حافظ على القرارات والمهام والعوائق والحقائق المهمة.
- لا تضف أي معلومة جديدة غير موجودة في الملخصات الجزئية.
- أخرج الملخص النهائي فقط.
""".strip()

        user_prompt = """
ادمج الملخصات الجزئية في ملخص عربي نهائي واحد.

قواعد:
- لا تفقد القرارات أو المهام أو الأسماء أو الأرقام أو التواريخ أو المدد أو النسب أو العوائق.
- إذا تكررت الفكرة نفسها، وحّدها في نقطة واحدة.
- استخدم فقط الأقسام التي تدعمها المادة.
- إذا لم يكن المحتوى اجتماعاً، فلا تفرض بنية اجتماع.
""".strip()

        return system_prompt, user_prompt

    system_prompt = """
You are merging partial summaries of a long transcript.

- Create one final clear, cohesive summary.
- Remove repetition.
- Preserve decisions, action items, blockers, and key facts.
- Do not add unsupported information.
- Output only the final summary.
""".strip()

    user_prompt = """
Merge the partial summaries into one final summary.

Rules:
- Do not lose decisions, action items, owners, numbers, dates, durations, metrics, blockers, or key facts.
- If the same point appears multiple times, merge it into one clean bullet.
- Use only sections supported by the content.
- If the content is not a meeting, do not force a meeting structure.
""".strip()

    return system_prompt, user_prompt
