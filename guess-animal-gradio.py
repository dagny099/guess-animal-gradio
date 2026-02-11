"""
Animal Guessing Game V2 (Composite Clues, Improved UX)
--------------------------------------------------------
Improvements in V2:
- Composite clues: Combines multiple data fields into fluent, natural sentences
- Each category has exactly 3 clues (down from 5-8 individual field clues)
- Image only shown after round ends (correct guess or give up)
- Hint/Give up buttons only visible during active gameplay
- All 3 clues shown in final fact card for educational value

Dataset: guess-the-animal-dataset.xlsx with 4 sheets (Dogs/Cats/Horses/Dinosaurs)
"""

import random
import pandas as pd
import gradio as gr

# ----------------------------
# Dataset configuration
# ----------------------------

XLSX_PATH = "guess-the-animal-dataset.xlsx"

SHEETS = {
    "Dogs": "Dog Breed Identification",
    "Cats": "Cat Breed Identification",
    "Horses": "Horse Breed Identification",
    "Dinosaurs": "Dinosaur Species Identification",
}

IMAGE_FIELD = "Example Image"

ANSWER_FIELD = {
    "Dogs": "Breed",
    "Cats": "Breed",
    "Horses": "Breed",
    "Dinosaurs": "Common Name",
}

# Each category now has exactly 3 composite clues
MAX_CLUES = 3

# ----------------------------
# Load data at startup
# ----------------------------

def _load_and_clean_sheet(sheet_name: str) -> pd.DataFrame:
    """Load Excel sheet and remove unnamed columns."""
    df = pd.read_excel(XLSX_PATH, sheet_name=sheet_name)
    df = df.loc[:, ~df.columns.astype(str).str.contains("^Unnamed", na=False)]
    return df

DECKS = {category: _load_and_clean_sheet(sheet) for category, sheet in SHEETS.items()}

# ----------------------------
# Helper utilities
# ----------------------------

def as_msg(role: str, content: str) -> dict:
    """Create Gradio chat message dict."""
    return {"role": role, "content": content}

def safe_str(x) -> str:
    """Convert value to string, handling NaN/None gracefully."""
    if x is None:
        return ""
    try:
        if pd.isna(x):
            return ""
    except Exception:
        pass
    return str(x).strip()

def build_score_text(state: dict | None) -> str:
    """Create HUD-style score display."""
    # score = state.get("score", 0)
    # streak = state.get("streak", 0)
    # cat = state.get("category", "—")
    # return f"**Category:** {cat} &nbsp;&nbsp;|&nbsp;&nbsp; **Score:** {score} &nbsp;&nbsp;|&nbsp;&nbsp; **Streak:** {streak}"
    state = state or {}
    ICON = {"Dogs":"🐶", "Cats":"🐱", "Horses":"🐴", "Dinosaurs":"🦖"}
    cat = state.get("category", "—")
    icon = ICON.get(cat, "🧭")
    score = state.get("score", 0)
    streak = state.get("streak", 0)
    return f"**{icon} {cat}** &nbsp;&nbsp; **⭐ Score:** {score} &nbsp;&nbsp; **🔥 Streak:** {streak}"

def get_example_image(row: dict) -> str | None:
    """Extract image URL from row."""
    url = safe_str(row.get(IMAGE_FIELD, ""))
    return url or None

def generate_image_html(img_url: str | None) -> str:
    """
    Generate HTML img tag for client-side image loading.
    Avoids Gradio's server-side download (which gets 403 from Wikimedia).
    """
    if not img_url:
        return "<p style='color: gray; text-align: center;'>No image available</p>"

    return f"""
    <div style="text-align: center; padding: 10px;">
        <img src="{img_url}"
             style="max-width: 100%; height: auto; max-height: 400px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);"
             alt="Species image"
             onerror="this.onerror=null; this.src=''; this.alt='Image failed to load'; this.style.display='none'; this.nextElementSibling.style.display='block';">
        <p style="display: none; color: gray; margin-top: 10px;">Image failed to load. <a href="{img_url}" target="_blank">View original</a></p>
    </div>
    """

def pick_round_row(category: str) -> dict:
    """Select random row from category deck (must have valid answer)."""
    df = DECKS[category].copy()
    answer_col = ANSWER_FIELD[category]
    df = df.dropna(subset=[answer_col])
    row = df.sample(1).iloc[0].to_dict()
    return row

def make_options(category: str, correct_answer: str, n_options: int = 4) -> list[str]:
    """
    Generate multiple-choice options:
    - 1 correct answer + 3 distractors from same category
    - Shuffled randomly
    - Total of 4 options for clean single-row layout
    """
    df = DECKS[category]
    answer_col = ANSWER_FIELD[category]

    candidates = [safe_str(x) for x in df[answer_col].dropna().tolist()]
    candidates = [c for c in candidates if c and c.lower() != correct_answer.lower()]

    distractors = random.sample(candidates, k=min(n_options - 1, len(candidates)))
    options = [correct_answer] + distractors
    random.shuffle(options)
    return options

# ----------------------------
# Composite clue builder
# ----------------------------

def build_composite_clue(state: dict, clue_number: int) -> str:
    """
    Build a composite clue combining multiple dataset fields into natural language.

    Args:
        state: Current game state containing category and row data
        clue_number: Which clue to build (1, 2, or 3)

    Returns:
        Formatted clue string with category-specific field combinations
    """
    category = state["category"]
    row = state["row"]

    # DOGS: Clue structure
    # 1: Country, Continent, Creation Time, Use
    # 2: Color
    # 3: Personality Traits
    if category == "Dogs":
        if clue_number == 1:
            country = safe_str(row.get("Country", "unknown"))
            continent = safe_str(row.get("Continent", "unknown"))
            creation = safe_str(row.get("Creation Time", "unknown time"))
            use = safe_str(row.get("Use", "various purposes"))
            return f"**Clue 1:** This species was bred in {country}, {continent} during the {creation} for use(s) like {use}"
        elif clue_number == 2:
            color = safe_str(row.get("Color", "various colors"))
            return f"**Clue 2:** This species is often found in colors: {color}"
        elif clue_number == 3:
            personality = safe_str(row.get("Personality Traits", "varied traits"))
            return f"**Clue 3:** Personality traits associated with the species are {personality}"

    # CATS: Clue structure
    # 1: Country, Continent, History
    # 2: Color
    # 3: Personality
    elif category == "Cats":
        if clue_number == 1:
            country = safe_str(row.get("Country", "unknown"))
            continent = safe_str(row.get("Continent", "unknown"))
            history = safe_str(row.get("History", "unknown history"))
            return f"**Clue 1:** This species was bred in {country}, {continent} and a tidbit of its history: {history}"
        elif clue_number == 2:
            color = safe_str(row.get("Color", "various colors"))
            return f"**Clue 2:** This species is often found in colors: {color}"
        elif clue_number == 3:
            personality = safe_str(row.get("Personality", "varied traits"))
            return f"**Clue 3:** Personality traits associated with the species are {personality}"

    # HORSES: Clue structure
    # 1: Country, Continent, Creation, Uses
    # 2: Color, Weight, Height
    # 3: Distinguishing Features
    elif category == "Horses":
        if clue_number == 1:
            country = safe_str(row.get("Country", "unknown"))
            continent = safe_str(row.get("Continent", "unknown"))
            creation = safe_str(row.get("Creation", "unknown time"))
            uses = safe_str(row.get("Uses", "various uses"))
            return f"**Clue 1:** This species was bred in {country}, {continent} around {creation}. Current uses include {uses}"
        elif clue_number == 2:
            color = safe_str(row.get("Color", "various colors"))
            weight = safe_str(row.get("Weight", "unknown weight"))
            height = safe_str(row.get("Height", "unknown height"))
            return f"**Clue 2:** This species is often found in color(s): {color}, and typical weight ranges are {weight} & height ranges are {height}"
        elif clue_number == 3:
            features = safe_str(row.get("Distinguishing Features", "varied features"))
            return f"**Clue 3:** Distinguishing features associated with this species are: {features}"

    # DINOSAURS: Clue structure
    # 1: Locations Found, Eating Habits
    # 2: Rough Size, Clade
    # 3: Social Behavior
    elif category == "Dinosaurs":
        if clue_number == 1:
            locations = safe_str(row.get("Locations Found", "unknown locations"))
            eating = safe_str(row.get("Eating Habits", "unknown diet"))
            return f"**Clue 1:** This species was found in {locations} and is a {eating}"
        elif clue_number == 2:
            size = safe_str(row.get("Rough Size", "unknown size"))
            clade = safe_str(row.get("Clade", "unknown clade"))
            return f"**Clue 2:** This species has size of roughly {size} and in the Clade {clade}"
        elif clue_number == 3:
            social = safe_str(row.get("Social Behavior", "unknown behavior"))
            return f"**Clue 3:** Social behaviors associated are: {social}"

    return "Clue information unavailable"

def next_clue_text(state: dict) -> str:
    """
    Generate and advance to next composite clue.
    Updates state["clue_index"] to track progression.
    """
    i = state.get("clue_index", 0)

    if i >= MAX_CLUES:
        return "No more clues available. You can guess, click **Give up**, or start a **New Round**."

    # Build composite clue (1-indexed for display)
    clue = build_composite_clue(state, i + 1)
    state["clue_index"] = i + 1  # Advance clue counter

    return clue

def build_all_clues_md(state: dict) -> str:
    """
    Build markdown showing all 3 composite clues for the final fact card.
    Shows what the user learned (or could have learned) during the round.
    """
    lines = ["### All Clues"]
    for i in range(MAX_CLUES):
        # Temporarily set clue_index to generate each clue
        clue = build_composite_clue(state, i + 1)
        lines.append(clue)
    return "\n".join(lines)

# def fact_card_md(state: dict) -> str:
#     """
#     Generate final fact card shown after round ends.
#     Includes: Answer, all 3 clues, and image URL.
#     """
#     category = state["category"]
#     row = state["row"]
#     answer_col = ANSWER_FIELD[category]
#     answer = safe_str(row.get(answer_col, ""))

#     lines = [
#         f"### Answer: **{answer}**",
#         "",
#         # build_all_clues_md(state),
#         # ""
#     ]

#     # # Include image URL for reference
#     # img_url = get_example_image(row)
#     # if img_url:
#     #     lines.append(f"**Image URL:** {img_url}")

#     return "\n".join(lines)

def points_for_clues_used(clues_used: int) -> int:
    """
    Score based on efficiency:
    - 1 clue = 3 points
    - 2 clues = 2 points
    - 3 clues = 1 point
    """
    if clues_used <= 1:
        return 3
    if clues_used == 2:
        return 2
    return 1

# ----------------------------
# Game state helpers
# ----------------------------

def is_game_active(state: dict) -> bool:
    """Check if a round is currently in progress."""
    return (state and
            "category" in state and
            not state.get("round_over", False))

# ----------------------------
# Event handlers
# ----------------------------

def start_round(category: str, state: dict | None):
    """
    Initialize a new round:
    - Pick random entry from category
    - Generate 5 answer options
    - Show first clue
    - Hide image (revealed only at end)
    - Show Hint/Give up buttons
    """
    # Preserve session stats
    prev_score = (state or {}).get("score", 0)
    prev_streak = (state or {}).get("streak", 0)

    row = pick_round_row(category)
    correct = safe_str(row.get(ANSWER_FIELD[category], ""))
    options = make_options(category, correct, n_options=4)
    img_url = get_example_image(row)

    state = {
        "category": category,
        "row": row,
        "answer": correct,
        "options": options,
        "clue_index": 0,
        "round_over": False,
        "score": prev_score,
        "streak": prev_streak,
        "img_url": img_url,
    }

    # Get first clue
    clue = next_clue_text(state)

    chat = [
        as_msg(
            "assistant",
            f"Here's your first clue:\n\n{clue}\n\n"
        )
    ]

    # Generate HTML for image (client-side loading avoids 403 errors)
    img_html = generate_image_html(img_url)

    # Return updated UI state
    return (
        state,
        gr.update(value=chat, visible=True),  # Show chat with first clue
        gr.update(choices=options, value=None, visible=True),  # Show options
        build_score_text(state),
        gr.update(value=img_html, visible=False),  # Set image HTML but keep hidden
        gr.update(visible=True),   # Show Hint button
        gr.update(visible=True),   # Show Give up button
        gr.update(visible=True),   # Show Submit button
    )

def give_hint(chat: list, state: dict):
    """Reveal next composite clue."""
    if not is_game_active(state):
        msg = "Pick a category and click **New Round** first." if not state or "category" not in state else "That round is already over. Click **New Round** to play again."
        chat = (chat or []) + [as_msg("assistant", msg)]
        return chat, state

    clue = next_clue_text(state)
    chat = (chat or []) + [as_msg("assistant", clue)]
    return chat, state

def submit_guess(selected: str, chat: list, state: dict):
    """
    Evaluate player's guess:
    - Correct: Award points, end round, show image
    - Wrong: Reset streak, allow retry
    """
    if not is_game_active(state):
        msg = "Pick a category and click **New Round** first." if not state or "category" not in state else "That round is already over. Click **New Round** to play again."
        chat = (chat or []) + [as_msg("assistant", msg)]
        return chat, state, build_score_text(state or {}), gr.update(), gr.update(), gr.update(), gr.update()

    if not selected:
        chat = (chat or []) + [as_msg("assistant", "Choose one of the options first, then click **Submit Guess**.")]
        return chat, state, build_score_text(state), gr.update(), gr.update(), gr.update(), gr.update()

    correct = state["answer"]
    chat = (chat or []) + [as_msg("user", f"My guess: {selected}")]

    # Correct answer
    if safe_str(selected).lower() == safe_str(correct).lower():
        clues_used = max(1, state.get("clue_index", 0))
        pts = points_for_clues_used(clues_used)

        state["score"] = state.get("score", 0) + pts
        state["streak"] = state.get("streak", 0) + 1
        state["round_over"] = True

        chat = chat + [
            as_msg(
                "assistant",
                f"✅ Correct! **{correct}**\n\n"
                f"Points: **+{pts}** (you used {clues_used} clue(s))\n\n"
#                f"{fact_card_md(state)}\n\n"
                "Click **New Round** to play again."
            )
        ]

        # Show image now that round is over
        return (
            chat,
            state,
            build_score_text(state),
            gr.update(visible=True),  # Show image (value already set)
            gr.update(visible=False),  # Hide Hint button
            gr.update(visible=False),  # Hide Give up button
            gr.update(),  # Submit button remains visible
        )

    # Wrong answer
    state["streak"] = 0
    chat = chat + [as_msg("assistant", "Not quite. Click **Hint** for another clue, or guess again.")]
    return chat, state, build_score_text(state), gr.update(), gr.update(), gr.update(), gr.update()

def give_up(chat: list, state: dict):
    """
    Reveal answer without awarding points.
    Shows image and all clues for educational value.
    """
    if not is_game_active(state):
        msg = "Pick a category and click **Start / New Round** first." if not state or "category" not in state else "That round is already over. Click **New Round** to play again."
        chat = (chat or []) + [as_msg("assistant", msg)]
        return chat, state, build_score_text(state or {}), gr.update(), gr.update(), gr.update(), gr.update()

    state["round_over"] = True
    state["streak"] = 0

    chat = (chat or []) + [
        as_msg(
            "assistant",
            f"All good — the answer was **{state['answer']}**.\n\n"
#            f"{fact_card_md(state)}\n\n"
            "Click **New Round** when you're ready."
        )
    ]

    # Show image now that round is over
    return (
        chat,
        state,
        build_score_text(state),
        gr.update(visible=True),  # Show image (value already set)
        gr.update(visible=False),  # Hide Hint button
        gr.update(visible=False),  # Hide Give up button
        gr.update(),  # Submit button remains visible
    )

# ----------------------------
# UI Layout
# ----------------------------

with gr.Blocks(title="Three Clues: Animal ID Game") as demo:
    gr.Markdown(
        "## Name the Species! \n"
    )

    state = gr.State({})

    with gr.Row():
        # Left panel: Controls
        with gr.Column(scale=1, min_width=260):
            category = gr.Dropdown(
                choices=list(SHEETS.keys()),
                value="Dogs",
                label="Category"
            )
            score_md = gr.Markdown("**Category:** — | **Score:** 0 | **Streak:** 0")

            start_btn = gr.Button("New Round", variant="primary")
            hint_btn = gr.Button("Hint", visible=False)  # Hidden until game starts
            giveup_btn = gr.Button("Give up", visible=False)  # Hidden until game starts

            gr.Markdown(
                "**How to play**\n"
                "- Click **New Round** and read Clue 1\n"
                "- Choose the species OR request another clue\n"
                "- Max 3 clues before you must guess or give up\n"
                "- Answer revealed at the end"
            )

        # Right panel: Gameplay area
        with gr.Column(scale=2, min_width=520):
            chat = gr.Chatbot(label="Clues", height=300, autoscroll=True, visible=False)

            options = gr.Radio(
                choices=[],
                label="Choose one:",
                value=None,
                visible=False
            )
            submit_btn = gr.Button("Submit Guess", variant="primary", visible=False, elem_id="submit-guess-btn")

            # Image revealed only after round ends (using HTML for client-side loading)
            image = gr.HTML(
                label="Creature",
                visible=False  # Start hidden
            )

    # ----------------------------
    # Event wiring
    # ----------------------------

    # Start/New Round: Reset game state, show first clue, hide image, show UI components
    start_btn.click(
        fn=start_round,
        inputs=[category, state],
        outputs=[state, chat, options, score_md, image, hint_btn, giveup_btn, submit_btn],
    )

    # Hint: Reveal next clue
    hint_btn.click(
        fn=give_hint,
        inputs=[chat, state],
        outputs=[chat, state],
    )

    # Submit Guess: Check answer, potentially end round and show image
    submit_btn.click(
        fn=submit_guess,
        inputs=[options, chat, state],
        outputs=[chat, state, score_md, image, hint_btn, giveup_btn, submit_btn],
    )

    # Give Up: End round, show answer and image
    giveup_btn.click(
        fn=give_up,
        inputs=[chat, state],
        outputs=[chat, state, score_md, image, hint_btn, giveup_btn, submit_btn],
    )

demo.queue()
demo.launch(css="""
    #submit-guess-btn {
        background: linear-gradient(to right, #10b981, #059669) !important;
        border: none !important;
    }
    #submit-guess-btn:hover {
        background: linear-gradient(to right, #059669, #047857) !important;
    }
""", server_name="0.0.0.0")  # share=True for public access
