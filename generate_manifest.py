#generate_manifest.py
#Run: python generate_manifest.py
#Creates data/manifest.json from your existing flat .txt files

import json
from pathlib import Path

DATA_FOLDER = Path("data")

# Maps filename prefix → genre
# Add more rules here if your filenames follow a pattern

PREFIX_TO_GENRE = {
    "letter":              "letter",
    "khat":                "letter",
    "خط":                  "letter",

    "application":         "application",
    "darkhwast":           "application",
    "درخواست":             "application",

    "story":               "story",
    "kahani":              "story",
    "aap_beeti":           "story",
    "کہانی":               "story",

    "dialogue":            "dialogue",
    "mukalma":             "dialogue",
    "مکالمہ":              "dialogue",

    "mcq":                 "mcq",

    "short":               "short_question",
    "sawal":               "short_question",
    "questions":           "short_question",

    "tashreeh_ghazal":     "tashreeh_ghazal",
    "ghazal":              "tashreeh_ghazal",

    "tashreeh_nazam":      "tashreeh_nazam",
    "nazam":               "tashreeh_nazam",

    "nasar":               "nasar_tashreeh",
    "sabaq":               "nasar_tashreeh",

    "khulasa":             "khulasa",
    "summary":             "khulasa",

    "markazi_khyal":             "markazi_khyal",
    "central":             "markazi_khyal",

    "zarbul":              "zarbul_imsal",
    "mahawaray":           "zarbul_imsal",
    "idiom":               "zarbul_imsal",

    "sentence":            "sentence_correction",
    "correction":          "sentence_correction",
}

def infer_genre(filename: str) -> str:
    stem = filename.lower().replace("-", "_")
    for prefix, genre in PREFIX_TO_GENRE.items():
        if stem.startswith(prefix):
            return genre
    return "short_question"  # safe default — change if you prefer another

def make_topic(stem: str) -> str:
    return stem.replace("_", " ").replace("-", " ").title()

manifest = []
for txt_file in sorted(DATA_FOLDER.glob("*.txt")):
    genre = infer_genre(txt_file.name)
    manifest.append({
        "file":           txt_file.name,
        "genre":          genre,
        "sub_type":       txt_file.stem,
        "topic":          make_topic(txt_file.stem),
        "format_section": "full",
        "source":         DATA_FOLDER.name,
        "board":          "lahore",
        "grade":          "9",
    })

out_path = DATA_FOLDER / "manifest.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)

print(f"✅ manifest.json created with {len(manifest)} entries → {out_path}")
print("\nGenres assigned:")
for entry in manifest:
    print(f"  {entry['file']:<40} → {entry['genre']}")