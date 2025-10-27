import sys
import os

# --- Ensure package imports work when running standalone ---
if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from levels import level2
except ImportError:
    import level2

class Level1:
    def __init__(self, game):
        self.game = game
        print("Entered Level 1")

    def run(self):
        print("Playing Level 1...")
        level_complete = True
        if level_complete:
            print("Level 1 complete!")
            self.next_level()

    def next_level(self):
        self.game.current_level = level2.Level2(self.game)
        self.game.current_level.run()


if __name__ == "__main__":
    class DummyGame: pass
    Level1(DummyGame()).run()
