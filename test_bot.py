import asyncio
import logging
from poke_env.player import Player, BattleOrder, RandomPlayer
from poke_env.server_configuration import LocalhostServer

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")

class TestBot(Player):
    """Bot mínimo para probar conexión local."""
    
    async def choose_move(self, battle) -> BattleOrder:
        moves = list(battle.available_moves.values()) if battle.available_moves else []
        if moves:
            return self.create_order(moves[0])
        switches = list(battle.available_switches.values()) if battle.available_switches else []
        if switches:
            return self.create_order(switches[0])
        return self.choose_random_move()
    
    def teampreview(self, battle) -> BattleOrder:
        return self.choose_random_move()

async def main():
    # ✅ poke-env 0.8.0: LocalhostServer existe aquí
    server_config = LocalhostServer(port=8080)
    
    bot = TestBot(username="TestBot", server_configuration=server_config)
    opponent = RandomPlayer(username="RandomOpp", server_configuration=server_config)
    
    logging.info("🚀 Iniciando prueba de conexión local...")
    results = await bot.battle_against(opponent, n_battles=2)
    
    wins = sum(1 for r in results if r == 1)
    logging.info(f"✅ Prueba completada: {wins}/2 victorias")

if __name__ == "__main__":
    asyncio.run(main())
