"""Scripted ways to ask a native speaker — the elicitation move-set.

An LLM (or the rule layer) cannot invent facts about a language it has never seen. When the evidence
runs out, the *right* action is not to guess but to ask the speaker a well-formed question. This is the
catalogue of question archetypes a field linguist actually uses; each is a template with slots. In a
ParseGym scenario the correct solution is frequently "invoke question Q with these fillers" — choosing
the question that most cheaply resolves the ambiguity (and that a non-linguist speaker can answer).

Each archetype declares which `Stage` it typically serves and whether it is an EARLY move (bootstrapping
forms/meanings) or a LATE move (fine distinctions once a grammar exists). `options_min/max` bound how many
concrete alternatives the rendered question should offer the speaker (the brief calls for 3–10).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpeakerQuestion:
    id: str
    name: str
    kind: str           # the elicitation move
    template: str       # fill with .render(**slots)
    resolves: str       # the ambiguity it removes
    phase: str          # "early" | "late"
    options_min: int = 0
    options_max: int = 0
    note: str = ""      # how to keep it answerable by a non-linguist

    def render(self, **slots: str) -> str:
        try:
            return self.template.format(**slots)
        except KeyError as exc:
            raise KeyError(f"question {self.id} missing slot {exc}") from exc


# The catalogue. IDs are stable — ParseGym solutions reference them.
QUESTIONS: tuple[SpeakerQuestion, ...] = (
    SpeakerQuestion(
        "elicit_meaning", "Elicit meaning", "open",
        "What does “{form}” mean? Could you use it in a short sentence?",
        "a form with no gloss at all (cold start)", "early",
        note="Ask for a usage sentence too — it often reveals the part of speech.",
    ),
    SpeakerQuestion(
        "elicit_form", "Elicit form", "open",
        "How do you say “{english}” in {language}?",
        "we know the meaning we need but not the word", "early",
    ),
    SpeakerQuestion(
        "meaning_choice", "Choose the meaning", "choice",
        "When you hear “{form}”, does it mean {options}? (or something else?)",
        "a homophone / polysemous form — which sense is meant here", "late",
        options_min=2, options_max=10,
        note="Anchor each option with a tiny example; never offer grammatical jargon.",
    ),
    SpeakerQuestion(
        "grammaticality", "Grammaticality judgement", "yes_no",
        "Can you say “{form}”? Does it sound right / natural to you?",
        "whether a form the grammar generated is actually a real word", "late",
        note="Pair a yes/no form with a real one so 'no' is informative.",
    ),
    SpeakerQuestion(
        "minimal_pair", "Minimal-pair contrast", "contrast",
        "Is there a difference between “{a}” and “{b}”? Do they mean different things, "
        "or are they the same word said two ways?",
        "are two surface forms distinct morphemes, or allomorphs of one", "late",
    ),
    SpeakerQuestion(
        "allomorph_check", "Same word or two words", "yes_no",
        "Are “{a}” and “{b}” two forms of the SAME word, or two DIFFERENT words?",
        "irregular stem allomorphy vs accidental homophony", "late",
        note="Decides whether to add a stem allomorph (one entry) or a second entry.",
    ),
    SpeakerQuestion(
        "paradigm_fill", "Complete the paradigm", "open",
        "Starting from “{lemma}” (meaning ‘{gloss}’), how do you say it when it is {feature}?",
        "a missing or irregular inflected form", "early",
        note="Give the feature in plain terms: 'more than one', 'happened yesterday', 'to you'.",
    ),
    SpeakerQuestion(
        "segmentation", "Is this a separate piece", "yes_no",
        "Inside “{form}”, is “{part}” a piece you can take off and still have a word, "
        "or does it only ever appear stuck on?",
        "morpheme boundary — clitic / affix vs part of the stem", "late",
    ),
    SpeakerQuestion(
        "contrast_function", "What does the extra piece add", "open",
        "What is different in meaning between “{base}” and “{derived}”? What does the extra part do?",
        "the function/gloss of an affix that is attested but unlabelled", "early",
    ),
    SpeakerQuestion(
        "agreement_probe", "Agreement probe", "open",
        "If we change the subject from “{a}” to “{b}”, does “{form}” change? How?",
        "which agreement features (person/number/class) an affix carries", "late",
    ),
    SpeakerQuestion(
        "acceptability_rank", "Rank the alternatives", "choice",
        "Which of these sounds most natural: {options}? Are any of them wrong?",
        "an over-generating grammar produced several forms — which survive", "late",
        options_min=2, options_max=10,
    ),
    SpeakerQuestion(
        "frame_completion", "Fill the frame", "open",
        "Please finish this: “{frame} ___”. What word fits, and why that one?",
        "the category/slot a word must fill in context", "late",
    ),
)

BY_ID = {q.id: q for q in QUESTIONS}


def get(qid: str) -> SpeakerQuestion:
    return BY_ID[qid]
