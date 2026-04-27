print("✅ BOT FILE LOADED: green_nudge/tests.py")

from otree.api import *
import time
import random


doc = """
Green nudge (RSE) – lab-style:
- 10 conditions: 5 messages × 2 frames
- 6 repeated purchase decisions
- packaged is default
- global time limit
- instructions + comprehension quiz + demographics
"""


class C(BaseConstants):
    NAME_IN_URL = 'green_nudge'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 6
    TOTAL_TIME_SECONDS = 60

    # message types (between-subject)
    MSG_NEUTRAL = "neutral"
    MSG_SOC_DESC = "soc_desc"
    MSG_SOC_INJ = "soc_inj"
    MSG_ECO_DESC = "eco_desc"
    MSG_ECO_INJ = "eco_inj"

    MESSAGE_TYPES = [MSG_NEUTRAL, MSG_SOC_DESC, MSG_SOC_INJ, MSG_ECO_DESC, MSG_ECO_INJ]
    GOAL_FRAMES = ["individual", "collective"]

    MESSAGES = {
        MSG_NEUTRAL: "",
        MSG_SOC_DESC: "80 % des clients choisissent la version en vrac pour ce produit.",
        MSG_SOC_INJ: "La majorité des clients pensent qu’il est préférable de choisir la version en vrac.",
        MSG_ECO_DESC: "Choisir la version en vrac permet d’éviter environ 50 g de plastique.",
        MSG_ECO_INJ: "Pour réduire les déchets plastiques et protéger l’environnement, il est important de choisir la version en vrac.",
    }

    PRODUCTS = ["Pâtes", "Riz", "Lentilles", "Café", "Céréales", "Amandes"]

    PACK = "pack"
    BULK = "bulk"
    CHOICES = [(PACK, "Emballé"), (BULK, "Vrac")]

    # quiz answers
    QUIZ_DEFAULT_CORRECT = 2  # 1=Vrac, 2=Emballé
    QUIZ_TIME_CORRECT = TOTAL_TIME_SECONDS


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    # stored each round (but assigned from participant vars)
    message_type = models.StringField()
    goal_frame = models.StringField()

    # decision each round: set default to packaged to avoid None errors
    choice = models.StringField(choices=C.CHOICES, initial=C.PACK)

    timed_out = models.BooleanField(initial=False)

    submitted = models.BooleanField(initial=False)

    # quiz (round 1 only)
    quiz_default = models.IntegerField(
        choices=[(1, "Le vrac"), (2, "L’option emballée"), (3, "Les deux"), (4, "Aucune")],
        label="Q1. Quelle option est sélectionnée par défaut pour chaque produit ?",
        blank=True,
    )
    quiz_time = models.IntegerField(
        choices=[(0, "Pas de limite"), (30, "30 secondes"), (60, "60 secondes"), (180, "3 minutes")],
        label="Q2. Combien de temps avez-vous pour effectuer l’ensemble de vos choix ?",
        blank=True,
    )

    # demographics (round 6 only page, stored on last round's Player)
    age = models.IntegerField(label="Âge", min=16, max=99, blank=True)
    gender = models.StringField(
        label="Genre",
        choices=[
            ("woman", "Femme"),
            ("man", "Homme"),
            ("nonbinary", "Non-binaire / autre"),
            ("na", "Préfère ne pas répondre"),
        ],
        blank=True,
    )
    bulk_frequency = models.IntegerField(
        label="À quelle fréquence achetez-vous en vrac dans la vie quotidienne ?",
        choices=[
            (1, "Jamais"),
            (2, "Rarement"),
            (3, "Parfois"),
            (4, "Souvent"),
            (5, "Très souvent"),
        ],
        blank=True,
    )


def creating_session(subsession: Subsession):
    if subsession.round_number == 1:
        for p in subsession.get_players():
            msg = random.choice(C.MESSAGE_TYPES)
            frame = random.choice(C.GOAL_FRAMES)
            p.participant.vars["message_type"] = msg
            p.participant.vars["goal_frame"] = frame
            p.participant.vars["t0"] = None


def _get_remaining_time(player: Player) -> int:
    t0 = player.participant.vars.get("t0")
    if t0 is None:
        return C.TOTAL_TIME_SECONDS
    elapsed = time.time() - t0
    remaining = int(C.TOTAL_TIME_SECONDS - elapsed)
    return max(0, remaining)


def _get_message_text(player: Player) -> str:
    msg_type = player.participant.vars.get("message_type", C.MSG_NEUTRAL)
    return C.MESSAGES.get(msg_type, "")


def _get_goal_frame(player: Player) -> str:
    return player.participant.vars.get("goal_frame", "individual")


# -----------------------------
# LAB-STYLE PAGES (round 1)
# -----------------------------

class Instructions(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1

    @staticmethod
    def vars_for_template(player: Player):
        return dict(
            total_time=C.TOTAL_TIME_SECONDS,
            num_products=C.NUM_ROUNDS,
            goal_frame=_get_goal_frame(player),
        )


class Comprehension(Page):
    form_model = "player"
    form_fields = ["quiz_default", "quiz_time"]

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1

    @staticmethod
    def error_message(player: Player, values):
        errors = []
        if values.get("quiz_default") != C.QUIZ_DEFAULT_CORRECT:
            errors.append("Q1 incorrecte.")
        if values.get("quiz_time") != C.QUIZ_TIME_CORRECT:
            errors.append("Q2 incorrecte.")
        if errors:
            return " ".join(errors) + " Merci de relire les consignes et de répondre à nouveau."
        return None


class Start(Page):
    """
    Short 'ready' page. Starts the global timer here (not earlier),
    so all participants have the same 'decision time' window.
    """
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == 1

    @staticmethod
    def vars_for_template(player: Player):
        if player.participant.vars.get("t0") is None:
            player.participant.vars["t0"] = time.time()
        return dict(
            total_time=C.TOTAL_TIME_SECONDS,
            goal_frame=_get_goal_frame(player),
        )

class MidFeedback(Page):
    @staticmethod
    def is_displayed(player: Player):
        return (
                player.round_number == 3
                and not player.participant.vars.get("global_timeout", False)
        )

    @staticmethod
    def vars_for_template(player: Player):
        rounds_so_far = player.in_rounds(1, 3)
        bulk_count = sum(1 for r in rounds_so_far if r.choice == C.BULK)
        pack_count = 3 - bulk_count
        return dict(
            bulk_count=bulk_count,
            pack_count=pack_count,
            goal_frame=_get_goal_frame(player),
        )

# -----------------------------
# TASK PAGES (all rounds)
# -----------------------------

class Product(Page):
    form_model = "player"
    form_fields = ["choice"]

    @staticmethod
    def get_timeout_seconds(player: Player):
        # Pas de limite de temps pour les bots (sinon ils restent sur le défaut)
        if player.participant._is_bot:
            return None
        return _get_remaining_time(player)

    @staticmethod
    def vars_for_template(player: Player):
        player.message_type = player.participant.vars.get("message_type", C.MSG_NEUTRAL)
        player.goal_frame = player.participant.vars.get("goal_frame", "individual")

        i = player.round_number - 1
        message_text = _get_message_text(player)

        # Header + style du message (sans logique dans le template)
        if player.message_type in ["soc_desc", "soc_inj"]:
            msg_header = "👥 Message d’information"
            msg_border = "#1565c0"
            msg_bg = "#f3f8ff"
        elif player.message_type in ["eco_desc", "eco_inj"]:
            msg_header = "🌱 Information environnementale"
            msg_border = "#2e7d32"
            msg_bg = "#f4fff4"
        else:
            msg_header = "ℹ️ Information"
            msg_border = "#777777"
            msg_bg = "#f7f7f7"

        # Gestion propre du checked (PLUS AUCUN IF DANS LE HTML)
        checked_pack = "checked" if player.choice == C.PACK else ""
        checked_bulk = "checked" if player.choice == C.BULK else ""

        return dict(
            product_name=C.PRODUCTS[i],
            message_text=message_text,
            msg_header=msg_header,
            msg_border=msg_border,
            msg_bg=msg_bg,
            remaining=_get_remaining_time(player),
            round_number=player.round_number,
            num_rounds=C.NUM_ROUNDS,
            checked_pack=checked_pack,
            checked_bulk=checked_bulk,
        )

    @staticmethod
    def before_next_page(player: Player, timeout_happened):
        if timeout_happened:
            player.timed_out = True
            player.submitted = False
            # on marque que le temps global est écoulé
            player.participant.vars["global_timeout"] = True
        else:
            player.submitted = True

    @staticmethod
    def is_displayed(player: Player):
        return not player.participant.vars.get("global_timeout", False)

class Demographics(Page):
    form_model = "player"
    form_fields = ["age", "gender", "bulk_frequency"]

    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

class Results(Page):
    @staticmethod
    def is_displayed(player: Player):
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def vars_for_template(player: Player):
        rounds = player.in_all_rounds()

        # uniquement les produits réellement validés
        validated = [r for r in rounds if r.submitted]

        answered_n = len(validated)
        bulk_count = sum(1 for r in validated if r.choice == C.BULK)
        pack_count = answered_n - bulk_count
        any_timeout = any(r.timed_out for r in rounds)

        # feedback écologique simple
        grams_saved = bulk_count * 50
        percent_bulk = round((bulk_count / answered_n) * 100) if answered_n > 0 else 0

        return dict(
            answered_n=answered_n,
            total_n=C.NUM_ROUNDS,
            bulk_count=bulk_count,
            pack_count=pack_count,
            grams_saved=grams_saved,
            percent_bulk=percent_bulk,
            any_timeout=any_timeout,
        )

page_sequence = [Instructions, Comprehension, Start, Product, MidFeedback, Demographics, Results]

