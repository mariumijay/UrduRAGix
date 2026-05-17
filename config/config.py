RAG_MODES = {
    "paper_mcq": {
        "MAX_CONTEXT_CHUNKS": 6,
        "MAX_TOKENS_PER_CHUNK": 100,
        "MAX_OUTPUT_TOKENS": 1200,
        "TOP_K": 6
    },
    "mcq": {
        "MAX_CONTEXT_CHUNKS": 4,
        "MAX_TOKENS_PER_CHUNK": 300,
        "MAX_OUTPUT_TOKENS": 800,
        "TOP_K": 4
    },
    "one_line": {
        "MAX_CONTEXT_CHUNKS": 3,
        "MAX_TOKENS_PER_CHUNK": 200,
        "MAX_OUTPUT_TOKENS": 300,
        "TOP_K": 3
    },
    "short": {
        "MAX_CONTEXT_CHUNKS": 5,
        "MAX_TOKENS_PER_CHUNK": 500,
        "MAX_OUTPUT_TOKENS": 3045,
        "TOP_K": 5
    },
    "tashreeh": {
        "MAX_CONTEXT_CHUNKS": 5,
        "MAX_TOKENS_PER_CHUNK": 400,
        "MAX_OUTPUT_TOKENS": 2000,
        "TOP_K": 5
    },
    "khulasa": {
        "MAX_CONTEXT_CHUNKS": 6,
        "MAX_TOKENS_PER_CHUNK": 450,
        "MAX_OUTPUT_TOKENS": 2500,
        "TOP_K": 6
    },
    "markazi": {
        "MAX_CONTEXT_CHUNKS": 5,
        "MAX_TOKENS_PER_CHUNK": 400,
        "MAX_OUTPUT_TOKENS": 600,
        "TOP_K": 5
    },
    "application": {
        "MAX_CONTEXT_CHUNKS": 4,
        "MAX_TOKENS_PER_CHUNK": 350,
        "MAX_OUTPUT_TOKENS": 1200,
        "TOP_K": 4
    },
    "letter": { 
        "MAX_CONTEXT_CHUNKS": 4,
        "MAX_TOKENS_PER_CHUNK": 350,
        "MAX_OUTPUT_TOKENS": 1200,
        "TOP_K": 4
    },
    "story":  { 
        "MAX_CONTEXT_CHUNKS": 4,
        "MAX_TOKENS_PER_CHUNK": 350,
        "MAX_OUTPUT_TOKENS": 1500,
        "TOP_K": 4 
        },
    "dialogue": { 
        "MAX_CONTEXT_CHUNKS": 4,
        "MAX_TOKENS_PER_CHUNK": 350,
        "MAX_OUTPUT_TOKENS": 1500,
        "TOP_K": 4
    }
}

CHUNK_OVERLAP = 100

GENRE_TO_MODEL: dict[str, str] = {
    # FAST
    "mcq":                 "llama-3.1-8b-instant",
    "word_meanings":       "llama-3.1-8b-instant",
    "sentence_correction": "llama-3.1-8b-instant",
    "zarbul_imsal":        "llama-3.1-8b-instant",

    # BALANCED
    "short_question":      "qwen/qwen3-32b",
    "general_qa":          "qwen/qwen3-32b",
    "comprehension":       "qwen/qwen3-32b",
    "translation":         "qwen/qwen3-32b",
    "tashreeh_ghazal":     "qwen/qwen3-32b",
    "tashreeh_nazam":      "qwen/qwen3-32b",
    "nasar_tashreeh":      "qwen/qwen3-32b",
    "poem_explanation":    "qwen/qwen3-32b",
    "khulasa":             "qwen/qwen3-32b",
    "markazi_khyal":       "qwen/qwen3-32b",
    "application":         "qwen/qwen3-32b",
    "letter":              "qwen/qwen3-32b",
    "story":               "qwen/qwen3-32b",
    "dialogue":            "qwen/qwen3-32b",

    # STRONG (default for unmatched)
    "paper":               "llama-3.3-70b-versatile",
}

DEFAULT_MODEL = "qwen/qwen3-32b"

GENRE_TO_MODE: dict[str, str] = {
    # one-line / objective
    "mcq":                 "mcq",
    "word_meanings":       "mcq",
    "sentence_correction": "one_line",
    "zarbul_imsal":        "one_line",

    # short responses
    "short_question":      "short",
    "general_qa":          "short",
    "comprehension":       "short",
    "translation":         "short",

    # explanatory
    "tashreeh_ghazal":     "tashreeh",
    "tashreeh_nazam":      "tashreeh",
    "nasar_tashreeh":      "tashreeh",
    "poem_explanation":    "tashreeh",

    # summaries / longer structured responses
    "khulasa":             "khulasa",

    # conceptual / moral
    "markazi":       "markazi",

    # formatted writing tasks
    "application":         "application",
    "letter":              "letter",
    "story":               "story",
    "dialogue":            "dialogue",
}