from __future__ import annotations

import re


class ArabicScriptTransliterator:
    _digraph_map = {
        "tion": "شن",
        "ture": "تشر",
        "igh": "اي",
        "ph": "ف",
        "sh": "ش",
        "ch": "تش",
        "th": "ث",
        "gh": "غ",
        "kh": "خ",
        "ng": "نج",
        "qu": "كو",
        "ck": "ك",
        "ee": "ي",
        "oo": "و",
        "ou": "او",
        "ai": "اي",
        "ay": "اي",
        "ea": "ي",
        "ie": "ي",
        "oa": "و",
        "ow": "او",
    }

    _char_map = {
        "a": "ا",
        "b": "ب",
        "c": "ك",
        "d": "د",
        "e": "ي",
        "f": "ف",
        "g": "ج",
        "h": "ه",
        "i": "ي",
        "j": "ج",
        "k": "ك",
        "l": "ل",
        "m": "م",
        "n": "ن",
        "o": "و",
        "p": "ب",
        "q": "ق",
        "r": "ر",
        "s": "س",
        "t": "ت",
        "u": "و",
        "v": "ف",
        "w": "و",
        "x": "كس",
        "y": "ي",
        "z": "ز",
    }

    _digit_map = {
        "0": "٠",
        "1": "١",
        "2": "٢",
        "3": "٣",
        "4": "٤",
        "5": "٥",
        "6": "٦",
        "7": "٧",
        "8": "٨",
        "9": "٩",
    }

    _latin_pattern = re.compile(r"[A-Za-z0-9][A-Za-z0-9'._-]*")

    def transliterate_token(self, token: str) -> str:
        lower_token = token.lower()
        output: list[str] = []
        index = 0

        while index < len(lower_token):
            matched = False

            for size in (4, 3, 2):
                segment = lower_token[index:index + size]
                if segment in self._digraph_map:
                    output.append(self._digraph_map[segment])
                    index += size
                    matched = True
                    break

            if matched:
                continue

            char = lower_token[index]

            if char in self._digit_map:
                output.append(self._digit_map[char])
            elif char in self._char_map:
                output.append(self._char_map[char])
            elif char in {"'", "_", "-", "."}:
                output.append("")
            else:
                output.append(char)

            index += 1

        result = "".join(output)
        result = re.sub(r"(.)\1{2,}", r"\1\1", result)
        return result or token

    def transform_text(self, text: str) -> str:
        return self._latin_pattern.sub(lambda match: self.transliterate_token(match.group(0)), text)

    def transform_text_if_arabic_context(self, text: str, primary_language: str | None) -> str:
        """
        Transliterate Latin-script tokens only when the overall audio is primarily Arabic.
        This preserves English-only files as English.
        """
        if primary_language != "ar":
            return text
        return self.transform_text(text)


transliteration_service = ArabicScriptTransliterator()