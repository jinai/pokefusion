from pokefusion.db.database import database
from pokefusion.db.models import Totem
from pokefusion.fusionapi import FusionClient, FusionResult


class TotemService:
    def __init__(self, fusion_service: FusionClient) -> None:
        self.fusion_service = fusion_service

    def get_or_create(self, discord_id: int) -> FusionResult:
        totem, created = Totem.get_or_create(discord_id=discord_id)

        if created:
            fusion, head, body = self._generate_totem()
            Totem.update(head=head, body=body).where(Totem.discord_id == discord_id).execute()
            result = fusion
        else:
            result = self.fusion_service.fusion(str(totem.head), str(totem.body))

        return result

    def reroll_totem(self, discord_id: int) -> FusionResult:
        fusion, head, body = self._generate_totem()
        Totem.update(head=head, body=body).where(Totem.discord_id == discord_id).execute()
        return fusion

    def reroll_all_totems(self):
        with database.atomic("EXCLUSIVE"):
            # Todo: bulk update
            for (totem_id,) in Totem.get_all_ids():
                self.reroll_totem(totem_id)

    def _generate_totem(self):
        fusion = self.fusion_service.totem()
        return fusion, fusion.head.dex_id, fusion.body.dex_id
