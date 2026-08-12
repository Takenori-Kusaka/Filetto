"""S0-006 基準4: 出力後の字形正規化で混入を 0 にできるか、
そのとき原文の正しい字を壊す件数はいくつか。

正規化の設計:
  対応表の左辺は「CP932 へエンコードできない CJK 漢字」に限定する。
  日本語の文書組版に出現しない字形だけを置換対象にするため、
  置換によって正しい日本語の字が壊れることは構造上ありえない。
  この性質を実測でも確認する(原本テキスト層に対して適用し、変化を数える)。
"""
import json
import re
from pathlib import Path

DEV = Path(
    r"C:\Users\kokor\AppData\Local\Temp\claude\E--Github-Filetto-dev"
    r"\2504b730-c661-4318-ad58-32bb65612f92\scratchpad"
)

# RapidOCR 経路で実測された混入字形に対する対応表。
# 左辺はいずれも CP932 へエンコードできない。
TABLE = {
    "带": "帯",
    "查": "査",
    "笺": "箋",
    "项": "項",
    "閱": "閲",
}


def is_cjk(ch):
    cp = ord(ch)
    return (
        0x4E00 <= cp <= 0x9FFF
        or 0x3400 <= cp <= 0x4DBF
        or 0xF900 <= cp <= 0xFAFF
        or 0x20000 <= cp <= 0x2FA1F
    )


def encodable(ch, enc="cp932"):
    try:
        ch.encode(enc)
        return True
    except UnicodeEncodeError:
        return False


def hits(text):
    return sum(1 for c in text if is_cjk(c) and not encodable(c))


def normalize(text):
    return "".join(TABLE.get(c, c) for c in text)


def main():
    # 対応表の左辺が CP932 外であることを検証する
    bad = [k for k in TABLE if encodable(k)]
    assert not bad, f"対応表の左辺に CP932 内の字がある: {bad}"
    # 右辺が CP932 内(=日本語の字)であることを検証する
    bad_r = [v for v in TABLE.values() if not encodable(v)]
    assert not bad_r, f"対応表の右辺に CP932 外の字がある: {bad_r}"

    result = {"table": TABLE, "routes": {}}

    for name, d in [
        ("rapidocr", DEV / "route-rapidocr-text"),
        ("vlm", DEV / "route-vlm-text"),
    ]:
        before = after = 0
        changed = []
        for f in sorted(d.glob("*.txt")):
            t = f.read_text(encoding="utf-8", errors="replace")
            n = normalize(t)
            b, a = hits(t), hits(n)
            before += b
            after += a
            if b:
                for m in re.finditer(
                    "|".join(map(re.escape, TABLE)), t
                ):
                    s = max(0, m.start() - 12)
                    changed.append(
                        {
                            "file": f.name.replace(".txt", ""),
                            "glyph": m.group(),
                            "to": TABLE[m.group()],
                            "context": t[s : m.end() + 12].replace("\n", " "),
                        }
                    )
        result["routes"][name] = {
            "hits_before": before,
            "hits_after": after,
            "replacements": changed,
        }

    # 副作用の検証: 原本のテキスト層へ同じ正規化を当て、変化した文字数を数える。
    # レガシー .doc 3件は olefile の断片抽出で文字化けしているため、
    # 内訳を分けて記録する。
    legacy = {"inashiki-07.doc", "inashiki-09.doc", "inashiki-10.doc"}
    side_normal = side_legacy = 0
    ctrl_hits_normal = 0
    for f in sorted((DEV / "pure-text").glob("*.txt")):
        stem = f.name.replace(".txt", "")
        t = f.read_text(encoding="utf-8", errors="replace")
        n = normalize(t)
        diff = sum(1 for x, y in zip(t, n) if x != y)
        if stem in legacy:
            side_legacy += diff
        else:
            side_normal += diff
            ctrl_hits_normal += hits(t)
    result["side_effects_on_original_text_layer"] = {
        "changed_chars_excluding_legacy_doc": side_normal,
        "changed_chars_in_legacy_doc": side_legacy,
        "control_hits_excluding_legacy_doc": ctrl_hits_normal,
    }

    Path("glyph-fix.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    for name, r in result["routes"].items():
        print(f"{name}: 混入 {r['hits_before']} -> {r['hits_after']}")
    se = result["side_effects_on_original_text_layer"]
    print(
        f"原本テキスト層への副作用: レガシー.doc を除いて "
        f"{se['changed_chars_excluding_legacy_doc']} 文字が変化"
    )
    print(
        f"原本テキスト層の混入(レガシー.doc を除く): "
        f"{se['control_hits_excluding_legacy_doc']}"
    )
    print("\n置換の実例:")
    for c in result["routes"]["rapidocr"]["replacements"]:
        print(f"  [{c['file']}] {c['glyph']}->{c['to']}  …{c['context']}…")


if __name__ == "__main__":
    main()
