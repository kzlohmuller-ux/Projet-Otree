from otree.api import *
import random
from . import Instructions, Comprehension, Start, Product, MidFeedback, Demographics, Results


class PlayerBot(Bot):

    def play_round(self):

        if self.round_number == 1:
            yield Submission(Instructions, check_html=False)
            yield Comprehension, dict(quiz_default=2, quiz_time=60)
            yield Submission(Start, check_html=False)

        msg = self.participant.vars.get("message_type", "neutral")
        frame = self.participant.vars.get("goal_frame", "individual")

        # ----------------------------
        # PARAMÉTRAGE "DÉMO" : EFFETS FORTS
        # ----------------------------
        # Base (neutre) : faible mais pas ridicule
        p_bulk = 0.15

        # Effets par type de message (beaucoup plus marqués pour la démo)
        if msg == "soc_desc":
            p_bulk = 0.55
        elif msg == "soc_inj":
            p_bulk = 0.40
        elif msg == "eco_desc":
            p_bulk = 0.45
        elif msg == "eco_inj":
            p_bulk = 0.30
        elif msg == "neutral":
            p_bulk = 0.15

        # Cadre collectif : amplifie surtout les injonctifs
        if frame == "collective" and msg in ["soc_inj", "eco_inj"]:
            p_bulk += 0.20  # boost très visible

        # Petites variations pour éviter des taux trop "parfaits"
        p_bulk += random.uniform(-0.05, 0.05)

        p_bulk = max(0.02, min(0.95, p_bulk))
        choice = "bulk" if random.random() < p_bulk else "pack"

        yield Product, dict(choice=choice)

        if self.round_number == 3:
            yield Submission(MidFeedback, check_html=False)

        if self.round_number == 6:
            yield Demographics, dict(age=29, gender="na", bulk_frequency=3)
            yield Submission(Results, check_html=False)
