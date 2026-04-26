from __future__ import annotations

from app.services.summarization.types import LanguageAnalysis, OutputLanguage


def build_chunk_prompt(
    output_language: OutputLanguage,
    language_analysis: LanguageAnalysis,
    content_mode: str = "general",
) -> tuple[str, str]:
    if output_language == "ar":
        if content_mode == "meeting":
            transcript_context = "اجتماع أو نقاش عمل"
        elif language_analysis.detected_language == "neutral":
            transcript_context = "محتوى تعليمي أو شرح منظم"
        else:
            transcript_context = "محتوى منطوق عربي عام"

        system_prompt = """
أنت مختص في تلخيص نصوص التفريغ الصوتي العربية أو المختلطة بالعربية والإنجليزية.

مهمتك:
- افهم المعنى المقصود رغم أخطاء STT والتكرار والجمل المكسورة واللهجات والكلمات المختلطة.
- اكتب ملخصًا عربيًا واضحًا وطبيعيًا ومهنيًا.
- لا تخترع أي معلومة غير موجودة في النص.
- لا تضف أسبابًا أو نوايا أو نتائج أو تفسيرات غير مذكورة صراحة.
- إذا كان جزء من النص غير واضح، احذفه أو صغه بحذر شديد دون اختراع.
- لا تحوّل المحتوى إلى نصائح عامة أو عبارات إنشائية.
- أخرج الملخص النهائي فقط.
""".strip()

        user_prompt = f"""
اعتبر النص افتراضيًا {transcript_context} ما لم يتضح بوضوح أنه نوع آخر.

قواعد التلخيص:
- إذا كان المحتوى اجتماعًا أو نقاش عمل بوضوح، استخدم بنية اجتماع والتقط الموضوعات الرئيسية والقرارات والمهام والعوائق والحقائق المهمة.
- إذا لم يكن اجتماعًا، فلا تفرض بنية اجتماع. لخّصه بحسب نوعه الحقيقي مثل: شرح، مقابلة، قصة، مراجعة، أو حديث عام.
- استخدم فقط المعلومات المدعومة مباشرة في النص.
- حافظ على الأسماء والأرقام والنسب والتواريخ والمدد والمسؤوليات عندما تكون واضحة.
- تجنب التكرار والعموميات والعبارات الفضفاضة.
- لا تجعل الملخص قصيرًا جدًا إذا كان النص غنيًا بالمعلومات.
- لا تذكر قسمًا إلا إذا كان النص يدعمه فعلًا.
- لا تخلط الإنجليزية إلا إذا كانت المصطلحات نفسها وردت في النص وكانت مهمة للمعنى.
- لا تجعل كلمات إنجليزية تقنية منفردة مثل onboarding أو caching أو hybrid هي جوهر الملخص ما لم يوضح النص صراحة أنها الموضوع الرئيسي.
- إذا ظهرت مصطلحات إنجليزية تقنية داخل نص عربي، فاذكرها فقط كجزء من المعنى الحقيقي ولا تبنِ الملخص كله حولها.

إذا كان المحتوى اجتماعًا أو نقاش عمل، فاستخدم عند الحاجة فقط:

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

إذا لم يكن المحتوى اجتماعًا، فاستخدم فقط أقسامًا تناسبه مثل:
- **ملخص تنفيذي**
- **الموضوعات الرئيسية**
- **التفاصيل أو الأمثلة المهمة**
- **حقائق مهمة**
""".strip()

        return system_prompt, user_prompt

    transcript_context = (
        "educational content or a structured explanation"
        if language_analysis.detected_language == "neutral"
        else "general spoken content"
    )

    system_prompt = """
You are an expert summarizer of noisy speech-to-text transcripts.

Your job:
- Understand the intended meaning despite STT errors, repetition, broken phrasing, dialect, and mixed Arabic-English wording.
- Write a clear, natural, professional summary.
- Do not invent facts.
- Do not add causes, motives, interpretations, or conclusions not explicitly supported by the transcript.
- If a detail is unclear, omit it or state it cautiously without inventing meaning.
- Do not turn the transcript into generic advice.
- Output only the final summary.
""".strip()

    user_prompt = f"""
Treat the transcript as {transcript_context} unless it is clearly another type of content.

Rules:
- If the content is clearly a meeting or work discussion, use a structured meeting summary and capture main topics, decisions, action items, blockers, and key facts.
- If it is not clearly a meeting, do not force a meeting structure. Summarize according to the real content type.
- Use only claims directly supported by the transcript.
- Preserve names, numbers, percentages, dates, durations, responsibilities, and decisions when they are clear.
- Avoid repetition and vague bullets.
- Do not make the summary too short if the content is information-rich.
- Only include sections supported by the transcript.

If the content is a meeting, you may use:
- **Executive Summary**
- **Main Topics**
- **Decisions / Key Outcomes**
- **Action Items / Next Steps**
- **Blockers / Risks**
- **Key Facts**

If it is not a meeting, use only sections that fit the content, such as:
- **Executive Summary**
- **Main Topics**
- **Important Details or Examples**
- **Key Facts**
""".strip()

    return system_prompt, user_prompt


def build_combine_prompt(output_language: OutputLanguage, content_mode: str = "general") -> tuple[str, str]:
    if output_language == "ar":
        system_prompt = """
أنت تجمع ملخصات جزئية لنص تفريغ صوتي طويل.

- ادمجها في ملخص عربي نهائي واحد واضح ومتماسك.
- أزل التكرار.
- حافظ على التفاصيل المهمة والقرارات والمهام والعوائق والحقائق المهمة عندما تكون موجودة.
- لا تضف أي معلومة جديدة غير موجودة في الملخصات الجزئية.
- لا تفرض بنية اجتماع إذا لم يكن المحتوى اجتماعًا.
- أخرج الملخص النهائي فقط.
""".strip()

        user_prompt = """
ادمج الملخصات الجزئية في ملخص عربي نهائي واحد.

قواعد:
- لا تفقد الأسماء أو الأرقام أو التواريخ أو المدد أو النسب أو العوائق أو القرارات أو المهام عندما تكون مهمة.
- إذا تكررت الفكرة نفسها، وحّدها في نقطة واحدة.
- استخدم فقط الأقسام التي تدعمها المادة.
- إذا لم يكن المحتوى اجتماعًا، فلا تضف أقسام القرارات أو المهام.
- لا تجعل المصطلحات الإنجليزية التقنية هي المحور الرئيسي ما لم تكن كذلك بوضوح في المادة.
""".strip()

        return system_prompt, user_prompt

    system_prompt = """
You are merging partial summaries of a long transcript.

- Create one final clear, cohesive summary.
- Remove repetition.
- Preserve important details, decisions, action items, blockers, and key facts when present.
- Do not add unsupported information.
- Do not force a meeting structure if the content is not a meeting.
- Output only the final summary.
""".strip()

    user_prompt = """
Merge the partial summaries into one final summary.

Rules:
- Do not lose names, numbers, dates, durations, metrics, blockers, decisions, or action items when they matter.
- If the same point appears multiple times, merge it into one clean bullet.
- Use only sections supported by the content.
- If the content is not a meeting, do not add meeting-only sections.
""".strip()

    return system_prompt, user_prompt
