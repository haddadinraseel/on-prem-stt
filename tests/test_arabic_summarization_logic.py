from __future__ import annotations

import unittest

from app.services.summarization.service import transcript_summarizer


ARABIC_MEETING_TEXT = """نص اجتماع: تنسيق استراتيجية المنتج

المدة: ~30 دقيقة
المشاركون:

سارة (المديرة التنفيذية)
عمر (مدير المنتج)
لينا (مديرة الهندسة)
كريم (مدير التسويق)
دانا (العمليات)
[00:00 – 03:00] البداية

سارة: صباح الخير جميعًا، خلينا نبدأ.
عمر: تمام. بشكل عام عندنا ثلاث محاور: تحسين الاحتفاظ بالمستخدمين، إطلاق المساعد الذكي، والتحضير للتوسع في السعودية.

[24:00 – 27:00] اتخاذ القرار
سارة: خلاص، القرار:
نركز على إطلاق المساعد الذكي
نحسن onboarding فورًا
نأجل التوسع التقني في السعودية، بس نكمل الإجراءات

[27:00 – 30:00] الخطوات القادمة
سارة: الخطوات:
عمر: تحديد نطاق الميزة
لينا: تحسين الأداء والسرعة
كريم: خطة إطلاق
دانا: متابعة السعودية
"""

TIMESTAMPED_ARABIC_MEETING_TEXT = """[00:00:00] أحمد: تمام خلينا نبدأ. صباح الخير جميعاً. الهدف من الاجتماع اليوم هو نراجع أداء المنتج خلال الربع الماضي ونشوف شو الخطوات القادمة.
[00:00:15] سارة: بشكل عام عنا نمو 18% بالـ active users مقارنة بالربع اللي قبله.
[00:00:32] سارة: أكثر شي من السعودية، تقريباً 60% من النمو جاي من هناك.
[00:00:50] خالد: تقريباً من 42% لـ 35%.
[00:01:38] أحمد: لازم نبدأ فيه ASAP.
[00:02:20] خالد: وصل تقريباً 22 دولار بعد ما كان 15.
[00:05:15] ليلى: تقريباً 70% جاهزة.
[00:05:35] ليلى: بدنا أسبوعين تقريباً لننضف الداتا.
[00:15:25] أحمد: طيب نبدأ بالفيديو.
[00:18:15] سارة: أحياناً 24 ساعة.
[00:18:30] أحمد: explore it.
[00:22:00] أحمد: خلينا نلخص.
[00:22:05] أحمد: أول شي onboarding لازم يتحسن.
[00:22:10] أحمد: ثاني شي نبدأ A/B testing.
[00:22:15] أحمد: ثالث شي نشتغل على data quality.
[00:22:20] أحمد: ورابع شي نختبر beta للfeature الجديدة.
[00:25:00] أحمد: بالنسبة للتوظيف، نفتح positions.
[00:25:10] أحمد: وموضوع chatbot بدنا research.
"""


class ArabicSummarizationLogicTests(unittest.TestCase):
    def test_detects_arabic_meeting_content_mode(self) -> None:
        self.assertEqual(
            transcript_summarizer._detect_content_mode(ARABIC_MEETING_TEXT, "ar"),
            "meeting",
        )

    def test_extracts_explicit_arabic_decisions_and_actions(self) -> None:
        decisions = transcript_summarizer._extract_explicit_decisions_ar(ARABIC_MEETING_TEXT)
        actions = transcript_summarizer._extract_explicit_actions_ar(ARABIC_MEETING_TEXT)

        self.assertIn("نركز على إطلاق المساعد الذكي", decisions)
        self.assertIn("نحسن onboarding فورًا", decisions)
        self.assertIn("عمر: تحديد نطاق الميزة", actions)
        self.assertIn("دانا: متابعة السعودية", actions)

    def test_meeting_fallback_replaces_suspicious_summary(self) -> None:
        suspicious = """ملخص تنفيذي:
- onboarding
- caching
- hybrid
- RTL"""

        result = transcript_summarizer._apply_arabic_fallback_if_needed(
            suspicious,
            ARABIC_MEETING_TEXT,
            "meeting",
        )

        self.assertIn("**القرارات**", result)
        self.assertIn("نحسن onboarding فورًا", result)
        self.assertIn("**المهام أو الخطوات القادمة**", result)

    def test_general_arabic_fallback_replaces_meta_summary(self) -> None:
        spoken = (
            "في هذا الفيديو نزور عدة أماكن شعبية في بغداد لتجربة أكلات الشارع بميزانية محدودة. "
            "يبدأ الحديث عن سعر السندويشات وطريقة التحضير. "
            "ثم ينتقل المتحدث إلى وصف اللبن العراقي وطعمه."
        )
        meta = "عذرًا، النص الحالي لا يحتوي على معلومات واضحة ويمكنك تقديم نص صحيح للحصول على ملخص."

        result = transcript_summarizer._apply_arabic_fallback_if_needed(meta, spoken, "general")

        self.assertIn("**ملخص تنفيذي**", result)
        self.assertIn("**الموضوعات الرئيسية**", result)
        self.assertIn("أكلات الشارع", result)

    def test_timestamped_arabic_meeting_uses_meeting_mode_and_recap_fallback(self) -> None:
        self.assertEqual(
            transcript_summarizer._detect_content_mode(TIMESTAMPED_ARABIC_MEETING_TEXT, "ar"),
            "meeting",
        )

        recap = transcript_summarizer._extract_recap_actions_ar(TIMESTAMPED_ARABIC_MEETING_TEXT)
        direct = transcript_summarizer._extract_direct_action_statements_ar(TIMESTAMPED_ARABIC_MEETING_TEXT)
        result = transcript_summarizer._apply_arabic_fallback_if_needed(
            "ملخص عام وغير دقيق",
            TIMESTAMPED_ARABIC_MEETING_TEXT,
            "meeting",
        )

        self.assertIn("أول شي onboarding لازم يتحسن.", recap)
        self.assertIn("أحمد: طيب نبدأ بالفيديو.", direct)
        self.assertIn("**القرارات**", result)
        self.assertIn("ثاني شي نبدأ A/B testing.", result)
        self.assertIn("أحمد: وموضوع chatbot بدنا research.", result)
        self.assertIn("نمو المستخدمين النشطين بلغ 18% مقارنة بالربع السابق.", result)


    def test_meeting_minutes_append_only_business_relevant_ten_minute_chunks(self) -> None:
        text = """[00:00:10] أحمد: صباح الخير يا جماعة.
[00:01:00] سارة: خلصنا 70% من الـ backend وفي تأخير بسيط في الـ API integrations.
[00:04:20] محمد: عملنا retry logic وfallback مؤقت.
[00:11:10] أحمد: الجو اليوم جميل كثير.
[00:12:30] ليلى: في تعقيد في onboarding ولازم نبسط الخطوات هذا الأسبوع.
[00:18:40] محمد: الـ latency بين 1.8 و2 ثانية ولازم ننزلها لأقل من ثانية.
[00:24:00] أحمد: demo الأسبوع الجاي يحتاج تجهيز مشترك وأنا point of contact.
"""
        summary = transcript_summarizer._append_meeting_minutes_if_needed(
            "**ملخص تنفيذي**\n- اجتماع متابعة للمشروع.",
            text,
            "ar",
            "meeting",
        )

        self.assertIn("**محضر الاجتماع المختصر**", summary)
        self.assertIn("70% من الـ backend", summary)
        self.assertIn("onboarding", summary)
        self.assertIn("demo الأسبوع الجاي", summary)
        self.assertNotIn("الجو اليوم جميل", summary)


if __name__ == "__main__":
    unittest.main()
