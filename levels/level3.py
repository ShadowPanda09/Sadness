import sys
import os

if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from levels import boss_level
except ImportError:
    import boss_level

class Level3:
    def __init__(self, game):
        self.game = game
        print("Entered Level 3")

    def run(self):
        print("Playing Level 3...")
        level_complete = True
        if level_complete:
            print("Level 3 complete!")
            self.next_level()

    def next_level(self):
        self.game.current_level = boss_level.BossLevel(self.game)
        self.game.current_level.run()


if __name__ == "__main__":
    class DummyGame: pass
    Level3(DummyGame()).run()

