from __future__ import annotations

from app.services.summarization.types import LanguageAnalysis, OutputLanguage


def build_chunk_prompt(output_language: OutputLanguage, language_analysis: LanguageAnalysis) -> tuple[str, str]:
    if output_language == "ar":
        system_prompt = (
            "You summarize noisy Arabic or mixed Arabic-English speech-to-text transcripts. "
            "Infer the intended meaning despite STT mistakes, repetition, broken phrasing, dialect, and code-switching. "
            "Arabic quality matters as much as English quality. Produce natural, useful Modern Standard Arabic unless "
            "preserving a colloquial phrase is clearly necessary for meaning. Do not invent facts. Output only the final summary."
        )
        user_prompt = (
            "تعامل مع النص على أنه في الغالب اجتماع أو مناقشة عمل ما لم يتضح بوضوح أنه نوع آخر من المحتوى. "
            "افهم المعنى المقصود أولاً حتى لو كان النص يحتوي على أخطاء تفريغ أو تكرار أو عبارات مكسورة أو خليطًا "
            "من العربية والإنجليزية. ثم اكتب ملخصًا عربيًا منظمًا ومفيدًا يحافظ على التفاصيل المهمة ولا يكون قصيرًا "
            "بشكل مخل. استخدم عناوين واضحة ونقاطًا مرتبة. ركز أولاً على: الموضوعات الرئيسية، القرارات، الإجراءات "
            "المطلوبة، الخطوات القادمة، المشكلات أو العوائق، الأسباب، الحلول المقترحة، المخاطر، والمفاضلات. "
            "إذا وُجدت أسماء أو فرق أو أدوار مرتبطة بقرار أو مهمة فاذكرها. إذا وُجدت أرقام أو تواريخ أو مقارنات "
            "أو مواعيد أو مقاييس فاحتفظ بها. إذا كان النص تعليميًا أو تدريبيًا بدلاً من كونه اجتماعًا، فاذكر "
            "الإطار أو المنهج أو العملية المشروحة، واذكر الكلمات أو العبارات أو الأمثلة التعليمية فقط عندما تكون "
            "جزءًا أساسيًا من المحتوى. لا تخترع معلومات غير موجودة."
        )
        return system_prompt, user_prompt

    system_prompt = (
        "You summarize noisy English or mixed Arabic-English speech-to-text transcripts. "
        "Infer the intended meaning despite STT mistakes, repetition, broken phrasing, and code-switching. "
        "Do not invent facts. Output only the final summary."
    )
    user_prompt = (
        "Treat the transcript as a meeting or work discussion by default unless it is clearly another type of content. "
        "First infer the intended meaning even if the transcript contains STT mistakes, repetition, broken phrasing, "
        "or mixed Arabic-English fragments. Then write a structured, information-dense summary with clear headers and bullets. "
        "Prioritize: main topics, decisions made, action items, next steps, blockers, causes, proposed solutions, risks, "
        "trade-offs, and unresolved questions. Include owners, teams, or roles when they are tied to decisions or tasks. "
        "Preserve names, numbers, dates, comparisons, deadlines, metrics, and other important facts. "
        "If the transcript is educational instead of a meeting, capture the framework, process, or method being explained, "
        "and include taught terms or sample expressions only when they are central to the content. "
        "Avoid generic summaries and do not invent facts."
    )
    return system_prompt, user_prompt


def build_combine_prompt(output_language: OutputLanguage) -> tuple[str, str]:
    if output_language == "ar":
        system_prompt = (
            "You are combining partial summaries of a noisy Arabic or mixed-language transcript. "
            "Create one cohesive Arabic summary with clear headers and bullets. Remove repetition, preserve important details, "
            "maintain logical flow, and do not invent facts. Output only the final summary."
        )
        user_prompt = (
            "ادمج الملخصات الجزئية في ملخص عربي واحد منظم ومتماسك. أزل التكرار واحتفظ بالتفاصيل المهمة. "
            "احرص على إبقاء القرارات، الإجراءات المطلوبة، الخطوات القادمة، العوائق، المخاطر، الأسئلة المفتوحة، "
            "والأسماء أو الفرق المرتبطة بالمهام إن وجدت. لا تفقد الأرقام أو التواريخ أو الأمثلة أو المواعيد أو "
            "المقاييس المهمة. إذا كان المحتوى تعليميًا بوضوح، فاحتفظ بالعناصر التعليمية الأساسية دون أن تطغى على "
            "جوهر الملخص. لا تخترع معلومات."
        )
        return system_prompt, user_prompt

    system_prompt = (
        "You are combining partial summaries of a noisy speech transcript. "
        "Create one cohesive English summary with clear headers and bullets. Remove repetition, preserve important details, "
        "maintain logical flow, and do not invent facts. Output only the final summary."
    )
    user_prompt = (
        "Merge the partial summaries into one cohesive structured summary. Remove repetition, preserve important details, "
        "and keep logical flow. Do not lose decisions, action items, owners, deadlines, blockers, risks, unresolved questions, "
        "numbers, dates, metrics, or next steps. If the content is clearly educational, keep only the essential teaching details."
    )
    return system_prompt, user_prompt
