"""Custom one-off exercise builder and active exercise LLM ideation prompts.

Layer 2 Domain module. Pure business logic adhering to EXERCISE-10 and EXERCISE-11.
"""

from iw.contracts.exercises import CustomExerciseInput, ExercisePrompt
from iw.contracts.store import StoreProtocol
from iw.domain.exercises.models import ExerciseType


def _build_custom_triad(inp: CustomExerciseInput) -> ExercisePrompt:
    """Build a custom 3-Word Triad prompt from three words or comma/bullet text (EXERCISE-10)."""
    words = [w.strip() for w in (inp.word_1, inp.word_2, inp.word_3) if w.strip()]
    if not words and inp.custom_text.strip():
        raw = inp.custom_text.replace("•", ",").replace("|", ",")
        words = [p.strip() for p in raw.split(",") if p.strip()]
        if len(words) == 1 and " " in words[0]:
            words = [p.strip() for p in words[0].split() if p.strip()]
    prompt_text = " • ".join(words) if words else "custom • triad • spark"
    return ExercisePrompt(
        exercise_type=ExerciseType.TRIAD.value,
        title="3-Word Triad (Custom)",
        prompt_text=prompt_text,
        sub_text="Riff on novel connections: what hybrid mechanism, product, or scenario connects these three?",
        categories=["custom", "triad"],
        metadata={"words": ", ".join(words), "custom": "true"},
    )


def _build_custom_what_if(inp: CustomExerciseInput) -> ExercisePrompt:
    """Build a custom Cross-Domain What-If prompt (EXERCISE-10)."""
    ent = inp.entity.strip()
    sys_name = inp.system.strip().rstrip("?")
    if ent and sys_name:
        prompt_text = f"What if {ent} ran {sys_name}?"
    else:
        prompt_text = inp.custom_text.strip() or "What if NASA JPL ran a neighborhood bakery?"
    return ExercisePrompt(
        exercise_type=ExerciseType.WHAT_IF.value,
        title="Cross-Domain 'What If?' (Custom)",
        prompt_text=prompt_text,
        sub_text="If you transplanted their core culture, rules, and obsessions into this system, what would happen?",
        categories=["custom", "mashup", "transfer"],
        metadata={"entity": ent, "system": sys_name, "custom": "true"},
    )


def _build_custom_vault_hybrid(
    inp: CustomExerciseInput,
    store: StoreProtocol | None,
) -> ExercisePrompt:
    """Build a custom Vault Wildcard prompt pairing a node or concept with a wildcard noun (EXERCISE-10)."""
    node_id = inp.node_id.strip().upper()
    wildcard = inp.wildcard.strip() or "flywheel"
    node_title = inp.custom_title.strip() or node_id or "Custom Idea"
    cats = ["custom", "vault"]
    if store is not None and node_id:
        node = store.get_node(node_id)
        if node is not None:
            node_title = node.title
            cats.extend([node.type, node.domain])
    if inp.custom_text.strip() and not inp.node_id.strip() and not inp.wildcard.strip():
        prompt_text = inp.custom_text.strip()
    else:
        prompt_text = f"'{node_title}'  ✕  [{wildcard.upper()}]"
    label = f"Vault Wildcard: {node_id} (Custom)" if node_id else "Vault Wildcard (Custom)"
    return ExercisePrompt(
        exercise_type=ExerciseType.VAULT_HYBRID.value,
        title=label,
        prompt_text=prompt_text,
        sub_text=f"Force-multiply '{node_title}' with '{wildcard}'. How does it transform the core mechanism?",
        categories=cats,
        metadata={"node_id": node_id, "node_title": node_title, "wildcard": wildcard, "custom": "true"},
    )


def _build_custom_paradox(inp: CustomExerciseInput) -> ExercisePrompt:
    """Build a custom Paradoxical Constraint prompt (EXERCISE-10)."""
    text = inp.custom_text.strip() or "A tool stripped of its primary affordance"
    return ExercisePrompt(
        exercise_type=ExerciseType.PARADOX.value,
        title="Paradoxical Constraint (Custom)",
        prompt_text=text,
        sub_text="What does it do instead? What surprising new problem is this uniquely suited to solve?",
        categories=["custom", "constraint", "paradox"],
        metadata={"custom": "true"},
    )


def _build_custom_biomimicry(inp: CustomExerciseInput) -> ExercisePrompt:
    """Build a custom Biomimicry Spark prompt (EXERCISE-10)."""
    org = inp.organism.strip() or "Organism"
    text = inp.custom_text.strip() or f"Biological adaptation inspired by {org}"
    return ExercisePrompt(
        exercise_type=ExerciseType.BIOMIMICRY.value,
        title=f"Biomimicry: {org} (Custom)",
        prompt_text=text,
        sub_text="How can you translate this biological mechanism into a physical device, workflow, or architecture?",
        categories=["custom", "biomimicry", org.lower()],
        metadata={"organism": org, "custom": "true"},
    )


def _build_custom_assumption(inp: CustomExerciseInput) -> ExercisePrompt:
    """Build a custom Assumption Inversion prompt (EXERCISE-10)."""
    std = inp.standard_assumption.strip()
    inv = inp.inversion.strip()
    if std and inv:
        text = f"{std}\n➔ Inversion: {inv}"
    elif inv and not std:
        text = f"➔ Inversion: {inv}"
    else:
        text = inp.custom_text.strip() or std
    domain_label = inp.custom_title.strip() or "Custom"
    return ExercisePrompt(
        exercise_type=ExerciseType.ASSUMPTION.value,
        title=f"Inversion: {domain_label}",
        prompt_text=text,
        sub_text="How would you design a useful system or product around this reversed assumption?",
        categories=["custom", "inversion"],
        metadata={"standard_assumption": std, "inversion": inv, "custom": "true"},
    )


def _build_custom_freeform(inp: CustomExerciseInput) -> ExercisePrompt:
    """Build a freeform custom exercise prompt (EXERCISE-10)."""
    title = inp.custom_title.strip() or "Custom Exercise Prompt"
    text = inp.custom_text.strip() or "Custom creative starting point"
    return ExercisePrompt(
        exercise_type=inp.exercise_type.strip().lower() or ExerciseType.SURPRISE.value,
        title=title,
        prompt_text=text,
        sub_text="Explore novel mechanisms, products, or unexpected angles sparked by this starting point.",
        categories=["custom"],
        metadata={"custom": "true"},
    )


def build_custom_exercise_prompt(
    inp: CustomExerciseInput,
    store: StoreProtocol | None = None,
) -> ExercisePrompt:
    """Construct a one-off ExercisePrompt from user-supplied custom inputs (EXERCISE-10)."""
    t = inp.exercise_type.strip().lower()
    if t == ExerciseType.TRIAD.value or (inp.word_1.strip() or inp.word_2.strip() or inp.word_3.strip()):
        return _build_custom_triad(inp)
    if t == ExerciseType.WHAT_IF.value and (inp.entity.strip() or inp.system.strip() or inp.custom_text.strip()):
        return _build_custom_what_if(inp)
    if t == ExerciseType.VAULT_HYBRID.value and (inp.node_id.strip() or inp.wildcard.strip() or inp.custom_text.strip()):
        return _build_custom_vault_hybrid(inp, store)
    if t == ExerciseType.PARADOX.value and inp.custom_text.strip():
        return _build_custom_paradox(inp)
    if t == ExerciseType.BIOMIMICRY.value and (inp.organism.strip() or inp.custom_text.strip()):
        return _build_custom_biomimicry(inp)
    if t == ExerciseType.ASSUMPTION.value and (inp.standard_assumption.strip() or inp.inversion.strip() or inp.custom_text.strip()):
        return _build_custom_assumption(inp)
    return _build_custom_freeform(inp)


def build_ideation_llm_prompt(prompt: ExercisePrompt) -> str:
    """Build a ready-to-copy LLM brainstorming prompt for the active exercise (EXERCISE-11)."""
    return (
        f"You are an inventive engineering and product design collaborator.\n"
        f"We are running a creative lateral-thinking exercise:\n\n"
        f"Exercise Type: {prompt.title}\n"
        f"Starting Prompt: {prompt.prompt_text}\n"
        f"Challenge: {prompt.sub_text}\n\n"
        f"Please generate 5 distinct, concrete, non-obvious product, tool, or mechanism concepts "
        f"sparked by this starting point.\n"
        f"For each concept, provide:\n"
        f"1. **Concept Name & One-Line Hook**\n"
        f"2. **Core Mechanism**: How it physically or logically works and combines the prompt elements.\n"
        f"3. **Surprising Use Case**: Who needs this and what real friction it solves.\n"
        f"4. **Key Engineering Risk**: The hardest technical assumption to test first."
    )
